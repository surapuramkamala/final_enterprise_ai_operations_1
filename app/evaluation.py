from app.rag import retrieve, seed_documents
from app.agents import supervisor
from app.observability import trace


GOLDEN_DATASET = [
    {
        "question": "How long must passwords be?",
        "expected_terms": ["14 characters", "password"],
        "expected_title": "Password Standard",
    },
    {
        "question": (
            "What should I do after a suspected security incident?"
        ),
        "expected_terms": ["security team", "immediately"],
        "expected_title": "Security Incident Process",
    },
    {
        "question": (
            "What does least privilege mean for employee access?"
        ),
        "expected_terms": ["least privilege", "multi-factor"],
        "expected_title": "Employee Access Policy",
    },
]


def run_evaluations():
    seed_documents()

    retrieval_cases = []
    agent_cases = []

    for item in GOLDEN_DATASET:
        hits = retrieve(
            item["question"],
            top_k=3,
        )

        titles = [hit["title"] for hit in hits]

        found = item["expected_title"] in titles

        reciprocal_rank = (
            1 / (titles.index(item["expected_title"]) + 1)
            if found
            else 0
        )

        retrieval_cases.append({
            "question": item["question"],
            "expected_title": item["expected_title"],
            "retrieved_titles": titles,
            "hit_at_3": found,
            "reciprocal_rank": reciprocal_rank,
        })

        result = supervisor(
            item["question"],
            user_id="eval-user",
        )

        answer = result.get("answer", "").lower()

        terms_found = [
            term
            for term in item["expected_terms"]
            if term.lower() in answer
        ]

        passed = (
            result.get("status") == "completed"
            and bool(result.get("citations"))
            and bool(terms_found)
        )

        agent_cases.append({
            "question": item["question"],
            "status": result.get("status"),
            "citations_present": bool(
                result.get("citations")
            ),
            "expected_terms_found": terms_found,
            "agent_check_pass": passed,
        })

    total = len(GOLDEN_DATASET)

    hit_at_3 = (
        sum(case["hit_at_3"] for case in retrieval_cases)
        / total
    )

    mean_reciprocal_rank = (
        sum(
            case["reciprocal_rank"]
            for case in retrieval_cases
        )
        / total
    )

    agent_pass_rate = (
        sum(
            case["agent_check_pass"]
            for case in agent_cases
        )
        / total
    )

    report = {
        "dataset_size": total,
        "retrieval_hit_at_3": round(hit_at_3, 3),
        "mean_reciprocal_rank": round(
            mean_reciprocal_rank, 3
        ),
        "agent_pass_rate": round(agent_pass_rate, 3),
        "retrieval_cases": retrieval_cases,
        "agent_cases": agent_cases,
    }

    trace(
        "evaluation",
        "golden_dataset_eval",
        retrieval_hit_at_3=report["retrieval_hit_at_3"],
        agent_pass_rate=report["agent_pass_rate"],
    )

    return report