from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from sqlalchemy.orm import Session

import models
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

# Create the FastAPI application.
app = FastAPI()

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

# --------------------
# Issue Models
# --------------------

class IssueCreate(BaseModel):
    title: str
    description: str
    priority: str


class IssueUpdate(BaseModel):
    title: str
    description: str
    status: str
    priority: str


class Issue(BaseModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --------------------
# Temporary Data Store
# --------------------

issues: list[Issue] = []
next_issue_id = 1


# --------------------
# CRUD Endpoints
# --------------------

@app.post("/issues", response_model=Issue, status_code=201)
def create_issue(issue: IssueCreate, db: Session = Depends(get_db)):
    new_issue = models.IssueModel(
        title=issue.title,
        description=issue.description,
        status="open",
        priority=issue.priority,
    )

    db.add(new_issue)
    db.commit()
    db.refresh(new_issue)

    return new_issue

@app.get("/issues", response_model=list[Issue])
def get_issues():
    return issues


@app.get("/issues/{issue_id}", response_model=Issue)
def get_issue(issue_id: int):
    for issue in issues:
        if issue.id == issue_id:
            return issue

    raise HTTPException(status_code=404, detail="Issue not found")


@app.put("/issues/{issue_id}", response_model=Issue)
def update_issue(issue_id: int, updated_data: IssueUpdate):
    for index, issue in enumerate(issues):
        if issue.id == issue_id:
            updated_issue = Issue(
                id=issue.id,
                title=updated_data.title,
                description=updated_data.description,
                status=updated_data.status,
                priority=updated_data.priority,
                created_at=issue.created_at,
            )

            issues[index] = updated_issue
            return updated_issue

    raise HTTPException(status_code=404, detail="Issue not found")


@app.delete("/issues/{issue_id}", status_code=204)
def delete_issue(issue_id: int):
    for index, issue in enumerate(issues):
        if issue.id == issue_id:
            issues.pop(index)
            return

    raise HTTPException(status_code=404, detail="Issue not found")