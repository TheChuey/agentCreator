"""
tools/project_tools.py
======================

Every executable tool in the headless runtime, consolidated into one module.

One function per tool; each function's docstring is what the LLM "sees":
PromptManager turns the first line into the system prompt's AVAILABLE TOOLS
section, and Ollama derives the JSON tool schema from the function name,
signature, types, and docstring. Keep them precise and self-describing.

Registered tools (IDs in agent.json):
    map_files, read_file, write_text_file, delete_files,
    get_current_date, tell_me_the_date_and_time, search_chat_logs

File tools run against one of three backends, selected per agent (or, for the
standalone CLI, once per process via configure()):

    * a Project Manager bridge (HTTP)          - the Project Manager server
                                                  is the filesystem authority
    * a "direct" Project Manager provider      - in-process filesystem authority
                                                  (used when mounted inside PM)
    * the local disk (default, no provider)    - bare local filesystem

The provider is a small object with a stable surface:

    workspace_root (str)          .relpath(path) -> posix relative (or raises)
    .list_tree() -> nested tree   .read(rel) -> str     .write(rel, content)
    .create(rel, content)         .delete(rel)          .exists(rel) -> bool

Which provider a tool call uses is resolved by current_provider(): the binding
installed for that specific call (tools.registry.resolve_tools) wins over the
process default, so agents running side by side never share filesystem state.

The FileSession (tools/state.py) is per agent, created at build time.
"""

import os
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# DATA STORE (chat memory + tool log)
# ---------------------------------------------------------------------------

from tools.chatlog import search_text as _search_chatlog  # noqa: E402

# ---------------------------------------------------------------------------
# PROVIDER SELECTION
# ---------------------------------------------------------------------------

#: Process-wide default provider (None = operate on the local disk). This is
#: only the fallback for callers that do not bind a provider of their own;
#: per-agent binding goes through the ``_bound_provider`` context variable so
#: two agents can never fight over one module global.
_io: Any = None

#: Provider bound for the duration of a single tool call (see
#: tools.registry.resolve_tools). A ContextVar keeps the binding scoped to
#: the running thread/task, so concurrent agents stay independent.
_bound_provider: ContextVar = ContextVar("tool_provider", default=None)


def configure(provider: Any) -> None:
    """Set the process-wide default provider (None for local disk).

    The provider decides where files live AND how paths are translated. Both
    the HTTP bridge (bridge.client) and the in-process filesystem authority
    (bridge.providers.DirectProjectIO) implement the same surface.

    Prefer per-agent binding (tools.registry.resolve_tools(ids, provider)):
    this global remains for backwards compatibility and for the standalone
    headless CLI.
    """
    global _io
    _io = provider


def current_provider() -> Any:
    """The provider in force right now: the per-call binding, else the default."""
    bound = _bound_provider.get()
    return _io if bound is None else bound


@contextmanager
def using(provider: Any):
    """Activate ``provider`` for the duration of the block."""
    token = _bound_provider.set(provider)
    try:
        yield provider
    finally:
        _bound_provider.reset(token)


# ---------------------------------------------------------------------------
# READ - Docling-powered document reader (IBM Docling)
# ---------------------------------------------------------------------------

# Plain-text formats are read straight off disk (fast path). Everything else
# (PDF/DOCX/PPTX/XLSX/HTML/images/...) goes through IBM Docling's pipeline,
# which returns clean, structurally-formatted markdown.
_PLAIN_TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".log", ".text",
    ".csv", ".tsv",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".py", ".pyw", ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx",
    ".css", ".scss", ".sass", ".xml", ".tex", ".rst",
}


def _is_plain_text(path) -> bool:
    """True for files whose raw text is already the well-formatted content."""
    return Path(str(path)).suffix.lower() in _PLAIN_TEXT_EXTENSIONS


def _unquote_path(value) -> str:
    """Strip one level of surrounding quotes a model may have left on a path.

    Small local models frequently emit tool args that still include the
    double/single quotes from the prompt (e.g. output_path='"E:\\data\\x"').
    Quote characters are invalid inside Windows path components, so passing
    them through makes read/map/write/delete fail with WinError 123 - even
    though the underlying path was perfectly real. Only matching quote pairs
    at the very edges are stripped, and only for string arguments that are
    really paths, so ordinary quoted prose is never mangled.
    """
    v = str(value).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        return v[1:-1]
    return v


