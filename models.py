from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class ChatHistory(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    role: str  
    content: str
    mode_used: str = Field(default="Standard") 
    timestamp: datetime = Field(default_factory=datetime.utcnow)