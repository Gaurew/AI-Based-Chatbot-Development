from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List


class JobRecord(BaseModel):
    category: str
    postTitle: str
    organizationName: str
    numVacancies: Optional[int] = None
    salary: Optional[str] = None
    ageRequirement: Optional[str] = None
    experienceRequired: Optional[str] = None
    qualification: Optional[str] = None
    location: Optional[str] = None
    lastDate: Optional[str] = None
    postedDate: Optional[str] = None
    sourceUrl: str
    tags: List[str] = Field(default_factory=list)


class ScrapeResult(BaseModel):
    records: List[JobRecord]
    errors: List[str] = Field(default_factory=list)