_DOCLING_CONVERTERS = {}


def _docling_converter(ocr: bool):
    """Return a cached, lazily-created Docling DocumentConverter.

    The converter is created once per ocr setting and reused across calls so
    the (expensive) pipeline + model artifacts are initialized only once.
    First-ever conversion downloads the layout/OCR models from HuggingFace.
    """
    if ocr not in _DOCLING_CONVERTERS:
        try:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import DocumentConverter, PdfFormatOption
        except ImportError:
            _DOCLING_CONVERTERS[ocr] = None
            return None

        if ocr:
            options = PdfPipelineOptions(do_ocr=True)
            converter = DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
            )
        else:
            converter = DocumentConverter()

        _DOCLING_CONVERTERS[ocr] = converter
    return _DOCLING_CONVERTERS[ocr]


def _convert_with_docling(path: Path, ocr: bool) -> str | None:
    """Return Docling markdown for a binary document, or None when unavailable."""
    converter = _docling_converter(ocr)
    if converter is None:
        return None

    from docling.datamodel.base_models import ConversionStatus

    result = converter.convert(str(path), max_num_pages=400)
    if result.status is ConversionStatus.FAILURE:
        errors = "; ".join(e.error_message for e in getattr(result, "errors", []))
        raise ValueError(errors or "Docling could not convert the document.")
    return result.document.export_to_markdown()


def _read_local_file(p: Path, ocr: bool) -> dict:
    """Read a file from the local disk (text direct, binary via Docling)."""
    if _is_plain_text(p):
        return {
            "success": True,
            "tool": "read_file",
            "data": {
                "path": str(p),
                "filename": p.name,
                "file_type": p.suffix.lower(),
                "extracted_content": p.read_text(encoding="utf-8", errors="replace"),
                "status": "success",
            },
            "error": None,
        }
    markdown = _convert_with_docling(p, ocr)
    if markdown is None:
        return {
            "success": False,
            "tool": "read_file",
            "data": {},
            "error": "Docling is not installed. Install it with `pip install docling` "
                     "to read PDF/DOCX/PPTX/XLSX/HTML/image files.",
        }
    return {
        "success": True,
        "tool": "read_file",
        "data": {
            "path": str(p),
            "filename": p.name,
            "file_type": p.suffix.lower(),
            "extracted_content": markdown,
            "status": "success",
        },
        "error": None,
    }


def read_file(path: str, ocr: bool = True) -> dict:
    """Reads a file and returns its content as well-formatted text (markdown).

    Use this tool whenever you need the contents of a document, source file,
    or any file on disk. It returns the extracted content ready to use.

    Plain text and code files (.txt, .md, .log, .json, source code, ...) are
    read directly. All other formats - PDF, DOCX, PPTX, XLSX, HTML, images -
    are converted by IBM Docling into clean, structured markdown (OCR on by
    default for scanned PDFs). When a Project Manager is connected, project
    files are read through it (the Project Manager is the filesystem owner).

    Args:
        path (str): Absolute path to the file to read (relative to the
            Project Manager workspace when one is connected).
        ocr (bool): When True (default), optical character recognition is
            enabled for PDFs so scanned/rotated pages can be read.

    Returns:
        dict: {"success": bool, "tool": "read_file", "data": {...}, "error": str|None}
            data keys: path, filename, file_type, extracted_content, status
    """
    raw = _unquote_path(path)
    io = current_provider()

    if io is not None:
        # Project Manager is the filesystem authority. Plain text is read
        # through the provider; binary documents are converted locally when
        # the file is reachable on this machine, otherwise the provider's
        # own answer (or error) is returned.
        try:
            rel = io.relpath(raw)
        except Exception as exc:
            return {"success": False, "tool": "read_file", "data": {}, "error": str(exc)}

        if _is_plain_text(rel):
            try:
                content = io.read(rel)
                return {
                    "success": True,
                    "tool": "read_file",
                    "data": {
                        "path": str(Path(io.workspace_root) / rel),
                        "path_relative": rel,
                        "filename": Path(rel).name,
                        "file_type": Path(rel).suffix.lower(),
                        "extracted_content": content,
                        "status": "success",
                    },
                    "error": None,
                }
            except Exception as exc:
                return {"success": False, "tool": "read_file", "data": {}, "error": str(exc)}

        # Binary document: best-effort local Docling conversion, then the
        # provider's read (which may serve extracted text or refuse).
        local = Path(io.workspace_root) / rel
        if local.is_file():
            try:
                return _read_local_file(local, ocr)
            except Exception as exc:
                pass
        try:
            content = io.read(rel)
            return {
                "success": True,
                "tool": "read_file",
                "data": {
                    "path": str(Path(io.workspace_root) / rel),
                    "path_relative": rel,
                    "filename": Path(rel).name,
                    "file_type": Path(rel).suffix.lower(),
                    "extracted_content": content,
                    "status": "success",
                },
                "error": None,
            }
        except Exception as exc:
            return {"success": False, "tool": "read_file", "data": {}, "error": str(exc)}

    p = Path(raw)
    if not p.exists() or not p.is_file():
        return {
            "success": False,
            "tool": "read_file",
            "data": {},
            "error": f"File '{path}' not found."
        }

    try:
        return _read_local_file(p, ocr)
    except Exception as e:
        return {"success": False, "tool": "read_file", "data": {}, "error": str(e)}


