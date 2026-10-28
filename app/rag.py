
import re
import math
import uuid
from collections import Counter

from app.guardrails import sanitize
from app.observability import trace
from app.llm import generate_answer


# In-memory document store for this demo.
DOCUMENTS = []
CHUNKS = []


# Sample documents loaded automatically.
SEED_DOCUMENTS = [
    (
        "Employee Access Policy",
        (
            "Employees must use company-approved accounts and "
            "multi-factor authentication. Access should follow "
            "least privilege. Managers must request access changes "
            "through the service desk. Access for terminated "
            "employees must be revoked promptly after HR confirmation."
        ),
        "seed:access-policy",
    ),
    (
        "Security Incident Process",
        (
            "Report suspected security incidents to the security team "
            "immediately. Preserve relevant logs and do not delete "
            "evidence. The incident manager coordinates containment, "
            "investigation, and recovery."
        ),
        "seed:incident-process",
    ),
    (
        "Password Standard",
        (
            "Passwords must be at least 14 characters. Use unique "
            "passwords and never share credentials. Report suspected "
            "account compromise to the security team and reset "
            "credentials using the approved workflow."
        ),
        "seed:password-standard",
    ),
]


def tokens(text):
    """Convert text to lowercase search tokens."""
    return re.findall(r"[a-z0-9_'-]+", text.lower())


def chunk_text(text, size=700, overlap=100):
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))

        if end == len(words):
            break

        start = max(end - overlap, start + 1)

    return chunks


def add_document(title, text, source="user-upload"):
    """Store a document and create searchable chunks."""
    document_id = str(uuid.uuid4())[:8]

    document = {
        "id": document_id,
        "title": title,
        "source": source,
        "text": text,
    }

    DOCUMENTS.append(document)

    document_chunks = chunk_text(text)

    for index, chunk in enumerate(document_chunks):
        CHUNKS.append({
            "chunk_id": f"{document_id}-{index}",
            "document_id": document_id,
            "title": title,
            "source": source,
            "text": sanitize(chunk),
        })

    trace(
        "tool",
        "document_ingestion",
        document_id=document_id,
        title=title,
        chunk_count=len(document_chunks),
    )

    return document


def seed_documents():
    """Load example documents once per application process."""
    if not DOCUMENTS:
        for title, text, source in SEED_DOCUMENTS:
            add_document(title, text, source)


def list_documents():
    """Return document metadata without full document text."""
    return [
        {
            "id": document["id"],
            "title": document["title"],
            "source": document["source"],
        }
        for document in DOCUMENTS
    ]


def transform_query(question):
    """Generate a simple keyword-focused query."""
    terms = list(dict.fromkeys(
        term for term in tokens(question) if len(term) > 2
    ))

    focused_query = " ".join(terms)
    queries = [question]

    if focused_query and focused_query.lower() != question.lower():
        queries.append(focused_query)

    return queries


def retrieve(question, top_k=5):
    """
    Demonstration hybrid retrieval:
    combines BM25-style lexical scoring and TF-IDF-style scoring,
    then applies a lightweight lexical reranking step.
    """
    if not CHUNKS:
        seed_documents()

    all_tokens = [
        tokens(chunk["title"] + " " + chunk["text"])
        for chunk in CHUNKS
    ]

    document_sets = [set(items) for items in all_tokens]
    scores = {}

    for query in transform_query(question):
        query_tokens = tokens(query)

        for index, document_tokens in enumerate(all_tokens):
            counts = Counter(document_tokens)
            bm25_score = 0.0
            tfidf_score = 0.0

            for term in set(query_tokens):
                frequency = counts[term]

                if frequency:
                    denominator = (
                        frequency
                        + 1.2 * (
                            0.25
                            + 0.75 * len(document_tokens) / 100
                        )
                    )
                    bm25_score += frequency * 2.2 / denominator

                    document_frequency = sum(
                        term in terms for terms in document_sets
                    )

                    inverse_frequency = math.log(
                        1
                        + (
                            len(all_tokens)
                            - document_frequency
                            + 0.5
                        )
                        / (document_frequency + 0.5)
                    )

                    tfidf_score += (
                        1 + math.log(1 + frequency)
                    ) * inverse_frequency

            combined_score = (
                0.55 * bm25_score + 0.45 * tfidf_score
            )

            scores[index] = max(
                scores.get(index, 0.0),
                combined_score,
            )

    ranked_indices = sorted(
        scores,
        key=lambda index: scores[index],
        reverse=True,
    )

    candidates = []

    for index in ranked_indices[:max(top_k * 3, top_k)]:
        if scores[index] <= 0:
            continue

        chunk = dict(CHUNKS[index])
        question_terms = set(tokens(question))
        document_terms = set(
            tokens(chunk["title"] + " " + chunk["text"])
        )

        coverage = (
            len(question_terms & document_terms)
            / max(1, len(question_terms))
        )

        title_bonus = (
            0.25
            if question_terms & set(tokens(chunk["title"]))
            else 0
        )

        chunk["retrieval_score"] = round(scores[index], 4)
        chunk["rerank_score"] = round(
            coverage + title_bonus + min(scores[index], 10) / 100,
            4,
        )

        candidates.append(chunk)

    candidates.sort(
        key=lambda chunk: chunk["rerank_score"],
        reverse=True,
    )

    results = candidates[:top_k]

    trace(
        "tool",
        "hybrid_retrieval_rerank",
        query=question,
        transformed_queries=transform_query(question),
        candidate_count=len(candidates),
        result_count=len(results),
    )

    return results


def build_answer(question, hits):
    """Generate a grounded answer using NVIDIA and return citations."""
    if not hits:
        return {
            "answer": (
                "I could not find supporting information "
                "in indexed documents."
            ),
            "citations": [],
        }

    context_parts = []
    citations = []

    for hit in hits[:3]:
        context_parts.append(
            f"Document: {hit['title']}\n"
            f"Source: {hit['source']}\n"
            f"Content: {hit['text']}"
        )

        citations.append({
            "document_id": hit["document_id"],
            "title": hit["title"],
            "chunk_id": hit["chunk_id"],
            "source": hit["source"],
        })

    context = "\n\n".join(context_parts)

    try:
        answer = generate_answer(question, context)
    except Exception as error:
        # Log the error type, not credentials or the full exception.
        trace(
            "llm",
            "nvidia_generation_failed",
            error_type=type(error).__name__,
        )

        return {
            "answer": (
                "The NVIDIA AI service is unavailable or not configured. "
                "Check your NVIDIA API key, model, and service logs."
            ),
            "citations": citations,
        }

    if not answer:
        answer = (
            "The NVIDIA AI service returned an empty response. "
            "Please try again."
        )

    return {
        "answer": answer,
        "citations": citations,
    }
