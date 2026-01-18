from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


# Repository schemas
class RepositoryCreate(BaseModel):
    github_url: str = Field(..., description="GitHub repository URL")


class RepositoryResponse(BaseModel):
    id: UUID
    github_url: str
    name: str
    owner: str
    default_branch: str
    last_commit_hash: str | None
    summary: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RepositoryListResponse(BaseModel):
    repositories: list[RepositoryResponse]
    total: int


# Directory schemas
class DirectoryResponse(BaseModel):
    id: UUID
    path: str
    name: str
    summary: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DirectoryDetailResponse(DirectoryResponse):
    children: list["DirectoryResponse"]
    files: list["FileResponse"]


# File schemas
class FileResponse(BaseModel):
    id: UUID
    path: str
    name: str
    language: str | None
    summary: str | None
    line_count: int | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FileDetailResponse(FileResponse):
    code_units: list["CodeUnitResponse"]


# CodeUnit schemas
class CodeUnitResponse(BaseModel):
    id: UUID
    type: str
    name: str
    start_line: int
    end_line: int
    signature: str | None
    description: str | None
    metadata: dict | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CodeUnitDetailResponse(CodeUnitResponse):
    children: list["CodeUnitResponse"]


# Tree schemas
class TreeNode(BaseModel):
    id: UUID
    name: str
    path: str
    type: str  # 'directory' or 'file'
    summary: str | None
    children: list["TreeNode"] | None = None
    language: str | None = None


# AnalysisJob schemas
class AnalysisJobResponse(BaseModel):
    id: UUID
    repository_id: UUID
    status: str
    job_type: str
    progress: int
    total_files: int | None
    processed_files: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class AnalysisJobListResponse(BaseModel):
    jobs: list[AnalysisJobResponse]
    total: int


# GitHub OAuth schemas
class GitHubTokenResponse(BaseModel):
    access_token: str
    token_type: str


class GitHubUserResponse(BaseModel):
    login: str
    avatar_url: str
    name: str | None


# Rebuild models for forward references
DirectoryDetailResponse.model_rebuild()
FileDetailResponse.model_rebuild()
CodeUnitDetailResponse.model_rebuild()
TreeNode.model_rebuild()
