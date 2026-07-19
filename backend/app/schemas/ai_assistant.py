from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="Either 'user' or 'assistant'.")
    content: str


class ScenarioChatRequest(BaseModel):
    municipality_name: str
    business_subcategory: str
    radius_km: float
    question: str
    chat_history: List[ChatMessage] = Field(default_factory=list)
    model: Optional[str] = Field(
        default=None,
        description="Optional Ollama model override. Example: llama3.2:3b or mistral.",
    )


class ScenarioChatResponse(BaseModel):
    status: str
    answer: str
    model: str
    ai_provider: str
    municipality_name: str
    business_subcategory: str
    radius_km: float
    used_signals: List[str]
    limitations: List[str]
    follow_up_suggestions: List[str]
    scenario_snapshot: Dict[str, Any]
    raw_ai_available: bool
    error: Optional[str] = None


class LocalAIStatusResponse(BaseModel):
    status: str = Field(
        ...,
        description="ready | model_missing | unavailable",
    )
    provider: str = "ollama"
    base_url: str
    default_model: str
    available_models: List[str] = Field(default_factory=list)
    message: str

    # AI health details: what actually drives local response quality.
    ollama_version: Optional[str] = Field(
        default=None, description="Running Ollama version, or null if unreachable."
    )
    model_installed: bool = Field(
        default=False, description="Whether the configured default_model is pulled."
    )
    structured_outputs: bool = Field(
        default=False,
        description="Whether schema-constrained JSON is active (needs Ollama >= 0.5).",
    )
    structured_outputs_note: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
