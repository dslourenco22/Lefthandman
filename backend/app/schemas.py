"""Pydantic v2 schemas for API I/O."""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ---- Auth ----
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = ""
    role: str = "hr"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


# ---- Job descriptions ----
DEFAULT_WEIGHTS = {
    "skills": 0.40,
    "experience": 0.20,
    "education": 0.10,
    "certifications": 0.10,
    "projects": 0.10,
    "soft_skills": 0.05,
    "keywords": 0.05,
}


class JobCreate(BaseModel):
    title: str
    raw_text: str
    weights: dict[str, float] | None = None


class JobOut(BaseModel):
    id: int
    title: str
    required_skills: list[str]
    preferred_skills: list[str]
    certifications: list[str]
    education: list[str]
    keywords: list[str]
    soft_skills: list[str]
    industry_terms: list[str]
    min_years_experience: float
    weights: dict
    created_at: datetime

    class Config:
        from_attributes = True


class WeightsUpdate(BaseModel):
    weights: dict[str, float]


class SkillsUpdate(BaseModel):
    required_skills: list[str]
    preferred_skills: list[str] = []


# ---- Candidates / scores ----
class ScoreOut(BaseModel):
    overall: float
    breakdown: dict
    matched_skills: list[str]
    missing_skills: list[str]
    strengths: list[str]
    weaknesses: list[str]
    recommendation: str
    recommendation_reason: str
    summary: str

    class Config:
        from_attributes = True


class CandidateOut(BaseModel):
    id: int
    job_id: int
    name: str
    email: str
    phone: str
    linkedin: str
    github: str
    location: str
    years_experience: float
    summary: str
    certifications: list[str]
    education: list
    status: str
    score: ScoreOut | None = None

    class Config:
        from_attributes = True


class RankedCandidate(BaseModel):
    rank: int
    candidate: CandidateOut


class ProcessingStatus(BaseModel):
    job_id: int
    total: int
    scored: int
    processing: int
    pending: int
    errored: int
    done: bool
