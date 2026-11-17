import asyncio
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient


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
        # Memory file ko research directory ke andar rakhte hain,
        # taaki wo bhi aapke project ke saath persist rahe.
        memory_file = Path(self.directory) / "memory.json"

        self.client = MultiServerMCPClient({
            "filesystem": {
                "transport": "stdio",
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    self.directory,
                ],
            },
            "memory": {
                "transport": "stdio",
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-memory",
                ],
                "env": {
                    # Default ~/.mcp/memory.json hota hai; hum explicitly
                    # research/ folder ke andar rakh rahe hain.
                    "MEMORY_FILE_PATH": str(memory_file),
                },
            },
        })

        try:
            self.tools = await asyncio.wait_for(
                self.client.get_tools(),
                timeout=self.CONNECT_TIMEOUT,
            )
        except asyncio.TimeoutError:
            await self.disconnect()
            raise RuntimeError(
                f"MCP tool discovery timed out after {self.CONNECT_TIMEOUT}s"
            )

        print("\n[MCP] Connected successfully")
        print("\n[MCP] Available tools:")
        for tool in self.tools:
            print("-", tool.name)

        # Ek chhota summary taaki pata chale kaunse server se kya aaya
        fs_count = sum(1 for t in self.tools if _is_fs_tool(t.name))
        mem_count = len(self.tools) - fs_count
        print(f"\n[MCP] filesystem tools: {fs_count} | memory tools: {mem_count}")
        print(f"[MCP] memory file: {memory_file}")

    async def get_tools(self):
        return self.tools

    async def disconnect(self):
        self.tools = []
        self.client = None
        print("[MCP] Manager closed")


def _is_fs_tool(name: str) -> bool:
    """Filesystem server ke typical tool names."""
    return name in {
        "read_file", "read_multiple_files", "write_file", "edit_file",
        "create_directory", "list_directory", "directory_tree",
        "move_file", "search_files", "get_file_info",
        "list_allowed_directories",
    }