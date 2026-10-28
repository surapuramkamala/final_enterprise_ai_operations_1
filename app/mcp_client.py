import os
import sys
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)


async def call_server(module, tool_name, arguments):
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", module],
        env={
            **os.environ,
            "PYTHONPATH": (
                ROOT
                + os.pathsep
                + os.environ.get("PYTHONPATH", "")
            ),
        },
    )

    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                tool_name,
                arguments,
            )

            return "\n".join(
                item.text
                for item in result.content
                if getattr(item, "text", None)
            )


def call_mcp(tool_name, arguments):
    if tool_name in {
        "search_knowledge",
        "list_knowledge_documents",
    }:
        module = "app.mcp_servers.knowledge_server"

    elif tool_name in {
        "current_utc_time",
        "safe_calculate",
    }:
        module = "app.mcp_servers.utility_server"

    else:
        raise PermissionError(
            "Tool is not allowlisted"
        )

    return asyncio.run(
        call_server(module, tool_name, arguments)
    )