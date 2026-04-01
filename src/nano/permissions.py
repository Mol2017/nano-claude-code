"""
Permission system for nano-claude-code.
Three modes mirroring claw-code's PermissionMode:
  ReadOnly        — bash blocked, file writes blocked
  WorkspaceWrite  — bash + writes allowed, but prompts user before executing
  DangerFullAccess — everything runs without prompting
"""

from enum import Enum
from rich.console import Console

console = Console()


class PermissionMode(Enum):
    READ_ONLY = "readonly"
    WORKSPACE_WRITE = "workspace_write"
    DANGER_FULL_ACCESS = "danger"


class Permissions:
    def __init__(self, mode: PermissionMode = PermissionMode.WORKSPACE_WRITE):
        self.mode = mode

    def can_bash(self) -> bool:
        return self.mode in (PermissionMode.WORKSPACE_WRITE, PermissionMode.DANGER_FULL_ACCESS)

    def can_write(self) -> bool:
        return self.mode in (PermissionMode.WORKSPACE_WRITE, PermissionMode.DANGER_FULL_ACCESS)

    def confirm_bash(self, command: str) -> bool:
        """Prompt user before running a bash command (WorkspaceWrite mode)."""
        if self.mode == PermissionMode.DANGER_FULL_ACCESS:
            return True
        if self.mode == PermissionMode.READ_ONLY:
            return False
        console.print(f"\n[yellow]Run command?[/yellow] [dim]{command[:120]}[/dim]")
        console.print("[bright_cyan]Confirm? [y/N]: [/bright_cyan]", end="")
        answer = input().strip().lower()
        return answer in ("y", "yes")

    def confirm_write(self, path: str) -> bool:
        """Prompt user before writing a file (WorkspaceWrite mode)."""
        if self.mode == PermissionMode.DANGER_FULL_ACCESS:
            return True
        if self.mode == PermissionMode.READ_ONLY:
            return False
        console.print(f"\n[yellow]Write file?[/yellow] [dim]{path}[/dim]")
        console.print("[bright_cyan]Confirm? [y/N]: [/bright_cyan]", end="")
        answer = input().strip().lower()
        return answer in ("y", "yes")
