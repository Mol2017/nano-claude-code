"""
Rich UI helpers for nano-claude-code.
Provides streaming panels, markdown rendering, and status spinners.
"""

from contextlib import contextmanager

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text

console = Console()

BORDER_COLOR = "bright_cyan"
TOOL_COLOR = "yellow"
ERROR_COLOR = "red"
DIM_COLOR = "dim"


def render_markdown(text: str, title: str = "Claude") -> None:
    """Render a markdown response in a styled panel."""
    if text.strip():
        console.print(Panel(Markdown(text), title=title, border_style=BORDER_COLOR))


def render_tool_call(name: str, inputs: dict) -> None:
    """Show a compact tool-call notification."""
    inputs_str = ", ".join(
        f"{k}={repr(v)[:60]}" for k, v in inputs.items()
    )
    console.print(f"  [{TOOL_COLOR}]⚙ {name}[/{TOOL_COLOR}] [dim]({inputs_str})[/dim]")


def render_tool_result(name: str, result: str) -> None:
    """Show truncated tool result."""
    preview = result[:300].replace("\n", " ")
    if len(result) > 300:
        preview += f"… ({len(result)} chars)"
    console.print(f"  [dim]↳ {preview}[/dim]")


def render_error(message: str) -> None:
    console.print(f"[{ERROR_COLOR}]Error: {message}[/{ERROR_COLOR}]")


def render_info(message: str) -> None:
    console.print(f"[{DIM_COLOR}]{message}[/{DIM_COLOR}]")


@contextmanager
def streaming_response(title: str = "Claude"):
    """
    Context manager that yields a function `update(text)`.
    Call update() as streaming chunks arrive to refresh the Live panel.
    """
    accumulated = [""]

    def update(chunk: str) -> None:
        accumulated[0] += chunk

    panel_ref = [Panel(Text(""), title=title, border_style=BORDER_COLOR)]

    with Live(panel_ref[0], console=console, refresh_per_second=10) as live:
        update_fn = update

        def refresh_update(chunk: str) -> None:
            update(chunk)
            live.update(
                Panel(
                    Markdown(accumulated[0]) if accumulated[0] else Text("…"),
                    title=title,
                    border_style=BORDER_COLOR,
                )
            )

        yield refresh_update


@contextmanager
def spinner(message: str):
    """Show a spinner while doing background work."""
    with console.status(f"[dim]{message}[/dim]", spinner="dots"):
        yield
