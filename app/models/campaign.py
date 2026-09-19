from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- Pydantic Schemas (Used for API Validation) ---

class CampaignBase(BaseModel):
    name: str
    description: Optional[str] = None
    icp: str # Ideal Customer Profile description
    status: str = "Draft" # Draft, Live, Paused, Completed, Archived

class CampaignCreate(CampaignBase):
    pass

class CampaignResponse(CampaignBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- SQLAlchemy Models (Your teammate will expand this) ---
# Example of what your teammate will write to map this to PostgreSQL
'''
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class DBCampaign(Base):
    __tablename__ = "campaigns"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True)
    description = Column(String)
    icp = Column(String)
    status = Column(String, default="Draft")
    created_at = Column(DateTime, default=datetime.utcnow)
'''
