from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class VoiceProfileSet(BaseModel):
    tone: Optional[str] = Field(None, description="Free-text tone, e.g. 'warm, conversational'")
    pov: Optional[Literal["first_person", "second_person", "third_person", "first-person", "second-person", "third-person"]] = Field(None, description="Point of view")

    @classmethod
    def normalize_pov(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.replace("-", "_")
        return v
    banned_words: Optional[list[str]] = Field(None, max_length=50, description="Words/phrases to avoid, max 50 items")
    extra_instructions: Optional[str] = Field(None, max_length=2000, description="Free-text catch-all, max 2000 chars")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tone": "professional, objective",
                "pov": "third_person",
                "banned_words": ["in conclusion", "synergy"],
                "extra_instructions": "Always provide concise answers."
            }
        }
    )

class VoiceProfileResponse(VoiceProfileSet):
    id: UUID
    client_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
