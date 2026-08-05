"""Storage wiring for the agent's virtual filesystem.

Scratch files stay ephemeral in StateBackend; only the skills prefix is routed
to disk. Pointing the whole backend at the filesystem would also hand the agent
the recursive `delete` tool over this repo, which deepagents 0.7.0 classifies as
an ordinary write.
"""

from __future__ import annotations

from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend

from app import config


def build_backend() -> CompositeBackend:
    # CompositeBackend strips the matched prefix before delegating, so root_dir
    # is the skills directory itself: a read of /skills/x/SKILL.md arrives at
    # the FilesystemBackend as /x/SKILL.md.
    return CompositeBackend(
        default=StateBackend(),
        routes={config.SKILLS_PREFIX: FilesystemBackend(root_dir=config.SKILLS_DIR)},
    )
