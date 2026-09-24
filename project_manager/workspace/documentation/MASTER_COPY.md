# Project Manager — Master Copy

Single-file backup of the complete application source code and file structure.

- **Project:** Project Manager
- **Version:** 1.0.0
- **Workspace version:** 1.0
- **Repo:** https://github.com/TheChuey/project
- **Generated:** 2026-09-23

---

## File Structure

```text
project/
    ├── documentation
    │   ├── MASTER_COPY.md
    │   └── PLAN_editor_interface.md
    ├── editor
    │   ├── __init__.py
    │   ├── events.py
    │   ├── operations.py
    │   └── session.py
    ├── projectConfiguration
    │   ├── __init__.py
    │   ├── project.json
    │   └── Project_files.py
    ├── routers
    │   ├── __init__.py
    │   ├── directories.py
    │   ├── errors.py
    │   ├── files.py
    │   ├── paths.py
    │   └── project.py
    ├── run_at_first_use
    │   ├── run.bat
    │   ├── run.sh
    │   └── setup.sh
    ├── static
    │   ├── editor.html
    │   └── index.html
    ├── .gitattributes
    ├── .gitignore
    ├── editor_client.py
    ├── README.md
    ├── requirements.txt
    └── server.py
```

---

## File Contents

### README.md

````markdown
# Project Manager

A lightweight FastAPI workspace server. Browse and edit project files from a
web dashboard with a Monaco-powered code editor.

## Features

- Project tree browser (browse, open, create, rename, delete)
- In-browser code editor with syntax highlighting
- JSON REST API for filesystem operations
- Works on Windows and (Chromebook) Linux

## Requirements

- Python 3.9+
- Network access for the code editor CDN (Monaco, loaded from cdnjs)

## Setup

### Windows

```bat
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
run.bat
```

### Chromebook (ChromeOS with Linux/Crostini)

Open a Linux terminal and enable the Linux apps if you have not already:

```sh
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

Clone the repo, then:

```sh
./setup.sh
./run.sh
```

Then open `http://127.0.0.1:8000` in the Chrome browser. On ChromeOS the
browser can reach the Linux container through `127.0.0.1`.

## Configuration

The server binds to `127.0.0.1:8000` by default. Override with environment
variables:

```sh
PROJECT_MANAGER_HOST=0.0.0.0 PROJECT_MANAGER_PORT=8080 ./run.sh
```

## API overview

| Method | Path                       | Description                |
| ------ | -------------------------- | -------------------------- |
| GET    | `/`                        | Dashboard UI               |
| GET    | `/editor`                  | Standalone editor UI       |
| GET    | `/api/health`              | Health + project info      |
| GET    | `/api/project`             | Project state + tree       |
| GET    | `/api/file/read?path=...`  | Read a file                |
| PUT    | `/api/file/write`          | Write a file               |
| POST   | `/api/file/create`         | Create a file              |
| POST   | `/api/directory/create`    | Create a directory         |
| PUT    | `/api/path/rename`         | Rename/move a path         |
| DELETE | `/api/file/delete?path=...`| Delete a file              |
| DELETE | `/api/directory/delete?path=...` | Delete a directory         |

Note: The `data/`, `config/`, `documentation/`, etc. folders are empty so git
does not track them; the server recreates them automatically on startup.
````
---

### requirements.txt

`text
fastapi==0.115.0
uvicorn[standard]==0.32.0
httpx==0.27.2
websockets==13.1

`
---

### server.py

`python
"""
Project Manager Server
======================

Lightweight FastAPI server for the Project Manager workspace.

Responsibilities:
    - Start the project.
    - Initialize the filesystem.
    - Serve the browser interface.
    - Provide project information.
    - Provide filesystem information.
    - Read files.
    - Write files.
    - Create files.
    - Create directories.
    - Rename files/directories.
    - Delete files/directories.

Filesystem operations are handled by project_files.py.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

import Project_files


# ============================================================
# CONFIGURATION
# ============================================================

HOST = os.environ.get(
    "PROJECT_MANAGER_HOST",
    "127.0.0.1",
)

PORT = int(
    os.environ.get(
        "PROJECT_MANAGER_PORT",
        "8000",
    )
)

PROJECT_ROOT = Path(__file__).resolve().parent

STATIC_DIR = PROJECT_ROOT / "static"

INDEX_HTML = STATIC_DIR / "index.html"

EDITOR_HTML = STATIC_DIR / "editor.html"


# ============================================================
# FASTAPI APPLICATION
# ============================================================

@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    """
    Build the basic project filesystem when
    the server starts.
    """

    Project_files.build_project_filesystem()

    yield


app = FastAPI(
    title="Project Manager Server",
    description="Lightweight Project Manager workspace server.",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# REQUEST MODELS
# ============================================================

class FileWriteRequest(BaseModel):

    path: str

    content: str


class FileCreateRequest(BaseModel):

    path: str

    content: str = ""


class RenameRequest(BaseModel):

    old_path: str

    new_path: str


# ============================================================
# ERROR HELPER
# ============================================================

def filesystem_error(
    error: Exception,
) -> HTTPException:
    """
    Convert filesystem exceptions into HTTP errors.
    """

    if isinstance(
        error,
        FileNotFoundError,
    ):

        return HTTPException(
            status_code=404,
            detail=str(error),
        )

    if isinstance(
        error,
        FileExistsError,
    ):

        return HTTPException(
            status_code=409,
            detail=str(error),
        )

    if isinstance(
        error,
        ValueError,
    ):

        return HTTPException(
            status_code=400,
            detail=str(error),
        )

    return HTTPException(
        status_code=500,
        detail=str(error),
    )


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    """
    Display the main project interface.
    """

    if not INDEX_HTML.exists():

        raise HTTPException(
            status_code=404,
            detail="static/index.html was not found.",
        )

    return FileResponse(
        INDEX_HTML
    )


# ============================================================
# EDITOR
# ============================================================

@app.get("/editor")
def editor():
    """
    Display the standalone editor.
    """

    if not EDITOR_HTML.exists():

        raise HTTPException(
            status_code=404,
            detail="static/editor.html was not found.",
        )

    return FileResponse(
        EDITOR_HTML
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():
    """
    Check server health.
    """

    return {
        "status": "healthy",
        "project": Project_files.read_project_info(),
    }


# ============================================================
# PROJECT STATE
# ============================================================

@app.get("/api/project")
def get_project():
    """
    Return project information and filesystem tree.
    """

    return Project_files.get_project_state()


# ============================================================
# READ FILE
# ============================================================

@app.get("/api/file/read")
def read_file(path: str):
    """
    Read a project text file.
    """

    try:

        content = Project_files.read_file(
            path
        )

        return {
            "path": path,
            "content": content,
        }

    except Exception as error:

        raise filesystem_error(
            error
        )


# ============================================================
# WRITE FILE
# ============================================================

@app.put("/api/file/write")
def write_file(
    request: FileWriteRequest,
):
    """
    Create or overwrite a project text file.
    """

    try:

        Project_files.write_file(
            request.path,
            request.content,
        )

        return {
            "status": "saved",
            "path": request.path,
        }

    except Exception as error:

        raise filesystem_error(
            error
        )


# ============================================================
# CREATE FILE
# ============================================================

@app.post("/api/file/create")
def create_file(
    request: FileCreateRequest,
):
    """
    Create a new project file.
    """

    try:

        Project_files.create_file(
            request.path,
            request.content,
        )

        return {
            "status": "created",
            "path": request.path,
        }

    except Exception as error:

        raise filesystem_error(
            error
        )


# ============================================================
# CREATE DIRECTORY
# ============================================================

@app.post("/api/directory/create")
def create_directory(
    path: str,
):
    """
    Create a project directory.
    """

    try:

        Project_files.create_directory(
            path
        )

        return {
            "status": "created",
            "path": path,
        }

    except Exception as error:

        raise filesystem_error(
            error
        )


# ============================================================
# RENAME
# ============================================================

@app.put("/api/path/rename")
def rename_path(
    request: RenameRequest,
):
    """
    Rename or move a project file/directory.
    """

    try:

        Project_files.rename_path(
            request.old_path,
            request.new_path,
        )

        return {
            "status": "renamed",
            "old_path": request.old_path,
            "new_path": request.new_path,
        }

    except Exception as error:

        raise filesystem_error(
            error
        )


# ============================================================
# DELETE FILE
# ============================================================

@app.delete("/api/file/delete")
def delete_file(
    path: str,
):
    """
    Delete a project file.
    """

    try:

        target = Project_files.resolve_project_path(
            path
        )

        if not target.exists():

            raise FileNotFoundError(
                "File not found."
            )

        if not target.is_file():

            raise ValueError(
                "Path is not a file."
            )

        Project_files.delete_path(
            path
        )

        return {
            "status": "deleted",
            "path": path,
        }

    except Exception as error:

        raise filesystem_error(
            error
        )


# ============================================================
# DELETE DIRECTORY
# ============================================================

@app.delete("/api/directory/delete")
def delete_directory(
    path: str,
):
    """
    Delete a project directory.
    """

    try:

        target = Project_files.resolve_project_path(
            path
        )

        if not target.exists():

            raise FileNotFoundError(
                "Directory not found."
            )

        if not target.is_dir():

            raise ValueError(
                "Path is not a directory."
            )

        Project_files.delete_path(
            path
        )

        return {
            "status": "deleted",
            "path": path,
        }

    except Exception as error:

        raise filesystem_error(
            error
        )


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
    )

`
---

