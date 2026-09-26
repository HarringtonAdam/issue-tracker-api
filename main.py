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

    issue.title = updated_data.title
    issue.description = updated_data.description
    issue.status = updated_data.status
    issue.priority = updated_data.priority

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