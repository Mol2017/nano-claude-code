"""
nano-claude-code — entry point.
Plain input() loop with Rich prompts, mirroring rallies-cli's interactive_shell().
"""

import os
import sys

from rich.panel import Panel
from rich.text import Text

from .agent import Agent
from .commands import handle_command
from .permissions import PermissionMode, Permissions
from .ui import console, render_error


BANNER = """\
 ███╗   ██╗ █████╗ ███╗   ██╗ ██████╗
 ████╗  ██║██╔══██╗████╗  ██║██╔═══██╗
 ██╔██╗ ██║███████║██╔██╗ ██║██║   ██║
 ██║╚██╗██║██╔══██║██║╚██╗██║██║   ██║
 ██║ ╚████║██║  ██║██║ ╚████║╚██████╔╝
 ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝
 nano-claude-code  •  type /help for commands"""


def parse_args() -> tuple[str, PermissionMode]:
    """Very minimal arg parsing: --dangerously-skip-permissions flag."""
    args = sys.argv[1:]
    mode = PermissionMode.WORKSPACE_WRITE
    cwd = os.getcwd()

    for arg in args:
        if arg in ("--dangerously-skip-permissions", "--danger"):
            mode = PermissionMode.DANGER_FULL_ACCESS
        elif arg == "--readonly":
            mode = PermissionMode.READ_ONLY

    return cwd, mode


def main() -> None:
    cwd, mode = parse_args()

    console.print(Panel(Text(BANNER, style="bright_cyan"), border_style="bright_cyan"))

    if mode == PermissionMode.READ_ONLY:
        console.print("[dim]Mode: read-only (no bash, no writes)[/dim]")
    elif mode == PermissionMode.DANGER_FULL_ACCESS:
        console.print("[yellow]Mode: danger — all operations auto-approved[/yellow]")
    else:
        console.print("[dim]Mode: workspace-write (prompts before bash/writes)[/dim]")

    permissions = Permissions(mode)
    agent = Agent(permissions=permissions, cwd=cwd)

    if agent._memory:
        console.print(f"[dim]Loaded memory from CLAUDE.md[/dim]")

    console.print()

    while True:
        try:
            console.print("[bright_cyan]> [/bright_cyan]", end="")
            user_input = input()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.startswith("/"):
            try:
                handle_command(user_input, agent)
            except SystemExit:
                break
            continue

        try:
            agent.submit_message(user_input)
        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted.[/dim]")
        except Exception as e:
            render_error(str(e))


if __name__ == "__main__":
    main()
