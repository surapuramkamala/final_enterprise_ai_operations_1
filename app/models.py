from pydantic import BaseModel, Field


class DocumentIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=100000)
    source: str = "user-upload"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    user_id: str = "demo-user"


class WorkflowRequest(AskRequest):
    require_approval: bool = True


class ApprovalRequest(BaseModel):
    approved: bool
    user_id: str = "demo-user"


class ToolRequest(BaseModel):
    tool_name: str
    arguments: dict = {}
    user_id: str = "demo-user"