# ---------------------------------------------------------------------------
# MAP - directory inspection
# ---------------------------------------------------------------------------

DEFAULT_IGNORE_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".idea", ".vscode"}


def _flatten_tree(entries: list, prefix: str = "") -> list[dict]:
    """Flatten a nested provider tree into one flat list of {path, type, name, size}."""
    flat = []
    for entry in entries or []:
        name = entry.get("name", "")
        rel = entry.get("path", "")
        if not rel and name:
            rel = f"{prefix}/{name}" if prefix else name
        flat.append({
            "name": name or Path(rel).name,
            "path": rel,
            "type": entry.get("type", "file"),
        })
        for child in entry.get("children") or []:
            flat.extend(_flatten_tree([child], prefix=rel))
    return flat


def _map_entries_local(root: Path) -> list[dict]:
    """os.walk the local disk; returns flat {name, path, type, level} entries."""
    files_data = []
    for current_dir, dirs, files in os.walk(root, topdown=True):
        depth = len(Path(current_dir).relative_to(root).parts)
        dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_DIRS]
        for d in dirs:
            full = Path(current_dir) / d
            files_data.append({"name": d, "path": str(full), "type": "directory", "level": depth + 1})
        for f in files:
            full = Path(current_dir) / f
            files_data.append({"name": f, "path": str(full), "type": "file", "level": depth + 1})
    return files_data


