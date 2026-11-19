import asyncio
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient


def _find_npx_script(pkg_name: str) -> Path | None:
    """Find local cached npx script to run via 'node' directly for instant startup."""
    npx_dir = Path.home() / ".npm" / "_npx"
    if not npx_dir.exists():
        return None
    for entry in npx_dir.glob(f"*/node_modules/{pkg_name}/dist/index.js"):
        if entry.is_file():
            return entry
    return None


def _ensure_node20_compatibility():
    """Ensure @modelcontextprotocol/server-filesystem does not crash on Node < 22."""
    npx_dir = Path.home() / ".npm" / "_npx"
    if not npx_dir.exists():
        return
    for pinned in npx_dir.glob("*/node_modules/@modelcontextprotocol/server-filesystem/dist/pinned-directory.js"):
        try:
            content = pinned.read_text(encoding="utf-8")
            if 'import { getSystemErrorMessage } from "util";' in content:
                content = content.replace(
                    'import { getSystemErrorMessage } from "util";',
                    'import util from "util";\nconst getSystemErrorMessage = util.getSystemErrorMessage || ((errno) => `system error ${errno}`);'
                )
                pinned.write_text(content, encoding="utf-8")
                print(f"[MCP] Patched Node 20 compatibility in {pinned}")
        except Exception as e:
            print(f"[MCP] Warning: could not patch {pinned}: {e}")


class MCPManager:
    CONNECT_TIMEOUT = 10  # seconds

    def __init__(self, directory):
        path = Path(directory).resolve()
        if not path.is_dir():
            raise FileNotFoundError(f"MCP directory missing: {path}")
        self.directory = str(path)
        self.client = None
        self.tools = []

    async def connect(self):
        memory_file = Path(self.directory) / "memory.json"

        # Apply Node 20 compatibility patch for server-filesystem if cached
        _ensure_node20_compatibility()

        # Prefer running directly via node if cached in ~/.npm/_npx
        fs_cached = _find_npx_script("@modelcontextprotocol/server-filesystem")
        mem_cached = _find_npx_script("@modelcontextprotocol/server-memory")

        fs_config = {
            "transport": "stdio",
            "command": "node" if fs_cached else "npx",
            "args": [str(fs_cached), self.directory] if fs_cached else ["-y", "@modelcontextprotocol/server-filesystem", self.directory],
        }

        mem_config = {
            "transport": "stdio",
            "command": "node" if mem_cached else "npx",
            "args": [str(mem_cached)] if mem_cached else ["-y", "@modelcontextprotocol/server-memory"],
            "env": {
                "MEMORY_FILE_PATH": str(memory_file),
            },
        }

        try:
            self.client = MultiServerMCPClient({
                "filesystem": fs_config,
                "memory": mem_config,
            })

            self.tools = await asyncio.wait_for(
                self.client.get_tools(),
                timeout=self.CONNECT_TIMEOUT,
            )
            print("\n[MCP] Connected successfully")
            print("\n[MCP] Available tools:")
            for tool in self.tools:
                print("-", tool.name)

            fs_count = sum(1 for t in self.tools if _is_fs_tool(t.name))
            mem_count = len(self.tools) - fs_count
            print(f"\n[MCP] filesystem tools: {fs_count} | memory tools: {mem_count}")
            print(f"[MCP] memory file: {memory_file}")
        except Exception as e:
            print(f"\n[MCP] Warning: Failed to connect to MCP servers ({e}). Continuing with core tools only.")
            self.tools = []
            self.client = None

    async def get_tools(self):
        return self.tools

    async def disconnect(self):
        self.tools = []
        self.client = None
        print("[MCP] Manager closed")


def _is_fs_tool(name: str) -> bool:
    """Filesystem server tool names check."""
    return name in {
        "read_file", "read_text_file", "read_media_file", "read_multiple_files",
        "write_file", "append_file", "edit_file", "create_directory",
        "list_directory", "list_directory_with_sizes", "directory_tree",
        "move_file", "copy_file", "search_files", "get_file_info",
        "list_allowed_directories",
    }
