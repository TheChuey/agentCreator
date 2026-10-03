"""
Project Manager Filesystem
==========================

This module is responsible for managing the physical
project filesystem.

Responsibilities:
    - Create the basic project structure.
    - Create/read project.json.
    - Read the project filesystem.
    - Read files.
    - Write files.
    - Create files.
    - Create directories.
    - Rename files/directories.
    - Delete files/directories.

The web server does NOT contain filesystem logic.
server.py calls this module.

Where the rules live
--------------------

**This module no longer decides what is reachable.** The browse-root table,
the containment check and the writability floor moved to
``ws_controlPanel.paths``, so that the permission engine and the filesystem
agree by construction rather than by two copies staying in sync. Everything
that used to be defined here is imported from there and re-exported under its
original name, so ``BROWSE_ROOTS``, ``resolve_project_path``,
``require_writable`` and the rest keep working for every existing caller --
``operations.py``, ``paths.py``, ``chat.py``, ``toollog.py`` and
``bridge/providers.py`` all continue to call the names they always called.

Two of those re-exports are load-bearing for the rest of the repository:

* ``BROWSE_ROOTS`` is an alias of the panel's ``ROOTS``, not a copy. Adding a
  root in one place adds it in both.
* ``require_writable`` is now the panel's floor check, which
  ``ws_controlPanel.gate.require_path`` calls *in addition to* the per-agent
  rules rather than instead of them. No agent grant can make a read-only root
  writable.

A second, independent containment check used to live in
``project_manager/interface/routers/agents.py``. It has been deleted; that
router calls ``ws_controlPanel.paths.resolve_agent_path`` instead.
"""

from __future__ import annotations

import errno
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

# The control panel is a repository sibling of this package, so reaching it
# means putting the repository root on the path first. The repository already
# does this for ``headless_app`` in five places; this is the panel's own
# copy, and it has to run before the imports below.
_AGENTCREATOR_ROOT = Path(
    __file__
).resolve().parents[2]

if str(
    _AGENTCREATOR_ROOT
) not in sys.path:

    sys.path.insert(
        0,
        str(_AGENTCREATOR_ROOT),
    )

from ws_controlPanel import paths as _paths


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PARAMETERS_DIR = Path(__file__).resolve().parent

#: The application package directory. Note this is *not* the repository
#: root -- ``AGENTCREATOR_ROOT`` is -- and the two are frequently confused.
REPO_ROOT = PARAMETERS_DIR.parent

AGENTCREATOR_ROOT = _AGENTCREATOR_ROOT

#: The managed project content, the browse roots, and the single containment
#: check. All owned by the control panel; re-exported here so the rest of the
#: server keeps one name for each of them.
PROJECT_ROOT = _paths.PROJECT_ROOT
PROJECT_JSON = PROJECT_ROOT / "project.json"
SOURCE_FILES_ROOT = _paths.SOURCE_FILES_ROOT
TEST_ENVIRONMENT_ROOT = _paths.TEST_ENVIRONMENT_ROOT

#: The browse roots. An alias, not a copy: see the module docstring.
BROWSE_ROOTS = _paths.ROOTS

#: The containment check and the writability floor.
resolve_project_path = _paths.resolve_project_path
split_root = _paths.split_root
is_writable_root = _paths.is_writable_root
resolve_browse_target = _paths.resolve_browse_target
resolve_browse_path = _paths.resolve_browse_path
require_writable = _paths.require_writable
to_root_qualified = _paths.to_root_qualified

#: Editability limits and the file-type gate.
MAX_EDITABLE_BYTES = _paths.MAX_EDITABLE_BYTES
TEXT_EXTENSIONS = _paths.TEXT_EXTENSIONS
IGNORED_DIRECTORIES = _paths.IGNORED_DIRECTORIES
should_ignore = _paths.should_ignore


# ============================================================
# STANDARD PROJECT FOLDERS
# ============================================================

PROJECT_FOLDERS = [
    "documentation",
    "project_scope",
    "To Do",
    "updates",
    "config",
    "data",
    "Tests"
]


# ============================================================
# BROWSER ROOTS
# ============================================================

# BROWSE_ROOTS, MAX_EDITABLE_BYTES, TEXT_EXTENSIONS, IGNORED_DIRECTORIES and
# should_ignore are imported from ``ws_controlPanel.paths`` at the top of this
# module. They used to be defined here. They are not redefined here now,
# because a second table of what is writable is exactly the kind of copy that
# drifts out of step with the permission engine and then quietly disagrees
# with it.


# ============================================================
# FILE TYPES
# ============================================================

