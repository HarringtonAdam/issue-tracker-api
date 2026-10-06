from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, ConfigDict, StringConstraints
from typing import Annotated
from datetime import datetime
from enum import Enum

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


class IssueStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    closed = "closed"

class IssuePriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


# --------------------
# Issue Models
# --------------------

IssueTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
IssueDescription = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=1000)
]


class IssueCreate(BaseModel):
    title: IssueTitle
    description: IssueDescription | None = None
    priority: IssuePriority = IssuePriority.medium


class IssueUpdate(BaseModel):
    title: IssueTitle | None = None
    description: IssueDescription | None = None
    status: IssueStatus | None = None
    priority: IssuePriority | None = None


class Issue(BaseModel):
    id: int
    title: str
    description: str
    status: IssueStatus
    priority: IssuePriority
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# --------------------
# CRUD Endpoints
# --------------------

@app.post("/issues", response_model=Issue, status_code=201)
def create_issue(issue: IssueCreate, db: Session = Depends(get_db)):
    new_issue = models.IssueModel(
        title=issue.title,
        description=issue.description,
        status="open",
        priority=issue.priority.value,
    )

    db.add(new_issue)
    db.commit()
    db.refresh(new_issue)

    return new_issue

@app.get("/issues", response_model=list[Issue])
def get_issues(db: Session = Depends(get_db)):
    db_issues = db.query(models.IssueModel).all()

    return db_issues


@app.get("/issues/{issue_id}", response_model=Issue)
def get_issue(issue_id: int, db: Session = Depends(get_db)):
    issue = (
        db.query(models.IssueModel)
        .filter(models.IssueModel.id == issue_id)
        .first()
    )

    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")

    return issue

@app.put("/issues/{issue_id}", response_model=Issue)
def update_issue(
    issue_id: int,
    updated_data: IssueUpdate,
    db: Session = Depends(get_db),
):
    issue = (
        db.query(models.IssueModel)
        .filter(models.IssueModel.id == issue_id)
        .first()
    )

    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")

    if updated_data.title is not None:
        issue.title = updated_data.title
    if updated_data.description is not None:
        issue.description = updated_data.description
    if updated_data.status is not None:
        issue.status = updated_data.status.value
    if updated_data.priority is not None:
        issue.priority = updated_data.priority.value

    db.commit()
    db.refresh(issue)

    return issue


@app.delete("/issues/{issue_id}", status_code=204)
def delete_issue(
    issue_id: int,
    db: Session = Depends(get_db),
):
    issue = (
        db.query(models.IssueModel)
        .filter(models.IssueModel.id == issue_id)
        .first()
    )

    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")

    db.delete(issue)
    db.commit()

    return
