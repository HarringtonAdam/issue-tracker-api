from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# Create the FastAPI application.
app = FastAPI()


# This describes the information a user must provide
# when creating a new issue.
class IssueCreate(BaseModel):
    title: str
    description: str
    priority: str


# This describes a complete issue after our application
# has created it.
class Issue(BaseModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    created_at: datetime


# Temporary storage for our issues.
# PostgreSQL will replace this later.
issues: list[Issue] = []


@app.get("/")
def root():
    return {"message": "Incident Tracker API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/issues", response_model=Issue, status_code=201)
def create_issue(issue_data: IssueCreate):
    new_issue = Issue(
        id=len(issues) + 1,
        title=issue_data.title,
        description=issue_data.description,
        status="open",
        priority=issue_data.priority,
        created_at=datetime.now(timezone.utc),
    )

    issues.append(new_issue)

    return new_issue


@app.get("/issues", response_model=list[Issue])
def get_issues():
    return issues


@app.get("/issues/{issue_id}", response_model=Issue)
def get_issue(issue_id: int):
    for issue in issues:
        if issue.id == issue_id:
            return issue

    raise HTTPException(
        status_code=404,
        detail="Issue not found",
    )