### projectConfiguration/project.json

`json
{
    "name": "Project Manager",
    "version": "1.0.0",
    "workspace_version": "1.0"
}
`
---

### projectConfiguration/Project_files.py

`python
"""
Project Manager Filesystem
==========================

This module is responsible for managing the physical
project filesystem.

Responsibilities:
    - Discover the project root.
    - Create the basic project structure.
    - Create/read project.json.
    - Read the project filesystem.
    - Read files.
    - Write files.
    - Create files.
    - Create directories.
    - Rename files/directories.
    - Delete files/directories.
    - Prevent access outside the project root.

The web server does NOT contain filesystem logic.
server.py calls this module.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_CONFIG_DIR = Path(__file__).resolve().parent

PROJECT_ROOT = PROJECT_CONFIG_DIR.parent

PROJECT_JSON = PROJECT_CONFIG_DIR / "project.json"


# ============================================================
# STANDARD PROJECT FOLDERS
# ============================================================

PROJECT_FOLDERS = [
    "documentation",
    "project_scope",
    "to_do",
    "updates",
    "config",
    "data",
]


# ============================================================
# FILE TYPES
# ============================================================

TEXT_EXTENSIONS = {
    ".py",
    ".txt",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".sql",
    ".xml",
    ".csv",
    ".env",
}


# ============================================================
# DIRECTORIES TO HIDE
# ============================================================

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
}


# ============================================================
# DEFAULT PROJECT INFORMATION
# ============================================================

DEFAULT_PROJECT = {
    "name": PROJECT_ROOT.name,
    "version": "1.0.0",
    "workspace_version": "1.0",
}


# ============================================================
# PATH SECURITY
# ============================================================

def resolve_project_path(relative_path: str) -> Path:
    """
    Convert a project-relative path into a safe absolute path.

    This prevents paths such as:

        ../../some_file.txt

    from escaping the project directory.

    Args:
        relative_path:
            Path relative to the project root.

    Returns:
        Safe absolute Path.

    Raises:
        ValueError:
            If the path is empty or outside the project.
    """

    if not relative_path:

        raise ValueError(
            "A project-relative path is required."
        )

    # Normalize Windows separators.
    relative_path = relative_path.replace(
        "\\",
        "/",
    )

    candidate = (
        PROJECT_ROOT / relative_path
    ).resolve()

    try:

        candidate.relative_to(
            PROJECT_ROOT
        )

    except ValueError:

        raise ValueError(
            "Access outside the project directory "
            "is not allowed."
        )

    return candidate


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

def should_ignore(path: Path) -> bool:
    """
    Determine whether a path should be hidden
    from the project browser.
    """

    return any(
        part in IGNORED_DIRECTORIES
        for part in path.parts
    )


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


# ============================================================
# READ FILESYSTEM
# ============================================================

def read_filesystem(
    directory: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Recursively read the project filesystem.

    Returns:
        JSON-friendly file/folder tree.
    """

    if directory is None:

        directory = PROJECT_ROOT

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
            PROJECT_ROOT
        )

        relative_path = str(
            relative_path
        ).replace(
            "\\",
            "/",
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
                        child
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
                    "editable": is_text_file(
                        child
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
) -> str:
    """
    Read a text file.

    Args:
        relative_path:
            Project-relative file path.

    Returns:
        File contents.

    Raises:
        ValueError:
            Invalid path or file type.
        FileNotFoundError:
            File does not exist.
    """

    file_path = resolve_project_path(
        relative_path
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
) -> None:
    """
    Create or overwrite a text file.

    Parent directories are automatically created.
    """

    file_path = resolve_project_path(
        relative_path
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
) -> None:
    """
    Create a new file.

    Refuses to overwrite an existing file.
    """

    file_path = resolve_project_path(
        relative_path
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
) -> None:
    """
    Create a directory.
    """

    directory = resolve_project_path(
        relative_path
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
) -> None:
    """
    Rename or move a file/directory within the project.

    Both paths must remain inside PROJECT_ROOT.
    """

    source = resolve_project_path(
        old_path
    )

    destination = resolve_project_path(
        new_path
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
) -> None:
    """
    Delete a file or directory.

    Directories are deleted recursively.

    The project root itself cannot be deleted.
    """

    target = resolve_project_path(
        relative_path
    )

    if target == PROJECT_ROOT:

        raise ValueError(
            "The project root cannot be deleted."
        )

    if not target.exists():

        raise FileNotFoundError(
            "Path not found."
        )

    if target.is_dir():

        shutil.rmtree(target)

    else:

        target.unlink()


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

`
---