def map_files(path: str, max_depth: int = 8, max_entries: int = 5000) -> dict:
    """Inspects a directory and returns a structured list of its files and folders.

    Use this tool to see what exists on disk before reading, writing, or
    deleting anything. Returns every file and subfolder under the given
    directory (to max_depth), excluding ordinary noise like .git, .venv, and
    __pycache__. Folders are listed with their subpaths so you know exactly
    where a file lives before you touch it.

    Args:
        path (str): Absolute path to the directory to inspect, or a path
            relative to the Project Manager workspace when one is connected.
        max_depth (int): Maximum subdirectory depth to descend into (default 8).
        max_entries (int): Maximum number of entries to return (default 5000).

    Returns:
        dict: {"success": bool, "tool": "map_files", "data": {...}, "error": str|None}
            data keys: files (list of {name, path, extension, type, parent, level}),
                        truncated (bool), max_entries (int)
    """
    # Small local models sometimes render ints as strings ("5000"); coerce so
    # the `>=` comparisons below never crash on a type mismatch.
    if isinstance(max_depth, str) and max_depth.strip().isdigit():
        max_depth = int(max_depth)
    if isinstance(max_entries, str) and max_entries.strip().isdigit():
        max_entries = int(max_entries)
    raw = _unquote_path(path)
    io = current_provider()

    if io is not None:
        try:
            base = io.relpath(raw)
        except Exception as exc:
            return {"success": False, "tool": "map_files", "data": {}, "error": str(exc)}
        try:
            flat = _flatten_tree(io.list_tree())
        except Exception as exc:
            return {"success": False, "tool": "map_files", "data": {}, "error": str(exc)}

        base = base.strip("/")
        base_parts = tuple(base.split("/")) if base else ()
        files_data = []
        for entry in flat:
            rel = entry.get("path", "").replace("\\", "/").strip("/")
            if not rel:
                continue
            rel_parts = tuple(rel.split("/"))
            if base_parts and rel_parts[:len(base_parts)] != base_parts:
                continue
            if base_parts and len(rel_parts) == len(base_parts):
                continue  # the requested directory itself, not an entry inside it
            level = len(rel_parts) - len(base_parts)
            if level > max_depth:
                continue
            if base_parts and any(p in DEFAULT_IGNORE_DIRS for p in rel_parts):
                continue
            files_data.append({
                "name": entry.get("name") or rel_parts[-1],
                "path": str(Path(io.workspace_root) / rel),
                "path_relative": rel,
                "extension": Path(rel).suffix,
                "type": entry.get("type", "file"),
                "parent": rel_parts[-2] if len(rel_parts) >= 2 else "",
                "level": level,
            })
            if len(files_data) >= max_entries:
                break
        truncated = len(files_data) >= max_entries
        return {
            "success": True,
            "tool": "map_files",
            "data": {"files": files_data, "truncated": truncated, "max_entries": max_entries},
            "error": None,
        }

    root = Path(raw)
    if not root.exists() or not root.is_dir():
        return {
            "success": False,
            "tool": "map_files",
            "data": {},
            "error": f"Path '{path}' is not a valid directory."
        }

    files_data = []
    for current_dir, dirs, files in os.walk(root, topdown=True):
        depth = len(Path(current_dir).relative_to(root).parts)
        if depth >= max_depth:
            dirs[:] = []
        else:
            dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_DIRS]

        for d in dirs:
            if len(files_data) >= max_entries:
                break
            full = Path(current_dir) / d
            files_data.append({
                "name": d,
                "path": str(full),
                "extension": "",
                "type": "directory",
                "parent": Path(current_dir).name if Path(current_dir) != root else "",
                "level": depth + 1,
            })

        for f in files:
            if len(files_data) >= max_entries:
                break
            full = Path(current_dir) / f
            files_data.append({
                "name": f,
                "path": str(full),
                "extension": Path(f).suffix,
                "type": "file",
                "parent": Path(current_dir).name if Path(current_dir) != root else "",
                "level": depth + 1,
            })

        if len(files_data) >= max_entries:
            break

    truncated = len(files_data) >= max_entries
    return {
        "success": True,
        "tool": "map_files",
        "data": {
            "files": files_data,
            "truncated": truncated,
            "max_entries": max_entries,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# WRITE - file creation
# ---------------------------------------------------------------------------

def write_text_file(name: str, content: str, output_path: str, overwrite: bool = False) -> dict:
    """Creates a text file containing the given content.

    Use this tool to save any text or code you have produced to disk. The
    parent directory is created automatically, so you do not need a separate
    "create folder" step. By default an existing file with the same name is
    NOT overwritten - pass overwrite=True when you intentionally want to.

    Args:
        name (str): File name to write, e.g. "summary.txt".
        content (str): Full text content to write into the file.
        output_path (str): Directory in which to create the file (inside the
            Project Manager workspace when one is connected).
        overwrite (bool): Whether to overwrite the file if it already exists
            (default False).

    Returns:
        dict: {"success": bool, "tool": "write_text_file", "data": {...}, "error": str|None}
            data keys: filename, path, type, size, status (built on success)
    """
    if not name or content is None or not output_path:
        return {
            "success": False,
            "tool": "write_text_file",
            "data": {},
            "error": "Missing required arguments. Need name (file name), content (text), and output_path (folder)."
        }

    io = current_provider()

    if io is not None:
        try:
            rel_dir = io.relpath(_unquote_path(output_path)).strip("/")
        except Exception as exc:
            return {"success": False, "tool": "write_text_file", "data": {}, "error": str(exc)}
        rel_file = f"{rel_dir}/{_unquote_path(name)}" if rel_dir else f"{_unquote_path(name)}"
        try:
            if overwrite:
                io.write(rel_file, content)
            else:
                io.create(rel_file, content)
        except Exception as exc:
            return {"success": False, "tool": "write_text_file", "data": {}, "error": str(exc)}
        absolute = str(Path(io.workspace_root) / rel_file)
        return {
            "success": True,
            "tool": "write_text_file",
            "data": {
                "filename": _unquote_path(name),
                "path": absolute,
                "path_relative": rel_file,
                "type": "text/plain",
                "size": 0,
                "status": "written",
            },
            "error": None,
        }

    try:
        out_dir = Path(_unquote_path(output_path))
        out_dir.mkdir(parents=True, exist_ok=True)
        file_path = out_dir / _unquote_path(name)

        if file_path.exists() and not overwrite:
            return {
                "success": False,
                "tool": "write_text_file",
                "data": {},
                "error": f"File '{file_path}' already exists and overwrite is set to False."
            }

        file_path.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "tool": "write_text_file",
            "data": {
                "filename": name,
                "path": str(file_path),
                "type": "text/plain",
                "size": file_path.stat().st_size,
                "status": "written",
            },
            "error": None,
        }
    except Exception as e:
        return {"success": False, "tool": "write_text_file", "data": {}, "error": str(e)}


# ---------------------------------------------------------------------------
# DELETE - two-step approval-safe deletion
# ---------------------------------------------------------------------------

def delete_files(file_list: list, approved: bool = False) -> dict:
    """Deletes files ONLY after explicit approval has been given.

    Deleting is permanent. Calling this tool with approved=False (the safe
    default) only PREPARES the deletion. Call it a second time with
    approved=True to actually remove the files; the runtime additionally
    blocks any path that was never proposed in the first (approved=False) call.

    Args:
        file_list (list): List of file paths to delete.
        approved (bool): Must be True to actually delete. False only records
            the pending request (two-step confirmation).

    Returns:
        dict: {"success": bool, "tool": "delete_files", "data": {...}, "error": str|None}
            data keys: results (path -> "deleted"/"file_not_found"/"error: ..."),
                        or pending_files (list) when approval is still required
    """
    if not file_list:
        return {
            "success": False,
            "tool": "delete_files",
            "data": {},
            "error": "No files provided for deletion."
        }

    if not approved:
        return {
            "success": False,
            "tool": "delete_files",
            "data": {"pending_files": file_list},
            "error": "Deletion requires explicit approval. Set approved=True to finalize."
        }

    io = current_provider()
    results = {}
    for f_path in file_list:
        try:
            if io is not None:
                rel = io.relpath(f_path)
                if io.exists(rel):
                    io.delete(rel)
                    results[f_path] = "deleted" if not io.exists(rel) else "failed_to_verify"
                else:
                    results[f_path] = "file_not_found"
            else:
                p = Path(_unquote_path(f_path))
                if p.exists() and p.is_file():
                    p.unlink()
                    results[f_path] = "deleted" if not p.exists() else "failed_to_verify"
                else:
                    results[f_path] = "file_not_found"
        except Exception as e:
            results[f_path] = f"error: {str(e)}"

    all_success = all(v == "deleted" for v in results.values())
    return {
        "success": all_success,
        "tool": "delete_files",
        "data": {"results": results},
        "error": None if all_success else "One or more files failed to delete.",
    }


# ---------------------------------------------------------------------------
# DATE / TIME
# ---------------------------------------------------------------------------

def get_current_date() -> str:
    """Returns the real current calendar date (e.g. 'Monday, January 05, 2026').

    Use this tool when you need to know today's date - for example when a
    user asks "what day is it", when dating a response, or when reasoning
    about relative dates. No arguments.
    """
    from datetime import datetime
    return datetime.now().strftime("%A, %B %d, %Y")


def tell_me_the_date_and_time() -> str:
    """Returns the current date and time down to the second.

    Use this tool for anything needing the moment now (date + time), like
    timestamps, "what time is it", or checking elapsed time. No arguments.
    """
    from datetime import datetime
    now = datetime.now()
    return f"The current date and time is {now.strftime('%Y-%m-%d %H:%M:%S')}"


# ---------------------------------------------------------------------------
# SEARCH - chat transcript / memory recall
# ---------------------------------------------------------------------------

def search_chat_logs(query: str) -> str:
    """Searches past chat transcripts for a keyword and returns the matching segments.

    Use this tool to recall what was discussed in earlier conversations: this
    is the agent's long-term memory. It searches the saved plain-text chat log
    (data/chatlog/chat.log) and returns the matching turns with their speaker.

    Args:
        query (str): The search keyword, term, or phrase to look up.

    Returns:
        str: Formatted search results ('' when nothing matches).
    """
    try:
        result = _search_chatlog(query)
        if not result:
            return f"No matches found in the chat log for the query: '{query}'."
        return result
    except Exception as e:
        return f"Error executing chat log search: {e}"


# Keep the module importable in environments without fancy deps (mirrors the
# original module header which inserted the app root into sys.path).
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))