import os
import uuid
import httpx

from app.guardrails import validate_input, validate_output
from app.rag import retrieve, build_answer
from app.observability import trace


APPROVALS = {}
SESSIONS = {}


def specialist(question, trace_id, name):
    top_k = 3 if name == "research_specialist" else 5

    hits = retrieve(question, top_k=top_k)
    result = build_answer(question, hits)

    trace(
        "agent",
        name,
        trace_id=trace_id,
        retrieved_chunks=len(hits),
    )

    return {
        **result,
        "agent": name,
        "retrieved_chunks": len(hits),
    }


def supervisor(
    question,
    user_id="demo-user",
    require_approval=False,
):
    trace_id = str(uuid.uuid4())

    valid, message = validate_input(question)

    if not valid:
        trace(
            "agent",
            "supervisor_blocked",
            trace_id=trace_id,
            reason=message,
        )

        return {
            "status": "blocked",
            "answer": message,
            "citations": [],
            "trace_id": trace_id,
        }

    SESSIONS.setdefault(user_id, []).append({
        "role": "user",
        "content": question,
    })

    query = question.lower()

    if any(
        word in query
        for word in ("compare", "summarize", "research", "overview")
    ):
        route = "research_specialist"
    else:
        route = "rag_specialist"

    # A2A: supervisor calls the research-agent HTTP endpoint.
    if route == "research_specialist":
        a2a_url = os.getenv(
            "A2A_RESEARCH_URL",
            "http://127.0.0.1:8000/agents/research",
        )

        try:
            response = httpx.post(
                a2a_url,
                json={
                    "question": question,
                    "user_id": user_id,
                },
                timeout=3.0,
            )

            response.raise_for_status()
            result = response.json()

            trace(
                "agent",
                "a2a_supervisor_to_research",
                trace_id=trace_id,
                status="ok",
            )

        except Exception as error:
            trace(
                "agent",
                "a2a_fallback_local",
                trace_id=trace_id,
                error=str(error),
            )

            result = specialist(
                question,
                trace_id,
                route,
            )

    else:
        result = specialist(
            question,
            trace_id,
            route,
        )

    valid_output, answer = validate_output(
        result["answer"]
    )

    result["answer"] = answer
    result["status"] = (
        "completed" if valid_output else "blocked"
    )

    trace(
        "agent",
        "supervisor_route",
        trace_id=trace_id,
        route=route,
        user_id=user_id,
    )

    sensitive_request = any(
        action in query
        for action in (
            "revoke access",
            "delete document",
            "send external email",
        )
    )

    if require_approval and sensitive_request:
        approval_id = str(uuid.uuid4())[:8]

        APPROVALS[approval_id] = {
            "user_id": user_id,
            "status": "pending",
        }

        trace(
            "agent",
            "human_approval_required",
            trace_id=trace_id,
            approval_id=approval_id,
        )

        return {
            "status": "approval_required",
            "approval_id": approval_id,
            "proposed_action": "sensitive_action",
            "answer": (
                "Sensitive action proposed; human approval "
                "is required. No action has been executed."
            ),
            "citations": result["citations"],
            "trace_id": trace_id,
        }

    SESSIONS[user_id].append({
        "role": "assistant",
        "content": result["answer"],
    })

    return {
        **result,
        "trace_id": trace_id,
        "session_messages": len(SESSIONS[user_id]),
    }


def decide_approval(approval_id, approved, user_id):
    approval = APPROVALS.get(approval_id)

    if not approval:
        return None

    if approval["user_id"] != user_id:
        return {
            "status": "forbidden",
            "message": "Approval belongs to another user.",
        }

    if approval["status"] != "pending":
        return {
            "status": approval["status"],
            "message": "Approval has already been handled.",
        }

    approval["status"] = (
        "approved" if approved else "rejected"
    )

    trace(
        "agent",
        "human_approval_decision",
        approval_id=approval_id,
        approved=approved,
        user_id=user_id,
    )

    return {
        "status": approval["status"],
        "message": (
            "Demo action recorded only; "
            "no external system was changed."
        ),
    }