### run_at_first_use/setup.sh

`bash
#!/usr/bin/env bash
#
# Project Manager - one-time setup for (Chromebook) Linux.
# Creates a virtual environment and installs dependencies.
#
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 was not found." >&2
    echo "On ChromeOS, enable Linux and then run:" >&2
    echo "  sudo apt update" >&2
    echo "  sudo apt install -y python3 python3-venv python3-pip" >&2
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

echo "Installing dependencies..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo
echo "Setup complete. Start the server with:  ./run.sh"
echo "Then open:  http://127.0.0.1:8000"
`
---

### run_at_first_use/run.sh

`bash
#!/usr/bin/env bash
#
# Project Manager - start the server from the virtual environment.
#
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Run ./setup.sh first." >&2
    exit 1
fi

echo "Starting Project Manager at http://127.0.0.1:8000"
echo "To stop: press Ctrl+C"
echo

.venv/bin/python server.py
`
---

### run_at_first_use/run.bat

`dosbatch
@echo off
rem Project Manager - start the server from the virtual environment.

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run: python -m venv .venv
    echo Then: .venv\Scripts\python -m pip install -r requirements.txt
    exit /b 1
)

echo Starting Project Manager at http://127.0.0.1:8000
echo To stop: press Ctrl+C
echo.

.venv\Scripts\python server.py
`
---

### static/index.html

`html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Manager Dashboard</title>

    <style>
        * {
            box-sizing: border-box;
        }

        html, body {
            margin: 0;
            padding: 0;
            width: 100vw;
            height: 100vh;
            font-family: Arial, sans-serif;
            background: #1e1e1e;
            color: #ffffff;
        }

        .topbar {
            height: 48px;
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 0 12px;
            background: #252526;
            border-bottom: 1px solid #3f3f46;
        }

        .title {
            font-weight: bold;
            margin-right: 12px;
        }

        button {
            border: 1px solid #555;
            background: #333;
            color: #fff;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
        }

        button:hover {
            background: #444;
        }

        button.primary {
            background: #0e639c;
            border-color: #1177bb;
        }

        .container {
            padding: 24px;
            max-width: 1200px;
            margin: 0 auto;
        }

        .actions {
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
        }

        .card {
            background: #252526;
            border: 1px solid #3f3f46;
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 20px;
        }

        .card h2 {
            margin-top: 0;
            margin-bottom: 12px;
            font-size: 18px;
        }

        .tree-item {
            user-select: none;
            cursor: pointer;
            padding: 6px 8px;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .tree-item:hover {
            background: #2a2d2e;
        }

        .children {
            margin-left: 16px;
        }

        .statusbar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: 26px;
            display: flex;
            align-items: center;
            padding: 0 10px;
            background: #007acc;
            color: white;
            font-size: 12px;
        }
    </style>
</head>
<body>

<div class="topbar">
    <div class="title">Project Manager Dashboard</div>
    <button class="primary" onclick="openEditor()">Editor</button>
    <button onclick="openEditorPopup()">Editor (Popup)</button>
    <button onclick="refreshProject()">Refresh</button>
</div>

<div class="container">
    <div class="actions">
        <button class="primary" onclick="openEditor()">Open Full Editor</button>
        <button onclick="openEditorPopup()">Launch Editor Window</button>
        <button onclick="submitCreateFilePrompt()">+ New File</button>
        <button onclick="submitCreateFolderPrompt()">+ New Folder</button>
    </div>

    <div class="card">
        <h2>Project Workspace</h2>
        <div id="projectTree">Loading files...</div>
    </div>
</div>

<div class="statusbar">
    <div id="statusMessage">Ready</div>
</div>

<script>
/* ============================================================
   NAVIGATION & EDITOR LAUNCHERS
   ============================================================ */

// Opens editor in the current window
function openEditor(filePath) {
    let url = "/editor";
    if (filePath) {
        url += "?path=" + encodeURIComponent(filePath);
    }
    window.location.href = url;
}

// Opens editor in a floating popup window
function openEditorPopup(filePath) {
    let url = "/editor";
    if (filePath) {
        url += "?path=" + encodeURIComponent(filePath);
    }

    const width = 1200;
    const height = 800;
    const left = (window.screen.width - width) / 2;
    const top = (window.screen.height - height) / 2;

    window.open(
        url,
        "ProjectManagerEditorPopup",
        `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes,status=no,toolbar=no,menubar=no`
    );
}

/* ============================================================
   PROJECT TREE & API CALLS
   ============================================================ */

async function loadProject() {
    setStatus("Loading project...");
    try {
        const response = await fetch("/api/project");
        if (!response.ok) throw new Error("Could not load project");

        const data = await response.json();
        renderTree(data.filesystem || []);
        setStatus("Project loaded");
    } catch (err) {
        setStatus("Error: " + err.message);
    }
}

function renderTree(items) {
    const container = document.getElementById("projectTree");
    container.innerHTML = "";
    renderItems(items, container);
}

function renderItems(items, container) {
    items.forEach(item => {
        const div = document.createElement("div");
        div.className = "tree-item";
        
        const label = document.createElement("span");
        label.textContent = (item.type === "directory" ? "📁 " : "📄 ") + item.name;
        div.appendChild(label);

        if (item.type === "file") {
            const btnGroup = document.createElement("div");
            
            const editBtn = document.createElement("button");
            editBtn.textContent = "Edit";
            editBtn.onclick = (e) => {
                e.stopPropagation();
                openEditor(item.path);
            };

            const popupBtn = document.createElement("button");
            popupBtn.textContent = "Popup";
            popupBtn.style.marginLeft = "4px";
            popupBtn.onclick = (e) => {
                e.stopPropagation();
                openEditorPopup(item.path);
            };

            btnGroup.appendChild(editBtn);
            btnGroup.appendChild(popupBtn);
            div.appendChild(btnGroup);
        }

        container.appendChild(div);

        if (item.type === "directory" && item.children) {
            const childrenContainer = document.createElement("div");
            childrenContainer.className = "children";
            container.appendChild(childrenContainer);
            renderItems(item.children, childrenContainer);
        }
    });
}

async function submitCreateFilePrompt() {
    const path = prompt("Enter file path/name:");
    if (!path) return;

    try {
        const res = await fetch("/api/file/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: path, content: "" })
        });
        if (!res.ok) throw new Error("Failed to create file");
        await loadProject();
        openEditor(path);
    } catch (err) {
        alert(err.message);
    }
}

async function submitCreateFolderPrompt() {
    const path = prompt("Enter folder path:");
    if (!path) return;

    try {
        const res = await fetch("/api/directory/create?path=" + encodeURIComponent(path), {
            method: "POST"
        });
        if (!res.ok) throw new Error("Failed to create folder");
        await loadProject();
    } catch (err) {
        alert(err.message);
    }
}

function refreshProject() {
    loadProject();
}

function setStatus(msg) {
    document.getElementById("statusMessage").textContent = msg;
}

// Initial Load
loadProject();
</script>

</body>
</html>
`
---

