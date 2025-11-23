from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


Channel = Literal["dream", "oracle", "sports", "audio", "text", "system"]


class ResonanceFrame(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    source: str                         # module name
    channel: Channel                    # high-level domain

    text: Optional[str] = None          # optional natural language payload
    tags: List[str] = Field(default_factory=list)

    # Dense numeric representation (embedding, features, etc.)
    numeric_vector: Optional[List[float]] = None

    # Symbolic state: runes, archetypes, labels
    symbolic_state: List[str] = Field(default_factory=list)

    # Attachments for later expansion
    attachments: Dict[str, Any] = Field(default_factory=dict)

    # Internal metrics / scoring
    metrics: Dict[str, float] = Field(default_factory=dict)
