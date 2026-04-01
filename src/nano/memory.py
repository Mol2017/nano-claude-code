"""
Memory loader for nano-claude-code.
Walks up from cwd collecting CLAUDE.md files into the system prompt,
mirroring Claude Code's memdir behavior.
"""

from pathlib import Path


def load_memory(cwd: str | None = None) -> str:
    """
    Walk from cwd up to filesystem root, collecting CLAUDE.md files.
    Returns concatenated content, outermost (root) first.
    Returns empty string if no CLAUDE.md files found.
    """
    root = Path(cwd or Path.cwd())
    parts: list[str] = []

    path = root.resolve()
    while True:
        claude_md = path / "CLAUDE.md"
        if claude_md.exists():
            try:
                content = claude_md.read_text().strip()
                if content:
                    parts.append(f"# Memory from {claude_md}\n\n{content}")
            except Exception:
                pass
        parent = path.parent
        if parent == path:
            break
        path = parent

    # parts are innermost-first; reverse so outermost (global) comes first
    parts.reverse()
    return "\n\n---\n\n".join(parts)