### static/editor.html

`html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Manager Editor</title>

    <style>
        * {
            box-sizing: border-box;
        }

        html, body {
            margin: 0;
            padding: 0;
            width: 100vw;
            height: 100vh;
            overflow: hidden;
            font-family: Arial, sans-serif;
            background: #1e1e1e;
            color: #ffffff;
        }

        .topbar {
            height: 48px;
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 0 12px;
            background: #252526;
            border-bottom: 1px solid #3f3f46;
        }

        .title {
            font-weight: bold;
            margin-right: 12px;
        }

        button {
            border: 1px solid #555;
            background: #333;
            color: #fff;
            padding: 6px 10px;
            border-radius: 4px;
            cursor: pointer;
        }

        button:hover {
            background: #444;
        }

        button.primary {
            background: #0e639c;
            border-color: #1177bb;
        }

        button.danger {
            background: #7f1d1d;
        }

        .workspace {
            display: flex;
            height: calc(100vh - 74px);
            width: 100%;
        }

        .sidebar {
            width: 250px;
            min-width: 180px;
            background: #252526;
            border-right: 1px solid #3f3f46;
            display: flex;
            flex-direction: column;
        }

        .sidebar-header {
            padding: 10px;
            border-bottom: 1px solid #3f3f46;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .resize-handle {
            width: 4px;
            cursor: col-resize;
            background: transparent;
            transition: background 0.2s;
        }

        .resize-handle:hover {
            background: #0e639c;
        }

        .tree {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
        }

        .tree-item {
            user-select: none;
            cursor: pointer;
            padding: 4px 6px;
            border-radius: 3px;
        }

        .tree-item:hover {
            background: #2a2d2e;
        }

        .tree-item.selected {
            background: #094771;
        }

        .children {
            margin-left: 12px;
        }

        .editor-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-width: 0;
            height: 100%;
        }

        .filebar {
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 12px;
            background: #1f1f1f;
            border-bottom: 1px solid #3f3f46;
        }

        #unsavedIndicator {
            color: #e2c08d;
            font-size: 12px;
            font-weight: bold;
            margin-left: 8px;
        }

        #editor {
            flex: 1;
            width: 100%;
            height: 100%;
            background: #1e1e1e;
        }

        .statusbar {
            height: 26px;
            display: flex;
            align-items: center;
            padding: 0 10px;
            background: #007acc;
            color: white;
            font-size: 12px;
        }

        .status-message {
            flex: 1;
        }
    </style>

    <!-- Monaco Loader CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs/loader.min.js"></script>
</head>
<body>

<div class="topbar">
    <div class="title">Project Manager Editor</div>
    <button onclick="goHome()">🏠 Home</button>
    <button class="primary" onclick="saveFile()">Save</button>
    <button onclick="newFile()">+ File</button>
    <button onclick="newFolder()">+ Folder</button>
    <button onclick="renameSelected()">Rename</button>
    <button class="danger" onclick="deleteSelected()">Delete</button>
    <button onclick="refreshTree()">Refresh</button>
</div>

<div class="workspace">
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <span>PROJECT FILES</span>
        </div>
        <div id="tree" class="tree">Loading...</div>
    </div>
    
    <div class="resize-handle" id="resizeHandle"></div>

    <div class="editor-area">
        <div class="filebar">
            <div>
                <span id="currentFile">No file selected</span>
                <span id="unsavedIndicator"></span>
            </div>
            <div id="language">plaintext</div>
        </div>
        <div id="editor"></div>
    </div>
</div>

<div class="statusbar">
    <div id="statusMessage" class="status-message">Initializing...</div>
</div>

<script>
/* ============================================================
   GLOBAL STATE
   ============================================================ */

let editor = null;
let currentFile = null;
let currentLanguage = "plaintext";
let isDirty = false;
let projectTree = [];

/* ============================================================
   NAVIGATION
   ============================================================ */

function goHome() {
    if (isDirty) {
        const proceed = confirm("You have unsaved changes. Return to home?");
        if (!proceed) return;
    }
    window.location.href = "/";
}

/* ============================================================
   LANGUAGE DETECTION MAP
   ============================================================ */

function getLanguage(filePath) {
    if (!filePath) return "plaintext";
    const ext = filePath.split(".").pop().toLowerCase();
    const map = {
        py: "python",
        js: "javascript",
        jsx: "javascript",
        ts: "typescript",
        tsx: "typescript",
        html: "html",
        htm: "html",
        css: "css",
        json: "json",
        md: "markdown",
        yaml: "yaml",
        yml: "yaml",
        sql: "sql",
        xml: "xml",
        sh: "shell",
        env: "shell",
        txt: "plaintext"
    };
    return map[ext] || "plaintext";
}

/* ============================================================
   MONACO INITIALIZATION
   ============================================================ */

if (typeof require !== 'undefined') {
    require.config({
        paths: {
            vs: "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs"
        }
    });

    require(["vs/editor/editor.main"], function () {
        editor = monaco.editor.create(document.getElementById("editor"), {
            value: "// Select a file from the sidebar to start editing\n",
            language: "plaintext",
            theme: "vs-dark",
            automaticLayout: true,
            minimap: { enabled: true },
            wordWrap: "on",
            fontSize: 14,
            
            // Indentation & Auto-formatting controls
            tabSize: 4,
            insertSpaces: true,
            autoIndent: "full",
            formatOnType: true,
            formatOnPaste: true
        });

        editor.onDidChangeModelContent(function () {
            if (!currentFile) return;
            isDirty = true;
            updateDirtyIndicator();
        });

        setStatus("Ready");

        loadProject().then(() => {
            const urlParams = new URLSearchParams(window.location.search);
            const initialPath = urlParams.get("path");
            if (initialPath) {
                openFile(initialPath);
            }
        });
    });
} else {
    setStatus("Error: Could not load Monaco CDN loader script.");
}

/* ============================================================
   PROJECT TREE & FILESYSTEM OPERATIONS
   ============================================================ */

async function loadProject() {
    setStatus("Loading project...");
    try {
        const response = await fetch("/api/project");
        if (!response.ok) throw new Error("Could not load project.");

        const data = await response.json();
        projectTree = data.filesystem || [];
        renderTree();
        setStatus("Project loaded.");
    } catch (error) {
        setStatus("Error: " + error.message);
    }
}

function renderTree() {
    const tree = document.getElementById("tree");
    tree.innerHTML = "";
    renderItems(projectTree, tree);
}

function renderItems(items, container) {
    for (const item of items) {
        const row = document.createElement("div");
        row.className = "tree-item";

        if (item.type === "directory") {
            row.classList.add("folder");
            row.textContent = "📁 " + item.name;
            container.appendChild(row);

            const children = document.createElement("div");
            children.className = "children";
            container.appendChild(children);

            renderItems(item.children || [], children);
        } else {
            row.textContent = "📄 " + item.name;
            if (currentFile === item.path) {
                row.classList.add("selected");
            }

            row.onclick = function () {
                openFile(item.path);
            };

            container.appendChild(row);
        }
    }
}

async function openFile(filePath) {
    if (isDirty) {
        const proceed = confirm("You have unsaved changes. Open another file?");
        if (!proceed) return;
    }

    setStatus("Opening " + filePath + "...");

    try {
        const response = await fetch("/api/file/read?path=" + encodeURIComponent(filePath));
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Could not read file.");
        }

        const data = await response.json();
        currentFile = filePath;
        currentLanguage = getLanguage(filePath);

        if (editor) {
            editor.setValue(data.content);
            monaco.editor.setModelLanguage(editor.getModel(), currentLanguage);
        }

        isDirty = false;
        updateFileDisplay();
        renderTree();
        setStatus("Opened " + filePath);
    } catch (error) {
        setStatus("Error: " + error.message);
        alert(error.message);
    }
}

async function saveFile() {
    if (!currentFile || !editor) {
        alert("No file is currently open.");
        return;
    }

    setStatus("Saving...");

    try {
        const response = await fetch("/api/file/write", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                path: currentFile,
                content: editor.getValue()
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Could not save file.");
        }

        isDirty = false;
        updateDirtyIndicator();
        setStatus("Saved " + currentFile);
        await refreshTree();
    } catch (error) {
        setStatus("Save error: " + error.message);
        alert(error.message);
    }
}

async function newFile() {
    const fileName = prompt("Enter new file path/name:");
    if (!fileName) return;

    try {
        const response = await fetch("/api/file/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                path: fileName,
                content: ""
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Could not create file.");
        }

        await refreshTree();
        await openFile(fileName);
        setStatus("Created " + fileName);
    } catch (error) {
        alert(error.message);
    }
}

async function newFolder() {
    const folderPath = prompt("Enter new folder path:");
    if (!folderPath) return;

    try {
        const response = await fetch("/api/directory/create?path=" + encodeURIComponent(folderPath), {
            method: "POST"
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Could not create folder.");
        }

        await refreshTree();
        setStatus("Created folder " + folderPath);
    } catch (error) {
        alert(error.message);
    }
}

async function renameSelected() {
    if (!currentFile) {
        alert("Select a file first.");
        return;
    }

    const newName = prompt("Enter the new file path:", currentFile);
    if (!newName || newName === currentFile) return;

    try {
        const response = await fetch("/api/path/rename", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                old_path: currentFile,
                new_path: newName
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Could not rename file.");
        }

        currentFile = newName;
        await refreshTree();
        await openFile(newName);
    } catch (error) {
        alert(error.message);
    }
}

async function deleteSelected() {
    if (!currentFile) {
        alert("Select a file first.");
        return;
    }

    const confirmed = confirm("Delete " + currentFile + "?");
    if (!confirmed) return;

    try {
        const response = await fetch("/api/file/delete?path=" + encodeURIComponent(currentFile), {
            method: "DELETE"
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Could not delete file.");
        }

        currentFile = null;
        editor.setValue("");
        isDirty = false;
        updateFileDisplay();
        await refreshTree();
        setStatus("File deleted.");
    } catch (error) {
        alert(error.message);
    }
}

async function refreshTree() {
    await loadProject();
}

/* ============================================================
   UI UPDATES & UTILITIES
   ============================================================ */

function updateFileDisplay() {
    document.getElementById("currentFile").textContent = currentFile ? currentFile : "No file selected";
    document.getElementById("language").textContent = currentLanguage;
    updateDirtyIndicator();
}

function updateDirtyIndicator() {
    document.getElementById("unsavedIndicator").textContent = isDirty ? "● UNSAVED" : "";
}

function setStatus(message) {
    document.getElementById("statusMessage").textContent = message;
}

/* ============================================================
   KEYBOARD SHORTCUTS & SIDEBAR RESIZE
   ============================================================ */

document.addEventListener("keydown", function (event) {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        saveFile();
    }
});

const sidebar = document.getElementById("sidebar");
const resizeHandle = document.getElementById("resizeHandle");
let resizing = false;

resizeHandle.addEventListener("mousedown", function () {
    resizing = true;
    document.body.style.cursor = "col-resize";
});

document.addEventListener("mousemove", function (event) {
    if (!resizing) return;
    const width = event.clientX;
    if (width >= 180 && width <= 500) {
        sidebar.style.width = width + "px";
        if (editor) editor.layout();
    }
});

document.addEventListener("mouseup", function () {
    resizing = false;
    document.body.style.cursor = "";
});

window.addEventListener("beforeunload", function (event) {
    if (!isDirty) return;
    event.preventDefault();
    event.returnValue = "";
});
</script>

</body>
</html>
`
---

