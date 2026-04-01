"""
Slash command dispatch for nano-claude-code.
Pattern from claw-code's commands.py and rallies-cli's helpers.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .ui import console, render_info

if TYPE_CHECKING:
    from .agent import Agent

COMMANDS = {
    "/help": "Show available commands and tools",
    "/clear": "Clear conversation history",
    "/compact": "Summarize history and restart with the summary as context",
    "/memory": "Show loaded CLAUDE.md memory",
    "/exit": "Quit nano-claude-code",
    "/quit": "Quit nano-claude-code",
}

TOOLS_SUMMARY = {
    "bash": "Run a shell command",
    "read_file": "Read file contents",
    "write_file": "Write or create a file",
    "edit_file": "Find-and-replace in a file",
    "glob": "List files by glob pattern",
    "grep": "Search file contents with regex",
}


def handle_command(raw: str, agent: "Agent") -> bool:
    """
    Dispatch a slash command. Returns True if handled (don't send to agent),
    False if unrecognized (will be passed to agent as normal message).
    """
    parts = raw.strip().split(None, 1)
    cmd = parts[0].lower()

    match cmd:
        case "/help":
            _cmd_help()
        case "/clear":
            agent.clear()
            render_info("Conversation cleared.")
        case "/compact":
            render_info("Compacting conversation…")
            agent.compact()
            render_info("Done. History replaced with summary.")
        case "/memory":
            _cmd_memory(agent)
        case "/exit" | "/quit":
            console.print("[dim]Goodbye.[/dim]")
            raise SystemExit(0)
        case _:
            render_info(f"Unknown command: {cmd}. Type /help for available commands.")

    return True


def _cmd_help() -> None:
    table = Table(title="Commands", border_style="bright_cyan", show_header=False)
    table.add_column("Command", style="bright_cyan")
    table.add_column("Description")
    for cmd, desc in COMMANDS.items():
        table.add_row(cmd, desc)
    console.print(table)

    tools_table = Table(title="Tools", border_style="yellow", show_header=False)
    tools_table.add_column("Tool", style="yellow")
    tools_table.add_column("Description")
    for tool, desc in TOOLS_SUMMARY.items():
        tools_table.add_row(tool, desc)
    console.print(tools_table)


def _cmd_memory(agent: "Agent") -> None:
    mem = agent._memory
    if not mem:
        render_info("No CLAUDE.md found in this directory or its parents.")
    else:
        console.print(Panel(Markdown(mem), title="Memory (CLAUDE.md)", border_style="bright_cyan"))
