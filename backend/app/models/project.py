from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class ProjectStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    INDEXING = "indexing"
    READY = "ready"
    ERROR = "error"

class ProjectMeta(BaseModel):
    id: str
    name: str
    source: str                          # GitHub URL or zip filename
    branch: Optional[str] = None         # active branch for GitHub projects
    is_stale: bool = False               # True when source changed but not yet reindexed
    languages: list[str] = []
    include_languages: list[str] = []    # empty = index all languages
    status: ProjectStatus = ProjectStatus.PENDING
    error_message: Optional[str] = None
    last_indexed: Optional[datetime] = None

class ProjectCreate(BaseModel):
    github_url: Optional[str] = None
    # zip upload handled via multipart form, not this model
