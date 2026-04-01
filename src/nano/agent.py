"""
Core agentic query loop for nano-claude-code.
Mirrors the while(true) loop in Claude Code's query.ts and
claw-code's ConversationRuntime::run_turn().

Loop: append user message → call model (streaming) → render text →
      execute any tool_use blocks → append results → repeat until no tools.
"""

import os
from typing import Any

import anthropic

from .memory import load_memory
from .permissions import Permissions
from .tools import execute_tool, get_tools
from .ui import (
    console,
    render_markdown,
    render_tool_call,
    render_tool_result,
    streaming_response,
)

DEFAULT_MODEL = "claude-opus-4-5"
MAX_TOKENS = 8096


class Agent:
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        permissions: Permissions | None = None,
        cwd: str | None = None,
    ):
        self.client = anthropic.Anthropic()
        self.model = model
        self.permissions = permissions or Permissions()
        self.cwd = cwd or os.getcwd()
        self.messages: list[dict[str, Any]] = []
        self.tools = get_tools()
        self._memory: str = load_memory(self.cwd)

    def reload_memory(self) -> None:
        self._memory = load_memory(self.cwd)

    def clear(self) -> None:
        self.messages.clear()

    def compact(self) -> None:
        """Summarize the conversation and restart with the summary as context."""
        if not self.messages:
            return
        summary = self._summarize_history()
        self.messages = [
            {
                "role": "user",
                "content": f"[Conversation compacted]\n\n{summary}",
            },
            {
                "role": "assistant",
                "content": "Understood. I have the context from our previous conversation.",
            },
        ]

    def _summarize_history(self) -> str:
        """Ask the model to summarize the current conversation."""
        history_text = "\n".join(
            f"{m['role'].upper()}: "
            + (
                m["content"]
                if isinstance(m["content"], str)
                else str(m["content"])[:500]
            )
            for m in self.messages[-30:]  # last 30 messages
        )
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Please summarize the following conversation history "
                        "concisely, preserving key decisions, files touched, "
                        "and open questions:\n\n" + history_text
                    ),
                }
            ],
        )
        return resp.content[0].text if resp.content else "(summary unavailable)"

    def _build_system(self) -> str:
        parts = [
            "You are nano-claude-code, a helpful AI coding assistant with access to tools.",
            "You can read and edit files, run bash commands, and search the codebase.",
            f"Working directory: {self.cwd}",
            "Use tools freely to explore the codebase and accomplish tasks.",
            "When using edit_file, old_string must match exactly — include surrounding context if needed to make it unique.",
        ]
        if self._memory:
            parts.append("\n---\n# Project Memory (from CLAUDE.md)\n\n" + self._memory)
        return "\n\n".join(parts)

    def submit_message(self, user_text: str) -> None:
        """
        Add a user message and run the agentic loop until the model
        stops requesting tool calls.
        """
        self.messages.append({"role": "user", "content": user_text})

        while True:
            # Call model with streaming output
            response_content = self._call_model_streaming()

            # Split into text and tool_use blocks
            text_blocks = [b for b in response_content if b.type == "text"]
            tool_blocks = [b for b in response_content if b.type == "tool_use"]

            # Text is already rendered live during streaming, but if the
            # streaming panel didn't fire (e.g. empty stream), render now.
            # We skip re-rendering since streaming_response already displayed it.

            # Append assistant turn — serialize only fields the API accepts.
            # model_dump() includes internal SDK fields (e.g. parsed_output)
            # that the API rejects with 400 when sent back in message history.
            self.messages.append(
                {
                    "role": "assistant",
                    "content": [_serialize_block(b) for b in response_content],
                }
            )

            # No tools → done
            if not tool_blocks:
                break

            # Execute tools
            tool_results = []
            for block in tool_blocks:
                render_tool_call(block.name, block.input)
                result = execute_tool(block.name, block.input, self.permissions)
                render_tool_result(block.name, result)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

            self.messages.append({"role": "user", "content": tool_results})

    def _call_model_streaming(self) -> list:
        """
        Call the Anthropic API with streaming, rendering text chunks live.
        Returns the final list of content blocks.
        """
        system = self._build_system()
        accumulated_text = [""]
        final_message = None

        with streaming_response("Claude") as update:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=self.messages,
                tools=self.tools,
            ) as stream:
                for event in stream:
                    if (
                        hasattr(event, "type")
                        and event.type == "content_block_delta"
                        and hasattr(event, "delta")
                        and hasattr(event.delta, "text")
                    ):
                        update(event.delta.text)
                        accumulated_text[0] += event.delta.text

                final_message = stream.get_final_message()

        return final_message.content


def _serialize_block(block) -> dict:
    """
    Serialize an Anthropic SDK content block to only the fields the API
    accepts when the block is sent back in message history. model_dump()
    includes internal SDK fields that trigger 400 errors.
    """
    if block.type == "text":
        return {"type": "text", "text": block.text}
    if block.type == "tool_use":
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
        }
    # fallback: strip unknown extra fields by keeping only the known-safe ones
    return {"type": block.type}