# TEXT_EXTENSIONS is imported from ``ws_controlPanel.paths``. It is the write
# type gate: ``write_file`` and ``create_file`` below both refuse anything
# whose suffix is not in it, so a rename cannot be used to slip a binary past
# the text-only editor.


# ============================================================
# DEFAULT PROJECT INFORMATION
# ============================================================

DEFAULT_PROJECT = {
    "name": PROJECT_ROOT.name,
    "version": "1.0.0",
    "workspace_version": "1.0",
}
# ============================================================
# RE-EXPORTED FROM THE CONTROL PANEL
# ============================================================

# The six functions that used to live between here and the browser tree --
# resolve_project_path, split_root, is_writable_root, resolve_browse_target,
# resolve_browse_path and require_writable -- are now imported from
# ws_controlPanel.paths at the top of this module and re-exported under their
# original names.
#
# The point of moving them is not tidiness. ``ws_controlPanel.gate`` has to
# enforce the same containment and the same writability floor that these
# callers enforce, and it cannot import this package without creating a cycle:
# the panel is imported *by* this module. So the rules live in the panel and
# flow outward, rather than being copied inward.
#
# Every caller below is unchanged, and that is the test of the move:
#   operations.py            seven require_writable calls, all still named the same
#   bridge/providers.py      three more, plus resolve_browse_path
#   routers/chat.py          resolve_project_path for the mirrored log
#   routers/toollog.py       resolve_project_path to reach an agent.json
#   routers/paths.py         rename, through operations