### gitattributes

`git-attrs
# Text files use LF line endings everywhere.
* text=auto eol=lf

# Explicit text / code files
*.py text eol=lf
*.sh text eol=lf
*.bat text eol=lf
*.html text eol=lf
*.css text eol=lf
*.js text eol=lf
*.json text eol=lf
*.md text eol=lf
*.txt text eol=lf
`
---

### gitignore

`gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.eggs/
build/
dist/

# Virtual environments
.venv/
venv/
env/

# Test / tooling caches
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# Editor / IDE
.idea/
.vscode/

# Logs
*.log
`
---

*End of master copy.*
```

---

<!-- ==== 38/39 : workspace/documentation/PLAN_editor_interface.md ==== -->

### workspace/documentation/PLAN_editor_interface.md

```markdown
# Plan: Project Manager Interface

Python module + organized server CRUD + modular UI.

## Goal

Keep the application as a **Project Manager** while adding a proper interface that allows AI agents and other Python programs to communicate with the Project Manager.

The Project Manager remains responsible for:

- project files
- directories
- file editing
- project configuration
- filesystem safety
- project initialization
- web UI

The new interface becomes another way to interact with those existing Project Manager capabilities.

The interface must **not bypass `Project_files.py`**.

## Architecture

```text
                         PROJECT MANAGER
                               │
              ┌────────────────┴────────────────┐
              │                                 │
        Web Interface                    Python Interface
              │                                 │
        Browser / Monaco                 AI Agents / Scripts
              │                                 │
              └────────────────┬────────────────┘
                               │
                        Project Manager
                        operation layer
                               │
                        Project_files.py
                               │
                        Project filesystem
```

