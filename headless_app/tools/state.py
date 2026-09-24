"""
app/tools/state.py
==================

Shared working state for the file-management tools.

The FileSession is the single in-memory record of everything a file-aware
agent has discovered, read, written, or proposed for deletion during the
current process. It lets later tool calls (and the model itself) build on
previous results instead of re-scanning the filesystem each turn.

The session is process-wide: one instance is created lazily and shared by
every agent that is built in this process.

It is injected into the conversation by Agent._inject_session_context and
hydrated from tool results by the _record_result wrapper in app/agents/factory.py.
"""


class FileSession:
    """Manages file-management working state for AI agents dynamically.

    Tracks, across tool calls in one process:

        discovered_files   - paths surfaced by map_files / other listing tools
        selected_files     - paths the agent has explicitly chosen to work on
        read_files         - paths whose contents have already been read
        working_content    - path -> last extracted text content (read_file)
        output_files       - paths the agent has written (write_text_file)
        pending_deletion   - paths proposed for deletion but not yet approved
    """

    def __init__(self):
        self.discovered_files = []
        self.selected_files = []
        self.read_files = []
        self.working_content = {}
        self.output_files = []
        self.pending_deletion = []

    def add_discovered(self, paths: list):
        """Record files/directories surfaced by map_files (deduplicated)."""
        self.discovered_files = list(set(self.discovered_files + paths))

    def select_files(self, paths: list):
        """Mark paths as the agent's active working set (deduplicated)."""
        self.selected_files = list(set(self.selected_files + paths))

    def record_read(self, path: str, content: str):
        """Remember that a path was read and cache its extracted content."""
        if path not in self.read_files:
            self.read_files.append(path)
        self.working_content[path] = content

    def add_output(self, path: str):
        """Remember a path produced by the write tool (deduplicated)."""
        if path not in self.output_files:
            self.output_files.append(path)

    def mark_for_deletion(self, paths: list):
        """Propose paths for deletion (deduplicated; approval happens later)."""
        self.pending_deletion = list(set(self.pending_deletion + paths))

    def get_state(self) -> dict:
        """Snapshot the current session state for injection into the prompt."""
        return {
            "discovered_files": self.discovered_files,
            "selected_files": self.selected_files,
            "read_files": self.read_files,
            "output_files": self.output_files,
            "pending_deletion": self.pending_deletion
        }
