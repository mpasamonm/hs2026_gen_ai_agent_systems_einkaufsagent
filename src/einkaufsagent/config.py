"""Konfiguration: Umgebungsvariablen (.env) und Modellliste (config/models.toml)."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str  # Modellname, wie ihn LiteLLM listet
    label: str
    role: str
    structured_output: Literal["function_calling", "json_schema"] = "function_calling"
    reasoning_effort: str | None = None
    temperature: float | None = None
    usd_per_mtok_input: float | None = None
    usd_per_mtok_output: float | None = None

    def cost_usd(self, input_tokens: int, output_tokens: int) -> float | None:
        if self.usd_per_mtok_input is None or self.usd_per_mtok_output is None:
            return None
        return (input_tokens * self.usd_per_mtok_input + output_tokens * self.usd_per_mtok_output) / 1e6


def load_models(path: Path = ROOT / "config" / "models.toml") -> dict[str, ModelConfig]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return {m["id"]: ModelConfig.model_validate(m) for m in data["models"]}


def litellm_settings() -> tuple[str, str]:
    """Basis-URL und Key des FHNW-LiteLLM-Proxys (OpenAI-kompatibel)."""
    missing = [k for k in ("LITELLM_BASE_URL", "LITELLM_API_KEY") if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"Fehlt in .env: {', '.join(missing)} (Vorlage: .env.example)")
    return os.environ["LITELLM_BASE_URL"], os.environ["LITELLM_API_KEY"]


def flush_traces() -> None:
    """LangSmith sendet Traces im Hintergrund; vor Programmende abwarten, sonst fehlen die letzten Läufe."""
    from langchain_core.tracers.langchain import wait_for_all_tracers

    wait_for_all_tracers()
