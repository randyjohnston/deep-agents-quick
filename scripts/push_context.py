"""Push the researcher agent's instructions to LangSmith Context Hub.

Run with: uv run python scripts/push_context.py
"""

from dotenv import load_dotenv
from langsmith import Client
from langsmith.schemas import FileEntry

from app.agent import FALLBACK_INSTRUCTIONS

load_dotenv(override=True)


def main() -> None:
    client = Client()
    url = client.push_agent(
        "default/deep-agents-quick",
        files={"AGENTS.md": FileEntry(content=FALLBACK_INSTRUCTIONS)},
        description="Research agent for deep-agents-quick: conducts web research and writes reports.",
        tags=["research", "deep-agents"],
    )
    print(f"Pushed context: {url}")


if __name__ == "__main__":
    main()