The important principle is:

> There is one Project Manager and multiple interfaces to it.

## Target Structure

```text
project/
├── documentation/
│   └── MASTER_COPY.md
│
├── editor/
│   ├── __init__.py
│   ├── events.py
│   ├── session.py
│   └── operations.py
│
├── routers/
│   ├── __init__.py
│   ├── project.py
│   ├── files.py
│   ├── directories.py
│   ├── paths.py
│   └── ws.py
│
├── projectConfiguration/
│   ├── __init__.py
│   ├── Project_files.py
│   └── project.json
│
├── static/
│   ├── index.html
│   ├── editor.html
│   └── js/
│       ├── api.js
│       ├── session.js
│       ├── tree.js
│       ├── editor.js
│       └── main.js
│
├── editor_client.py
├── server.py
├── requirements.txt
└── ...
```

## Components

### 1. `editor/` — Project Manager operation/interface layer

This is the internal layer between the HTTP API and the filesystem.

It is **not a replacement for the Project Manager**.

It provides a clean set of operations that multiple interfaces can use.

#### `operations.py`

Create a controller such as `EditorInterface`.

It provides operations such as:

```text
open()
save()
create_file()
create_directory()
rename()
delete()
tree()
sessions()
```

Every filesystem mutation eventually goes through `Project_files.py`.

The controller should not implement its own filesystem logic.

Conceptually:

```text
Router
   ↓
Project Manager Interface
   ↓
Project_files
   ↓
Filesystem
```

### 2. `events.py` — Project Manager event system

Create a small event bus for changes occurring inside the Project Manager.

Example events:

```text
saved
created
renamed
deleted
tree_changed
```

Example:

```json
{
    "type": "saved",
    "path": "app.py"
}
```

The event system allows the browser and future agents to receive information about changes without directly monitoring the filesystem.

### 3. `session.py` — Interface sessions

Create:

```text
EditorSession
EditorManager
```

`EditorSession` tracks a connected interface client.

Possible state:

```text
client_id
open_file
dirty
last_modified
```

`EditorManager` maintains the active in-memory sessions.

It should also provide:

```text
register()
unregister()
update()
snapshot()
```

This is initially an in-memory system. Do not introduce a database for sessions.

### 4. `routers/` — Project Manager HTTP API

Split the existing API into resource-oriented routers.

#### `project.py`

```text
GET /api/project
GET /api/health
GET /api/sessions
```

#### `files.py`

```text
GET    /api/file/read
PUT    /api/file/write
POST   /api/file/create
DELETE /api/file/delete
```

#### `directories.py`

```text
POST   /api/directory/create
DELETE /api/directory/delete
```

#### `paths.py`

```text
PUT /api/path/rename
```

#### `ws.py`

```text
WS /api/ws
```

The existing REST paths and contracts remain unchanged.

### 5. WebSocket Interface

Add:

```text
/api/ws
```

The WebSocket provides real-time Project Manager events.

On connection:

```text
register session
```

Client messages may include:

```text
open
dirty
tree
```

Server events may include:

```text
saved
created
renamed
deleted
tree_changed
```

Example:

```json
{
    "type": "created",
    "path": "config/settings.json"
}
```

The browser can then update itself without requiring a complete page reload.

### 6. `editor_client.py` — Python Project Manager Interface

Create a Python client that allows another Python program or AI agent to communicate with the running Project Manager.

```python
from editor_client import EditorClient

client = EditorClient("http://127.0.0.1:8000")

client.tree()

client.open("app.py")

client.save(
    "app.py",
    "print('Hello World')"
)
```

Supported operations:

```text
open()
save()
create_file()
create_directory()
rename()
delete()
tree()
health()
sessions()
```

The client communicates with the Project Manager API. It must **not directly access the Project Manager filesystem**. This is important because the Project Manager remains the authority over filesystem operations.

### 7. Async Client

Provide an asynchronous client for AI-agent workflows:

```text
AsyncEditorClient
```

with asynchronous versions of the Project Manager operations.

Also provide:

```text
subscribe()
```

for receiving Project Manager events through WebSockets. This allows future agents to react to changes.

Example concept:

```text
AI Agent
   │
   ├── save file
   │
   ▼
Project Manager
   │
   ├── filesystem change
   │
   └── event
          │
          ▼
       Agent
```

### 8. Frontend Organization

The Project Manager UI remains visually and functionally the same. The JavaScript is reorganized into vanilla ES modules.

```text
static/js/
├── api.js
├── session.js
├── tree.js
├── editor.js
└── main.js
```

#### `api.js`

Central location for API requests. Responsible for:

```text
health
project
file operations
directory operations
rename
delete
sessions
```

#### `tree.js`

Responsible for:

- rendering the project tree
- selecting files
- refreshing the tree
- responding to tree-change events

#### `editor.js`

Responsible for Monaco. Move the existing Monaco initialization and behavior here with the goal of preserving it verbatim where practical. Keep:

