"""
Guardrail middleware for the deep agent.

Three layers:

1. AIDefenseMiddleware (aidefense_langchain) — Cisco AI Defense (optional):
   prompt injection, jailbreak, PII leakage, and unsafe-operation detection on
   all LLM I/O and tool calls. Install: uv sync --extra cisco

2. PIIMiddleware (langchain.agents.middleware) — built-in PII redaction; one
   instance per PII type (email, credit_card, ip, mac_address, url). No extra
   packages needed.

3. policy_moderation_middleware() — LLM-judged compliance gate against legal &
   marketing policies, implemented as a @before_agent input rail. Refuses
   restricted-advice requests before the model runs, so no tokens stream.
   Reuses the configured model. Drop <name>.md files in policies/ at the project
   root to extend coverage.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from langchain.agents.middleware import AgentState, after_agent, after_model, before_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_POLICIES_DIR = Path(__file__).parent.parent / "policies"

_BUILTIN_LEGAL = """\
- Do not provide specific legal advice or represent output as constituting legal advice.
- Do not disclose confidential client or contract information.
- Do not make statements that could constitute defamation, copyright infringement, or IP misuse.
- Do not generate content that could constitute fraud, deceptive trade practices, or regulatory violations.
"""

_BUILTIN_MARKETING = """\
- All claims must be factually accurate and substantiated.
- Do not make unqualified superlatives or comparisons to competitors without evidence.
- Do not promise specific business outcomes, ROI percentages, or performance guarantees.
- Do not use content that could be perceived as discriminatory or that targets protected groups.
- Maintain brand voice: professional, clear, and inclusive.
"""


class _PolicyVerdict(BaseModel):
    """Structured verdict returned by the policy judge."""

    violated: bool = Field(description="True if the content violates any policy.")
    reason: str | None = Field(
        default=None,
        description="Brief explanation of which policy was violated and how. Null if no violation.",
    )


def _extract_text(content: Any) -> str:
    """Pull text out of a message.content that may be a string or a list of blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(block.get("text", ""))
            else:
                parts.append(getattr(block, "text", "") or "")
        return " ".join(p for p in parts if p).strip()
    return ""


