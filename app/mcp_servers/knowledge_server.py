from mcp.server.fastmcp import FastMCP

mcp = FastMCP("knowledge-tools")


@mcp.tool()
def search_knowledge(query: str) -> str:
    """Search local knowledge documents for relevant information."""

    from app.rag import retrieve, build_answer, seed_documents

    seed_documents()

    hits = retrieve(query, top_k=3)
    result = build_answer(query, hits)

    return result["answer"]


@mcp.tool()
def list_knowledge_documents() -> str:
    """Return titles of indexed knowledge documents."""

    from app.rag import list_documents, seed_documents

    seed_documents()

    documents = list_documents()

    return ", ".join(
        document["title"]
        for document in documents
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")