- Monaco configuration
- editor initialization
- syntax highlighting
- save behavior
- Ctrl+S
- dirty state
- theme
- sidebar behavior

#### `session.js`

Responsible for:

- WebSocket connection
- connection state
- sending session events
- receiving Project Manager events
- applying live changes

#### `main.js`

Responsible for application startup and wiring the modules together.

### 9. `server.py`

After the reorganization, `server.py` becomes the application entry point:

```text
create FastAPI application
        ↓
configure lifespan
        ↓
register routers
        ↓
serve static files
        ↓
start server
```

It should not become the location for Project Manager business logic.

## Requirements

Add:

```text
httpx
websockets
```

to `requirements.txt`. Keep the existing FastAPI and Uvicorn dependencies.

## What Does NOT Change

The following remain Project Manager responsibilities:

```text
Project_files.py
project.json
project initialization
filesystem safety
dashboard
Monaco editor
existing REST endpoints
project structure
Windows support
Linux/ChromeOS support
```

The interface adds capability; it does not replace these systems.

## Interface Principle

The interface must provide agents with a controlled Project Manager API. An agent should think in terms of:

```text
open project file
read project file
save project file
create project file
create directory
rename path
delete path
inspect project tree
```

rather than:

```text
open arbitrary filesystem path
write arbitrary filesystem path
delete arbitrary filesystem path
```

The Project Manager remains the authority.

## Verification

### 1. Application startup

```text
python server.py
```

Verify the server starts successfully.

### 2. Existing API

Verify all existing contracts continue working:

```text
/api/health
/api/project
/api/file/read
/api/file/write
/api/file/create
/api/file/delete
/api/directory/create
/api/directory/delete
/api/path/rename
```

### 3. Browser

Verify:

- dashboard loads
- project tree loads
- files open
- Monaco works
- editing works
- Ctrl+S works
- file creation works
- rename works
- deletion works

The UI should remain visually/functionally equivalent.

### 4. Real-Time Events

Open the Project Manager in a browser, then modify the project through another client. Verify the browser receives the appropriate event.

Examples:

```text
create → created
save → saved
rename → renamed
delete → deleted
```

### 5. Python Client

Run a test script:

```text
health
tree
create
open
save
rename
delete
```

Verify each operation goes through the Project Manager.

### 6. Filesystem Authority

Confirm that `editor_client.py`, `routers/`, `editor/` do not bypass `Project_files.py` for Project Manager filesystem operations.

## Final Architecture

```text
                    ┌─────────────────────┐
                    │   Project Manager   │
                    │       Server        │
                    └──────────┬──────────┘
                               │
                    Project Manager Core
                               │
                    ┌──────────▼──────────┐
                    │    Project_files    │
                    │  Filesystem Owner   │
                    └──────────┬──────────┘
                               │
                         Project Root
                               ▲
                               │
              ┌────────────────┴────────────────┐
              │                                 │
       Browser Interface                 Python Interface
              │                                 │
       Monaco / Dashboard                 editor_client.py
              │                                 │
              │                           AI Agents
              │                           Python Scripts
              │                                 │
              └──────────────┬──────────────────┘
                             │
                       Project Manager
                         HTTP / WS API
```

The central idea is:

> **Project Manager first. Interface second.**
```

---

<!-- ==== 39/39 : workspace/project.json ==== -->

### workspace/project.json

```json
{
    "name": "Project Manager",
    "version": "1.0.0",
    "workspace_version": "1.0"
}
```

---

> Generated by `scripts/gen_master_copy.py` on 2026-09-23. Do not edit by hand; regenerate with:
>
> `.venv/Scripts/python -m scripts.gen_master_copy`
```

---

<!-- ==== 38/39 : workspace/documentation/PLAN_editor_interface.md ==== -->

### workspace/documentation/PLAN_editor_interface.md

```markdown
# Plan: Project Manager Interface

Python module + organized server CRUD + modular UI.

## Goal

Keep the application as a **Project Manager** while adding a proper interface that allows AI agents and other Python programs to communicate with the Project Manager.

The Project Manager remains responsible for:

- project files
- directories
- file editing
- project configuration
- filesystem safety
- project initialization
- web UI

The new interface becomes another way to interact with those existing Project Manager capabilities.

The interface must **not bypass `Project_files.py`**.

## Architecture

```text
                         PROJECT MANAGER
                               │
              ┌────────────────┴────────────────┐
              │                                 │
        Web Interface                    Python Interface
              │                                 │
        Browser / Monaco                 AI Agents / Scripts
              │                                 │
              └────────────────┬────────────────┘
                               │
                        Project Manager
                        operation layer
                               │
                        Project_files.py
                               │
                        Project filesystem
```

The important principle is:

> There is one Project Manager and multiple interfaces to it.

## Target Structure

```text
project/
├── documentation/
│   └── MASTER_COPY.md
│
├── editor/
│   ├── __init__.py
│   ├── events.py
│   ├── session.py
│   └── operations.py
│
├── routers/
│   ├── __init__.py
│   ├── project.py
│   ├── files.py
│   ├── directories.py
│   ├── paths.py
│   └── ws.py
│
├── projectConfiguration/
│   ├── __init__.py
│   ├── Project_files.py
│   └── project.json
│
├── static/
│   ├── index.html
│   ├── editor.html
│   └── js/
│       ├── api.js
│       ├── session.js
│       ├── tree.js
│       ├── editor.js
│       └── main.js
│
├── editor_client.py
├── server.py
├── requirements.txt
└── ...
```

## Components

### 1. `editor/` — Project Manager operation/interface layer

This is the internal layer between the HTTP API and the filesystem.

It is **not a replacement for the Project Manager**.

It provides a clean set of operations that multiple interfaces can use.

#### `operations.py`

Create a controller such as `EditorInterface`.

It provides operations such as:

```text
open()
save()
create_file()
create_directory()
rename()
delete()
tree()
sessions()
```

Every filesystem mutation eventually goes through `Project_files.py`.

The controller should not implement its own filesystem logic.

Conceptually:

```text
Router
   ↓
Project Manager Interface
   ↓
Project_files
   ↓
