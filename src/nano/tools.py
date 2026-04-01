"""
Tool registry and executor for nano-claude-code.
Six tools mirroring Claude Code's minimal built-in set:
  bash, read_file, write_file, edit_file, glob, grep
"""

import glob as glob_module
import os
import re
import subprocess
from pathlib import Path

from .permissions import Permissions

# ---------------------------------------------------------------------------
# Tool schemas (sent to the Anthropic API)
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "bash",
        "description": (
            "Run a shell command and return its stdout + stderr. "
            "Use for system operations, running scripts, installing packages, etc. "
            "Prefer read-only commands when possible."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 30).",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file at the given path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative file path."},
                "offset": {"type": "integer", "description": "Line number to start reading from (1-indexed)."},
                "limit": {"type": "integer", "description": "Maximum number of lines to read."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file, creating it or overwriting it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write to."},
                "content": {"type": "string", "description": "The full content to write."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Replace an exact string in a file. "
            "old_string must match exactly (including whitespace). "
            "Fails if old_string is not found or appears more than once."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to edit."},
                "old_string": {"type": "string", "description": "The exact text to find."},
                "new_string": {"type": "string", "description": "The replacement text."},
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    {
        "name": "glob",
        "description": "List files matching a glob pattern (e.g. '**/*.py').",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern to match."},
                "path": {"type": "string", "description": "Directory to search in (default: cwd)."},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "grep",
        "description": "Search file contents for a regex pattern. Returns matching lines with file/line info.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern to search for."},
                "path": {"type": "string", "description": "File or directory to search (default: cwd)."},
                "glob": {"type": "string", "description": "Glob filter for files (e.g. '*.py')."},
                "case_insensitive": {"type": "boolean", "description": "Case-insensitive match."},
            },
            "required": ["pattern"],
        },
    },
]


def get_tools() -> list[dict]:
    return TOOLS


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def tool_bash(inputs: dict, permissions: Permissions) -> str:
    command = inputs.get("command", "")
    timeout = inputs.get("timeout", 30)

    if not permissions.can_bash():
        return "Error: bash is not allowed in ReadOnly mode."
    if not permissions.confirm_bash(command):
        return "Aborted: user declined to run the command."

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += "\n[stderr]\n" + result.stderr
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s."
    except Exception as e:
        return f"Error: {e}"


def tool_read_file(inputs: dict) -> str:
    path = inputs.get("path", "")
    offset = inputs.get("offset", 1)
    limit = inputs.get("limit", None)

    try:
        p = Path(path)
        if not p.exists():
            return f"Error: file not found: {path}"
        lines = p.read_text(errors="replace").splitlines()
        start = max(0, offset - 1)
        end = start + limit if limit else len(lines)
        selected = lines[start:end]
        # Add line numbers like Claude Code's Read tool
        numbered = [f"{start + i + 1}\t{line}" for i, line in enumerate(selected)]
        return "\n".join(numbered)
    except Exception as e:
        return f"Error: {e}"


def tool_write_file(inputs: dict, permissions: Permissions) -> str:
    path = inputs.get("path", "")
    content = inputs.get("content", "")

    if not permissions.can_write():
        return "Error: file writes are not allowed in ReadOnly mode."
    if not permissions.confirm_write(path):
        return "Aborted: user declined to write the file."

    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Written {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def tool_edit_file(inputs: dict, permissions: Permissions) -> str:
    path = inputs.get("path", "")
    old_string = inputs.get("old_string", "")
    new_string = inputs.get("new_string", "")

    if not permissions.can_write():
        return "Error: file writes are not allowed in ReadOnly mode."

    try:
        p = Path(path)
        if not p.exists():
            return f"Error: file not found: {path}"
        content = p.read_text(errors="replace")
        count = content.count(old_string)
        if count == 0:
            return "Error: old_string not found in file."
        if count > 1:
            return f"Error: old_string appears {count} times — must be unique."
        if not permissions.confirm_write(path):
            return "Aborted: user declined to edit the file."
        new_content = content.replace(old_string, new_string, 1)
        p.write_text(new_content)
        return f"Edited {path} — replaced {len(old_string)} chars with {len(new_string)} chars."
    except Exception as e:
        return f"Error: {e}"


def tool_glob(inputs: dict) -> str:
    pattern = inputs.get("pattern", "*")
    base = inputs.get("path", os.getcwd())

    try:
        matches = glob_module.glob(pattern, root_dir=base, recursive=True)
        matches.sort()
        if not matches:
            return "(no matches)"
        return "\n".join(matches[:500])  # cap at 500 paths
    except Exception as e:
        return f"Error: {e}"


def tool_grep(inputs: dict) -> str:
    pattern = inputs.get("pattern", "")
    path = inputs.get("path", os.getcwd())
    file_glob = inputs.get("glob", None)
    case_insensitive = inputs.get("case_insensitive", False)

    flags = re.IGNORECASE if case_insensitive else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return f"Error: invalid regex: {e}"

    results: list[str] = []
    search_path = Path(path)

    def search_file(fp: Path):
        try:
            for i, line in enumerate(fp.read_text(errors="replace").splitlines(), 1):
                if regex.search(line):
                    results.append(f"{fp}:{i}:{line}")
                    if len(results) >= 200:
                        return
        except Exception:
            pass

    if search_path.is_file():
        search_file(search_path)
    else:
        glob_pat = file_glob or "**/*"
        for fp in search_path.glob(glob_pat):
            if fp.is_file():
                search_file(fp)
            if len(results) >= 200:
                break

    if not results:
        return "(no matches)"
    return "\n".join(results)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def execute_tool(name: str, inputs: dict, permissions: Permissions) -> str:
    match name:
        case "bash":
            return tool_bash(inputs, permissions)
        case "read_file":
            return tool_read_file(inputs)
        case "write_file":
            return tool_write_file(inputs, permissions)
        case "edit_file":
            return tool_edit_file(inputs, permissions)
        case "glob":
            return tool_glob(inputs)
        case "grep":
            return tool_grep(inputs)
        case _:
            return f"Error: unknown tool '{name}'"
