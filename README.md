# nano-claude-code

A minimal Python implementation of [Claude Code](https://claude.ai/code) — the agentic CLI coding assistant. Captures the core architecture in ~500 lines of readable Python.

## What it does

- Talks to Claude via the Anthropic API
- Runs an agentic loop: model response → tool calls → results → next model call
- Streams responses live in the terminal using Rich
- Reads and edits files, runs bash commands, searches the codebase
- Loads `CLAUDE.md` memory files from your project directory
- Slash commands for session management

## Architecture

```
src/nano/
├── main.py        — input loop, banner, /command dispatch
├── agent.py       — while(True) agentic loop + streaming API calls
├── tools.py       — tool registry and implementations
├── commands.py    — /help /clear /compact /memory /exit
├── permissions.py — ReadOnly / WorkspaceWrite / DangerFullAccess modes
├── memory.py      — walks up from cwd collecting CLAUDE.md files
└── ui.py          — Rich live panels, markdown rendering
```

### Data flow

```
user input
    │
    ▼
main.py        — plain input() + Rich prompt
    │ /command → commands.py
    │ message  → agent.submit_message()
    ▼
agent.py       — while True agentic loop
    │
    ├── _call_model_streaming()
    │       └── anthropic SDK streaming → Live panel updates in terminal
    │
    ├── text blocks   → rendered as Markdown panel
    │
    └── tool_use blocks?
            │ yes → tools.py::execute_tool()
            │       permissions check → confirm_bash() / confirm_write()
            │       append tool_result → loop again
            └── no  → break
```

## Installation

Requires Python 3.12+ and an Anthropic API key.

```bash
git clone https://github.com/Mol2017/nano-claude-code
cd nano-claude-code

# create a virtual environment
uv venv .venv
uv pip install -e .

# or with plain pip
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
export ANTHROPIC_API_KEY="sk-ant-..."

# default mode (prompts before bash/writes)
.venv/bin/nano-claude-code

# or source the venv and run directly
source .venv/bin/activate
nano-claude-code

# skip all confirmation prompts
nano-claude-code --dangerously-skip-permissions

# read-only (no bash, no file writes)
nano-claude-code --readonly
```

## Tools

| Tool | Description |
|------|-------------|
| `bash` | Run a shell command |
| `read_file` | Read file contents (with line numbers) |
| `write_file` | Write or create a file |
| `edit_file` | Find-and-replace in a file (exact match) |
| `glob` | List files matching a glob pattern |
| `grep` | Search file contents with regex |

Write operations (`bash`, `write_file`, `edit_file`) require confirmation in the default `WorkspaceWrite` mode.

## Slash commands

| Command | Description |
|---------|-------------|
| `/help` | Show commands and tools |
| `/clear` | Clear conversation history |
| `/compact` | Summarize history and restart with summary as context |
| `/memory` | Show loaded CLAUDE.md content |
| `/exit` | Quit |

## Memory (CLAUDE.md)

On startup, nano-claude-code walks up from the current directory collecting `CLAUDE.md` files and injects them into the system prompt. Create one in your project root to give Claude persistent context:

```markdown
# My Project

This is a FastAPI service. Always use async functions.
Tests live in tests/ and use pytest with a real database — no mocks.
```

This is a simplified version of Claude Code's memory system. Real Claude Code additionally maintains a `~/.claude/memory/` directory with many typed memory files, and uses a Claude Sonnet side-call to select only the ≤5 most relevant files per query.

## Differences from real Claude Code

| Feature | nano-claude-code | Claude Code |
|---------|-----------------|-------------|
| Memory selection | all CLAUDE.md files, always | LLM picks ≤5 relevant files per turn |
| Tool loading | all 6 tools always sent | deferred tools loaded on demand via ToolSearchTool |
| MCP servers | not supported | stdio / SSE / HTTP tool servers |
| Permissions | 3 modes, confirm prompt | fine-grained per-tool allow/deny/ask |
| Background agents | none | memory consolidation (dream), memory extraction |
| Providers | Anthropic API only | Bedrock, Vertex, Foundry |

## Dependencies

- [`anthropic`](https://github.com/anthropics/anthropic-sdk-python) — Anthropic Python SDK
- [`rich`](https://github.com/Textualize/rich) — terminal UI (Live panels, Markdown, spinners)