Filesystem
```

### 2. `events.py` — Project Manager event system

Create a small event bus for changes occurring inside the Project Manager.

Example events:

```text
saved
created
renamed
deleted
tree_changed
```

Example:

```json
{
    "type": "saved",
    "path": "app.py"
}
```

The event system allows the browser and future agents to receive information about changes without directly monitoring the filesystem.

### 3. `session.py` — Interface sessions

Create:

```text
EditorSession
EditorManager
```

`EditorSession` tracks a connected interface client.

Possible state:

```text
client_id
open_file
dirty
last_modified
```

`EditorManager` maintains the active in-memory sessions.

It should also provide:

```text
register()
unregister()
update()
snapshot()
```

This is initially an in-memory system. Do not introduce a database for sessions.

### 4. `routers/` — Project Manager HTTP API

Split the existing API into resource-oriented routers.

#### `project.py`

```text
GET /api/project
GET /api/health
GET /api/sessions
```

#### `files.py`

```text
GET    /api/file/read
PUT    /api/file/write
POST   /api/file/create
DELETE /api/file/delete
```

#### `directories.py`

```text
POST   /api/directory/create
DELETE /api/directory/delete
```

#### `paths.py`

```text
PUT /api/path/rename
```

#### `ws.py`

```text
WS /api/ws
```

The existing REST paths and contracts remain unchanged.

### 5. WebSocket Interface

Add:

```text
/api/ws
```

The WebSocket provides real-time Project Manager events.

On connection:

```text
register session
```

Client messages may include:

```text
open
dirty
tree
```

Server events may include:

```text
saved
created
renamed
deleted
tree_changed
```

Example:

```json
{
    "type": "created",
    "path": "config/settings.json"
}
```

The browser can then update itself without requiring a complete page reload.

### 6. `editor_client.py` — Python Project Manager Interface

Create a Python client that allows another Python program or AI agent to communicate with the running Project Manager.

```python
from editor_client import EditorClient

client = EditorClient("http://127.0.0.1:8000")

client.tree()

client.open("app.py")

client.save(
    "app.py",
    "print('Hello World')"
)
```

Supported operations:

```text
open()
save()
create_file()
create_directory()
rename()
delete()
tree()
health()
sessions()
```

The client communicates with the Project Manager API. It must **not directly access the Project Manager filesystem**. This is important because the Project Manager remains the authority over filesystem operations.

### 7. Async Client

Provide an asynchronous client for AI-agent workflows:

```text
AsyncEditorClient
```

with asynchronous versions of the Project Manager operations.

Also provide:

```text
subscribe()
```

for receiving Project Manager events through WebSockets. This allows future agents to react to changes.

Example concept:

```text
AI Agent
   │
   ├── save file
   │
   ▼
Project Manager
   │
   ├── filesystem change
   │
   └── event
          │
          ▼
       Agent
```

### 8. Frontend Organization

The Project Manager UI remains visually and functionally the same. The JavaScript is reorganized into vanilla ES modules.

```text
static/js/
├── api.js
├── session.js
├── tree.js
├── editor.js
└── main.js
```

#### `api.js`

Central location for API requests. Responsible for:

```text
health
project
file operations
directory operations
rename
delete
sessions
```

#### `tree.js`

Responsible for:

- rendering the project tree
- selecting files
- refreshing the tree
- responding to tree-change events

#### `editor.js`

Responsible for Monaco. Move the existing Monaco initialization and behavior here with the goal of preserving it verbatim where practical. Keep:

- Monaco configuration
- editor initialization
- syntax highlighting
- save behavior
- Ctrl+S
- dirty state
- theme
- sidebar behavior

#### `session.js`

Responsible for:

- WebSocket connection
- connection state
- sending session events
- receiving Project Manager events
- applying live changes

#### `main.js`

Responsible for application startup and wiring the modules together.

### 9. `server.py`

After the reorganization, `server.py` becomes the application entry point:

```text
create FastAPI application
        ↓
configure lifespan
        ↓
register routers
        ↓
serve static files
        ↓
start server
```

It should not become the location for Project Manager business logic.

## Requirements

Add:

```text
httpx
websockets
```

to `requirements.txt`. Keep the existing FastAPI and Uvicorn dependencies.

## What Does NOT Change

The following remain Project Manager responsibilities:

```text
Project_files.py
project.json
project initialization
filesystem safety
dashboard
Monaco editor
existing REST endpoints
project structure
Windows support
Linux/ChromeOS support
```

The interface adds capability; it does not replace these systems.

## Interface Principle

The interface must provide agents with a controlled Project Manager API. An agent should think in terms of:

```text
open project file
read project file
save project file
create project file
create directory
rename path
delete path
inspect project tree
```

rather than:

```text
open arbitrary filesystem path
write arbitrary filesystem path
delete arbitrary filesystem path
```

The Project Manager remains the authority.

## Verification

### 1. Application startup

```text
python server.py
```

Verify the server starts successfully.

### 2. Existing API

Verify all existing contracts continue working:

```text
/api/health
/api/project
/api/file/read
/api/file/write
/api/file/create
/api/file/delete
/api/directory/create
/api/directory/delete
/api/path/rename
```

### 3. Browser

Verify:

- dashboard loads
- project tree loads
- files open
- Monaco works
- editing works
- Ctrl+S works
- file creation works
- rename works
- deletion works

The UI should remain visually/functionally equivalent.

### 4. Real-Time Events

Open the Project Manager in a browser, then modify the project through another client. Verify the browser receives the appropriate event.

Examples:

```text
create → created
save → saved
rename → renamed
delete → deleted
```

### 5. Python Client

Run a test script:

```text
health
tree
create
open
save
rename
delete
```

Verify each operation goes through the Project Manager.

### 6. Filesystem Authority

Confirm that `editor_client.py`, `routers/`, `editor/` do not bypass `Project_files.py` for Project Manager filesystem operations.

## Final Architecture

```text
                    ┌─────────────────────┐
                    │   Project Manager   │
                    │       Server        │
                    └──────────┬──────────┘
                               │
                    Project Manager Core
                               │
                    ┌──────────▼──────────┐
                    │    Project_files    │
                    │  Filesystem Owner   │
                    └──────────┬──────────┘
                               │
                         Project Root
                               ▲
                               │
              ┌────────────────┴────────────────┐
              │                                 │
       Browser Interface                 Python Interface
              │                                 │
       Monaco / Dashboard                 editor_client.py
              │                                 │
              │                           AI Agents
              │                           Python Scripts
              │                                 │
              └──────────────┬──────────────────┘
                             │
                       Project Manager
                         HTTP / WS API
```

The central idea is:

> **Project Manager first. Interface second.**
```

---

<!-- ==== 39/39 : workspace/project.json ==== -->

### workspace/project.json

```json
{
    "name": "Project Manager",
    "version": "1.0.0",
    "workspace_version": "1.0"
}
```

---

> Generated by `scripts/gen_master_copy.py` on 2026-09-23. Do not edit by hand; regenerate with:
>
> `.venv/Scripts/python -m scripts.gen_master_copy`