def policy_moderation_middleware(
    *,
    model: str | None = None,
    extra_policies: dict[str, str] | None = None,
    block_on_violation: bool = True,
):
    """Return [input_rail, output_rail] guardrails enforcing legal/marketing policies.

    The @before_agent input rail refuses restricted-advice requests before the
    model runs (short-circuits with `jump_to: "end"`) so no tokens stream.
    The @after_agent output rail backstops the input rail: if a violating
    response gets generated anyway, it overwrites the final AIMessage content
    with a refusal.

    Args:
        model: LangChain model string (e.g. "anthropic:claude-haiku-4-5-20251001").
               Defaults to POLICY_JUDGE_MODEL env var, falling back to MODEL.
        extra_policies: Additional {name: text} policies to include.
        block_on_violation: When True, short-circuit/rewrite on violation. When False, log only.
    """
    policies: dict[str, str] = {"legal": _BUILTIN_LEGAL, "marketing": _BUILTIN_MARKETING}

    if _POLICIES_DIR.exists():
        for md in sorted(_POLICIES_DIR.glob("*.md")):
            policies[md.stem] = md.read_text()

    if extra_policies:
        policies.update(extra_policies)

    policy_text = "\n\n---\n\n".join(
        f"## {name.upper()}\n{text.strip()}" for name, text in policies.items()
    )

    judge_model = (
        model
        or os.getenv("POLICY_JUDGE_MODEL")
        or os.getenv("MODEL", "anthropic:claude-sonnet-4-6")
    )
    judge = init_chat_model(judge_model).with_structured_output(_PolicyVerdict)

    input_system_prompt = (
        "You are a content policy gatekeeper. Determine whether responding "
        "substantively to the user's request would require generating content "
        "that violates company policy.\n\n"
        "Flag (violated=true) when the user is asking for:\n"
        "  • Legal advice, legal opinions, contract interpretation, or guidance on "
        "    legal procedures (e.g. 'how to break my lease', 'can I sue X', "
        "    'what are my rights', 'is X legal').\n"
        "  • Medical or mental-health advice on a specific situation.\n"
        "  • Financial or investment advice on a specific situation.\n"
        "  • Marketing copy that would require making unverifiable claims, "
        "    competitor comparisons, or ROI/performance guarantees.\n"
        "  • Anything that would necessarily violate the policies below.\n\n"
        "Do NOT flag general research/information questions, technical questions, "
        "or factual lookups. Err on the side of flagging when the request is "
        "specifically asking for personal advice in a restricted domain.\n\n"
        f"POLICIES:\n{policy_text}"
    )

    output_system_prompt = (
        "You are a strict compliance reviewer evaluating an AI-generated response. "
        "Determine whether the content violates company policy. Be thorough and "
        "unforgiving — partial, ambiguous, or 'with-disclaimer' violations all count.\n\n"
        "Flag (violated=true) when the response:\n"
        "  • Provides specific legal advice, legal opinions, or guidance on legal "
        "    procedures (even with a disclaimer).\n"
        "  • Provides specific medical/mental-health or financial/investment advice.\n"
        "  • Offers to provide a 'general overview', 'research summary', or "
        "    'common approaches' on a restricted topic — engagement is the violation.\n"
        "  • Asks clarifying questions to refine a restricted-advice request "
        "    (jurisdiction, reason, specifics). The compliant move is to refuse "
        "    and redirect, not to gather more facts.\n"
        "  • Walks through legal doctrines, remedies, or procedures (e.g. "
        "    'warranty of habitability', 'constructive eviction', 'SCRA').\n"
        "  • Drafts, edits, or interprets contracts or legal instruments.\n"
        "  • Makes marketing claims about products, capabilities, ROI, or release "
        "    timelines that aren't verifiably accurate or that reference "
        "    unreleased features.\n"
        "  • Could constitute fraud, defamation, IP infringement, or confidentiality "
        "    breach.\n\n"
        "A compliant response to a restricted-advice request is a short refusal "
        "that redirects to a licensed professional. Anything that engages with the "
        "substance — even disclaimed — is a violation.\n\n"
        f"POLICIES:\n{policy_text}"
    )

    @traceable(
        run_type="llm",
        name="policy-moderation-input-check",
        tags=["policy-judge", "guardrail", "input-rail"],
        metadata={"judge_model": judge_model, "policies": list(policies.keys())},
    )
    async def _judge_input(user_text: str) -> _PolicyVerdict:
        """Pre-flight check on the user request; attaches verdict to the trace."""
        verdict: _PolicyVerdict = await judge.ainvoke([
            SystemMessage(content=input_system_prompt),
            HumanMessage(content=f"USER REQUEST:\n{user_text}"),
        ])
        run = get_current_run_tree()
        if run is not None:
            run.add_metadata({"verdict": verdict.model_dump()})
        return verdict

    @traceable(
        run_type="llm",
        name="policy-moderation-output-check",
        tags=["policy-judge", "guardrail", "output-rail"],
        metadata={"judge_model": judge_model, "policies": list(policies.keys())},
    )
    async def _judge_output(content_text: str) -> _PolicyVerdict:
        """Post-flight check on the agent's final response; attaches verdict to the trace."""
        verdict: _PolicyVerdict = await judge.ainvoke([
            SystemMessage(content=output_system_prompt),
            HumanMessage(content=f"AI RESPONSE TO REVIEW:\n{content_text}"),
        ])
        run = get_current_run_tree()
        if run is not None:
            run.add_metadata({"verdict": verdict.model_dump()})
        return verdict

    @before_agent(can_jump_to=["end"])
    async def policy_input_check(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        """Refuse restricted-advice requests before the model runs (prevents streamed leak)."""
        messages = state["messages"]
        last_human = next(
            (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
        )
        if last_human is None:
            return None

        text = _extract_text(last_human.content)
        if not text:
            return None

        try:
            verdict = await _judge_input(text)
        except Exception as exc:
            logger.warning("Policy input check failed: %s", exc)
            return None

        if verdict.violated:
            reason = verdict.reason or "policy violation"
            logger.warning("Policy moderation refused input: %s", reason)
            if block_on_violation:
                refusal = AIMessage(
                    content=(
                        "I can't help with that. This kind of request requires a "
                        "licensed professional — please consult a qualified attorney, "
                        "doctor, or financial advisor for your situation."
                    )
                )
                return {"messages": [refusal], "jump_to": "end"}
        else:
            logger.info("Policy moderation: input passed compliance check.")

        return None

    @after_model
    async def policy_output_check(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        """Backstop check on the agent's final response; rewrites content on violation."""
        messages = state["messages"]
        last_ai = next(
            (m for m in reversed(messages) if isinstance(m, AIMessage)), None
        )
        if last_ai is None:
            return None

        text = _extract_text(last_ai.content)
        if not text:
            return None

        try:
            verdict = await _judge_output(text)
        except Exception as exc:
            logger.warning("Policy output check failed: %s", exc)
            return None

        if verdict.violated:
            reason = verdict.reason or "policy violation"
            logger.warning("Policy moderation flagged output: %s", reason)
            if block_on_violation:
                last_ai.content = (
                    "I can't help with that. The response was blocked by content "
                    f"policy: {reason}"
                )
        else:
            logger.info("Policy moderation: output passed compliance review.")

        return None

    return [policy_output_check]
