from fastapi import FastAPI, HTTPException

from app.models import (
    DocumentIn,
    AskRequest,
    WorkflowRequest,
    ApprovalRequest,
    ToolRequest,
)
from app.rag import (
    add_document,
    list_documents,
    seed_documents,
)
from app.agents import (
    supervisor,
    decide_approval,
    specialist,
)
from app.observability import trace, read_traces
from app.mcp_client import call_mcp
from app.guardrails import validate_input


app = FastAPI(
    title="Enterprise AI Operations Platform",
    version="1.0.0",
)


TOOL_POLICY = {
    "demo-user": {
        "search_knowledge",
        "list_knowledge_documents",
        "current_utc_time",
        "safe_calculate",
    },
    "admin-demo": {
        "search_knowledge",
        "list_knowledge_documents",
        "current_utc_time",
        "safe_calculate",
    },
}


@app.on_event("startup")
def startup():
    seed_documents()


@app.get("/")
def root():
    return {
        "message": "Enterprise AI Operations Platform",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/documents")
def create_document(payload: DocumentIn):
    document = add_document(
        payload.title,
        payload.text,
        payload.source,
    )

    return {
        "status": "indexed",
        "document": {
            "id": document["id"],
            "title": document["title"],
            "source": document["source"],
        },
    }


@app.get("/documents")
def documents():
    items = list_documents()

    return {
        "count": len(items),
        "documents": items,
    }


@app.post("/ask")
def ask(payload: AskRequest):
    return supervisor(
        payload.question,
        payload.user_id,
    )


@app.post("/workflow")
def workflow(payload: WorkflowRequest):
    return supervisor(
        payload.question,
        payload.user_id,
        payload.require_approval,
    )


@app.post("/approvals/{approval_id}")
def approval(
    approval_id: str,
    payload: ApprovalRequest,
):
    result = decide_approval(
        approval_id,
        payload.approved,
        payload.user_id,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Approval ID not found",
        )

    if result.get("status") == "forbidden":
        raise HTTPException(
            status_code=403,
            detail=result["message"],
        )

    return result


@app.post("/tools/call")
def tool_call(payload: ToolRequest):
    valid, message = validate_input(
        payload.tool_name + " " + str(payload.arguments)
    )

    if not valid:
        raise HTTPException(
            status_code=400,
            detail=message,
        )

    allowed_tools = TOOL_POLICY.get(
        payload.user_id,
        set(),
    )

    if payload.tool_name not in allowed_tools:
        trace(
            "tool",
            "authorization_denied",
            user_id=payload.user_id,
            tool_name=payload.tool_name,
        )

        raise HTTPException(
            status_code=403,
            detail="User is not authorized to call this tool.",
        )

    try:
        result = call_mcp(
            payload.tool_name,
            payload.arguments,
        )

        trace(
            "tool",
            "mcp_tool_call",
            user_id=payload.user_id,
            tool_name=payload.tool_name,
            result_preview=result[:200],
        )

        return {
            "tool": payload.tool_name,
            "result": result,
        }

    except PermissionError as error:
        raise HTTPException(
            status_code=403,
            detail=str(error),
        )

    except Exception as error:
        trace(
            "tool",
            "mcp_tool_error",
            tool_name=payload.tool_name,
            error=str(error),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"MCP tool call failed: "
                f"{type(error).__name__}: {error}"
            ),
        )


@app.post("/agents/research")
def a2a_research(payload: AskRequest):
    # Research agent contract called through HTTP by the supervisor.
    valid, message = validate_input(payload.question)

    if not valid:
        raise HTTPException(status_code=400, detail=message)

    result = specialist(
        payload.question,
        "a2a-" + payload.user_id,
        "research_specialist",
    )

    result["status"] = "completed"

    trace(
        "agent",
        "a2a_research_endpoint",
        user_id=payload.user_id,
        status=result["status"],
    )

    return {
        "agent_card": {
            "name": "ResearchAgent",
            "protocol": "HTTP A2A demo",
        },
        **result,
    }


@app.get("/traces")
def traces(limit: int = 100):
    items = read_traces(limit)

    return {
        "count": len(items),
        "traces": items,
    }


@app.get("/eval/run")
def run_eval():
    from app.evaluation import run_evaluations

    return run_evaluations()