def read_browse_filesystem(
    roots: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Build the browser tree.

    The top level is always the configured ``BROWSE_ROOTS`` folders,
    so the tree itself acts as the folder switcher. Every node path
    is prefixed with its root name.

    Roots that do not exist on disk are skipped.

    Args:
        roots:
            Names to include, or None for all of them. This narrows
            what a page is *shown*, nothing more: the omitted roots
            stay in ``BROWSE_ROOTS``, so their paths still resolve
            for read, write and delete. A page that lists one root
            can therefore hand a file from another root to a page
            that does list it.

    Returns:
        JSON-friendly tree, in ``BROWSE_ROOTS`` declaration order.
    """

    wanted = None if roots is None else set(roots)

    results: list[dict[str, Any]] = []

    for root_name, config in BROWSE_ROOTS.items():

        if wanted is not None and root_name not in wanted:

            continue

        root_path: Path = config["path"]

        if not root_path.is_dir():

            continue

        results.append(
            {
                "name": root_name,
                "path": root_name,
                "type": "directory",
                "root": root_name,
                "writable": bool(
                    config.get("writable", False)
                ),
                "children": read_filesystem(
                    root_path,
                    _root=root_path,
                    _prefix=root_name,
                ),
            }
        )

    return results


# ============================================================
# PROJECT INITIALIZATION
# ============================================================

def build_project_filesystem() -> None:
    """
    Create the standard Project Manager filesystem.

    Existing files and folders are never deleted.

    Safe to run every time the server starts.
    """

    # --------------------------------------------------------
    # Create standard directories
    # --------------------------------------------------------

    for folder_name in PROJECT_FOLDERS:

        folder_path = (
            PROJECT_ROOT / folder_name
        )

        folder_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    # --------------------------------------------------------
    # Create project.json
    # --------------------------------------------------------

    if not PROJECT_JSON.exists():

        PROJECT_JSON.write_text(
            json.dumps(
                DEFAULT_PROJECT,
                indent=4,
            ),
            encoding="utf-8",
        )


# ============================================================
# PROJECT INFORMATION
# ============================================================

def read_project_info() -> dict[str, Any]:
    """
    Read project.json.

    Returns:
        Project information dictionary.
    """

    if not PROJECT_JSON.exists():

        return DEFAULT_PROJECT.copy()

    try:

        return json.loads(
            PROJECT_JSON.read_text(
                encoding="utf-8"
            )
        )

    except (
        json.JSONDecodeError,
        OSError,
    ):

        return DEFAULT_PROJECT.copy()


# ============================================================
# FILE FILTERING
# ============================================================

def is_text_file(path: Path) -> bool:
    """
    Determine whether a file should be editable.

    Files without extensions are treated as text files.
    """

    if path.suffix == "":
        return True

    return (
        path.suffix.lower()
        in TEXT_EXTENSIONS
    )


def is_oversized(path: Path) -> bool:
    """
    Determine whether a file is too large to edit in the browser.

    Very large files are marked non-editable so the editor does
    not try to render a multi-megabyte document.
    """

    try:

        return path.stat().st_size > MAX_EDITABLE_BYTES

    except OSError:

        return False


# ============================================================
# READ FILESYSTEM
# ============================================================

def read_filesystem(
    directory: Path | None = None,
    _root: Path | None = None,
    _prefix: str = "",
) -> list[dict[str, Any]]:
    """
    Recursively read the project filesystem.

    Args:
        directory:
            Directory to list.
        _root:
            Root the emitted paths are relative to.
        _prefix:
            Prepended to every emitted path. Used by
            :func:`read_browse_filesystem` so each node carries its
            browser-root name (``source_files/APP_CODE_SNAPSHOT.md``),
            which is what lets the API resolve the path back to its root.

    Returns:
        JSON-friendly file/folder tree.
    """

    if directory is None:

        directory = PROJECT_ROOT

    if _root is None:

        _root = directory

    results: list[dict[str, Any]] = []

    try:

        children = sorted(
            directory.iterdir(),
            key=lambda item: (
                not item.is_dir(),
                item.name.lower(),
            ),
        )

    except (
        OSError,
        PermissionError,
    ):

        return results

    for child in children:

        if should_ignore(child):

            continue

        relative_path = child.relative_to(
            _root
        )

        relative_path = str(
            relative_path
        ).replace(
            "\\",
            "/",
        )

        if _prefix:

            relative_path = (
                f"{_prefix}/{relative_path}"
            )

        # ----------------------------------------------------
        # DIRECTORY
        # ----------------------------------------------------

        if child.is_dir():

            results.append(
                {
                    "name": child.name,
                    "path": relative_path,
                    "type": "directory",
                    "children": read_filesystem(
                        child,
                        _root=_root,
                        _prefix=_prefix,
                    ),
                }
            )

        # ----------------------------------------------------
        # FILE
        # ----------------------------------------------------

        else:

            try:

                size = child.stat().st_size

            except OSError:

                size = 0

            results.append(
                {
                    "name": child.name,
                    "path": relative_path,
                    "type": "file",
                    "size": size,
                    "editable": (
                        is_text_file(child)
                        and not is_oversized(child)
                    ),
                }
            )

    return results


# ============================================================
# PROJECT STATE
# ============================================================

def get_project_state() -> dict[str, Any]:
    """
    Return complete project information.

    This is the primary function used by server.py.
    """

    return {
        "project": read_project_info(),
        "root": str(PROJECT_ROOT),
        "filesystem": read_filesystem(),
    }


# ============================================================
# READ FILE
# ============================================================

def read_file(
    relative_path: str,
    root: Path | None = None,
) -> str:
    """
    Read a text file.

    Args:
        relative_path:
            Project-relative file path.
        root:
            Filesystem root. Defaults to the managed workspace.

    Returns:
        File contents.

    Raises:
        ValueError:
            Invalid path or file type.
        FileNotFoundError:
            File does not exist.
    """

    file_path = resolve_project_path(
        relative_path,
        root,
    )

    if not file_path.exists():

        raise FileNotFoundError(
            "File not found."
        )

    if not file_path.is_file():

        raise ValueError(
            "Path is not a file."
        )

    if not is_text_file(file_path):

        raise ValueError(
            "This file type is not editable."
        )

    try:

        return file_path.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:

        raise ValueError(
            "File is not a UTF-8 text file."
        )


# ============================================================
# WRITE FILE
# ============================================================

def write_file(
    relative_path: str,
    content: str,
    root: Path | None = None,
) -> None:
    """
    Create or overwrite a text file.

    Parent directories are automatically created.
    """

    file_path = resolve_project_path(
        relative_path,
        root,
    )

    if not is_text_file(file_path):

        raise ValueError(
            "This file type cannot be edited."
        )

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path.write_text(
        content,
        encoding="utf-8",
    )


# ============================================================
# CREATE FILE
# ============================================================

def create_file(
    relative_path: str,
    content: str = "",
    root: Path | None = None,
) -> None:
    """
    Create a new file.

    Refuses to overwrite an existing file.
    """

    file_path = resolve_project_path(
        relative_path,
        root,
    )

    if file_path.exists():

        raise FileExistsError(
            "A file or directory with that "
            "name already exists."
        )

    if not is_text_file(file_path):

        raise ValueError(
            "This file type cannot be created "
            "by the text editor."
        )

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path.write_text(
        content,
        encoding="utf-8",
    )


# ============================================================
# CREATE DIRECTORY
# ============================================================

def create_directory(
    relative_path: str,
    root: Path | None = None,
) -> None:
    """
    Create a directory.
    """

    directory = resolve_project_path(
        relative_path,
        root,
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )


# ============================================================
# RENAME
# ============================================================

def rename_path(
    old_path: str,
    new_path: str,
    root: Path | None = None,
) -> None:
    """
    Rename or move a file/directory within the active root.

    Both paths must remain inside the active root.
    """

    source = resolve_project_path(
        old_path,
        root,
    )

    destination = resolve_project_path(
        new_path,
        root,
    )

    if not source.exists():

        raise FileNotFoundError(
            "The source path does not exist."
        )

    if destination.exists():

        raise FileExistsError(
            "The destination already exists."
        )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    source.rename(
        destination
    )


# ============================================================
# DELETE
# ============================================================

def delete_path(
    relative_path: str,
    root: Path | None = None,
) -> None:
    """
    Delete a file or directory.

    Directories are deleted recursively through
    :func:`remove_tree`, which tolerates a tree that is still
    settling instead of leaving it half-deleted.

    The active root itself cannot be deleted.
    """

    target = resolve_project_path(
        relative_path,
        root,
    )

    if target == root or target == PROJECT_ROOT:

        raise ValueError(
            "The project root cannot be deleted."
        )

    if not target.exists():

        raise FileNotFoundError(
            "Path not found."
        )

    if target.is_dir():

        remove_tree(target)

    else:

        target.unlink()


# ============================================================
# RECURSIVE DELETE
# ============================================================

# Windows reports a directory that is still changing as WinError 5
# (access denied), 32 (file in use) or 145 (directory not empty).
# Those mean "not settled yet", not "you may not do this", so they are
# retried. Anything else is a real refusal and propagates at once.

TRANSIENT_DELETE_WIN_ERRORS = frozenset({5, 32, 145})

TRANSIENT_DELETE_ERRNOS = frozenset({
    errno.ENOTEMPTY,
    errno.EACCES,
    errno.EPERM,
})

#: Attempts before falling back to a manual bottom-up removal.
DELETE_ATTEMPTS = 3

#: Backoff between attempts, in seconds.
DELETE_BACKOFF = 0.05


def is_transient_delete_error(
    error: OSError,
) -> bool:
    """
    Whether a delete failure is worth retrying.

    Args:
        error:
            The failure raised by the delete attempt.

    Returns:
        True when the failure means "the tree has not settled yet".
    """

    win_error = getattr(
        error,
        "winerror",
        None,
    )

    if win_error is not None:

        return (
            win_error
            in TRANSIENT_DELETE_WIN_ERRORS
        )

    return (
        error.errno
        in TRANSIENT_DELETE_ERRNOS
    )


def remove_tree_manual(
    target: Path,
) -> None:
    """
    Remove a directory tree bottom-up.

    The last resort for :func:`remove_tree`: ``shutil.rmtree`` has
    already failed, so every entry is unlinked individually and each
    directory is then removed empty. Entries that vanished on their own
    are ignored, since a retry race means the work is already done.

    Raises:
        OSError:
            If an entry survives.
    """

    for parent, directories, files in os.walk(
        target,
        topdown=False,
    ):

        for name in files:

            child = Path(parent) / name

            try:

                # A read-only attribute is the usual reason unlink is
                # refused, and clearing it is harmless.
                os.chmod(child, 0o666)

            except OSError:
                pass

            try:

                child.unlink()

            except FileNotFoundError:
                pass

        for name in directories:

            try:

                (Path(parent) / name).rmdir()

            except FileNotFoundError:
                pass

    target.rmdir()


def remove_tree(
    target: Path,
) -> None:
    """
    Delete a directory tree, surviving a tree that is still settling.

    A bare ``shutil.rmtree`` is not enough: on a filesystem without
    transactional deletes (exFAT, for instance) it can fail partway
    with "directory not empty" and leave the tree half-deleted, which
    is how a folder ends up listed but permanently inaccessible. So the
    tree is removed with retries first, then bottom-up by hand, and the
    original error is only reported if entries genuinely survive.

    Args:
        target:
            The directory to remove.

    Raises:
        OSError:
            If the tree could not be fully removed.
    """

    last_error: OSError | None = None

    for attempt in range(DELETE_ATTEMPTS):

        try:

            shutil.rmtree(target)
            return

        except FileNotFoundError:
            return

        except OSError as error:

            if not is_transient_delete_error(error):
                raise

            last_error = error

            if attempt + 1 < DELETE_ATTEMPTS:
                time.sleep(
                    DELETE_BACKOFF * (attempt + 1)
                )

    remove_tree_manual(target)

    if target.exists():

        raise last_error


# ============================================================
# COMMAND-LINE TEST
# ============================================================

if __name__ == "__main__":

    print(
        "Initializing Project Manager..."
    )

    build_project_filesystem()

    print()
    print("Project root:")
    print(PROJECT_ROOT)

    print()
    print("Project information:")

    print(
        json.dumps(
            read_project_info(),
            indent=4,
        )
    )

    print()
    print("Project filesystem:")

    print(
        json.dumps(
            read_filesystem(),
            indent=4,
        )
    )
