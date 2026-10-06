"""Fähigkeiten der Modelle im LiteLLM-Proxy prüfen (SW4-Checkliste: Function Calling, strukturierte Ausgabe).

    uv run ea-check-models

Pro Modell aus config/models.toml: (1) einfacher Chat, (2) strukturierte Ausgabe per Function Calling,
(3) per JSON Schema. Das Ergebnis bestimmt den Eintrag ``structured_output`` in config/models.toml.
"""

from __future__ import annotations

import json
import time
import urllib.request

from pydantic import BaseModel

from einkaufsagent.config import litellm_settings, load_models
from einkaufsagent.llm import build_chat_model


class Probe(BaseModel):
    payment_days: int
    discount_pct: float


PROMPT = "Gib als Beispiel ein Konditionspaket mit Zahlungsziel 45 Tage und Rabatt 1.5 % zurück."


def list_proxy_models() -> list[str]:
    base, key = litellm_settings()
    root = base.rstrip("/").removesuffix("/v1")
    req = urllib.request.Request(f"{root}/v1/models", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return [m["id"] for m in json.load(r)["data"]]


def probe(model_id: str) -> dict[str, str]:
    cfg = load_models()[model_id]
    llm = build_chat_model(cfg)
    res: dict[str, str] = {}
    t0 = time.perf_counter()
    try:
        out = llm.invoke("Antworte nur mit OK.")
        res["chat"] = f"ok ({time.perf_counter() - t0:.1f}s): {str(out.content)[:20]!r}"
    except Exception as e:
        res["chat"] = f"FEHLER {type(e).__name__}: {str(e)[:80]}"
    for method in ("function_calling", "json_schema"):
        try:
            out = llm.with_structured_output(Probe, method=method, include_raw=True).invoke(PROMPT)
            p = out["parsed"]
            res[method] = "ok" if p and p.payment_days == 45 else f"falsch/leer: {out.get('parsing_error')}"
        except Exception as e:
            res[method] = f"FEHLER {type(e).__name__}: {str(e)[:80]}"
    return res


def main() -> None:
    available = list_proxy_models()
    print("Im Proxy verfügbar:", ", ".join(available), "\n")
    for model_id in load_models():
        if model_id not in available:
            print(f"{model_id}: NICHT im Proxy")
            continue
        r = probe(model_id)
        rec = (
            "function_calling"
            if r["function_calling"] == "ok"
            else "json_schema"
            if r["json_schema"] == "ok"
            else "–"
        )
        print(
            f"{model_id}\n  chat: {r['chat']}\n  function_calling: {r['function_calling']}\n"
            f'  json_schema: {r["json_schema"]}\n  → structured_output = "{rec}"\n'
        )


if __name__ == "__main__":
    main()
