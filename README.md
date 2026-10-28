# Enterprise AI Operations Platform

## Requirements
- Python 3.11+
- pip

## Setup

Create a virtual environment:

    py -3.11 -m venv .venv

Activate it on Windows:

    .venv\Scripts\Activate.ps1

Install dependencies:

    pip install -r requirements.txt

Create the environment file:

    copy .env.example .env

Start the API:

    uvicorn app.main:app --reload

Open:

    http://127.0.0.1:8000/docs

## Features

- Document ingestion and chunking
- Hybrid lexical retrieval
- Reranking and query transformation
- Source citations
- Supervisor and specialized agents
- MCP knowledge and utility servers
- HTTP A2A research-agent interaction
- Input and output guardrails
- Tool authorization
- Human approval workflow
- Golden dataset evaluation
- Regression tests
- JSONL observability traces

## Evaluation

    pytest -q

Open /eval/run to evaluate retrieval and agent responses.

## Traces

Open /traces?limit=30 to inspect recent events.



--------
post/documents
--------------
{
  "title": "Password Security Policy",
  "text": "All passwords must be at least 14 characters long. Employees must use unique passwords and never share their credentials. Report suspected account compromise to the security team immediately.",
  "source": "user-upload"
}

post/ask
--------
{
  "question": "What is the minimum password length?",
  "user_id": "demo-user"
}


post/documenst
-------
{
  "title": "Enterprise Security Incident Response Process",
  "text": "The purpose of this procedure is to provide a consistent process for identifying, containing, investigating, resolving, and learning from information security incidents. Security incidents may be identified through security monitoring systems, employee reports, automated alerts, vulnerability assessments, or other security monitoring activities. The security team should record available information and determine whether the event represents an actual or potential security incident. The team evaluates severity based on systems affected, information affected, number of users affected, business impact, security impact, and potential regulatory requirements. Containment actions may include isolating affected systems, disabling compromised accounts, blocking malicious network traffic, and restricting access to affected resources while preserving investigation evidence. Eradication includes removing malicious software and unauthorized accounts, correcting vulnerable configurations, applying security patches, and resetting compromised credentials. Recovery includes validating system security, monitoring restored systems, confirming vulnerabilities have been addressed, and restoring business services. Lessons learned should identify what happened, how the incident was detected, which actions succeeded or failed, and what improvements are required. Documentation should include identification time, affected systems, actions performed, people involved, evidence collected, recovery actions, and final resolution. High-severity incidents should be escalated to appropriate security, technology, management, legal, or compliance teams. The lifecycle is Identification, Assessment, Containment, Eradication, Recovery, Lessons Learned, and Process Improvement.",
  "source": "incident_process(2).txt"
}

post/ask
--------
1. What are the different ways a security incident can be identified?
Copy question
2. What factors should the security team consider when assessing an incident's severity?
3. What actions can the response team take to contain a security incident?
4. What activities are performed during the eradication phase?
