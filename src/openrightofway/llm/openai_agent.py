from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from openrightofway.utils.logging import get_logger

logger = get_logger(__name__)


def _deterministic_summary(data: Dict[str, Any]) -> str:
    events: List[Dict[str, Any]] = list(data.get("events", []))
    total = len(events)
    high_crit = sum(1 for e in events if e.get("threat", {}).get("level") in {"high", "critical"})
    alerts = len(data.get("alerts", []))
    tickets = len(data.get("tickets", []))
    parts = [
        f"Events: {total}",
        f"High/Critical: {high_crit}",
        f"Alerts sent: {alerts}",
        f"Tickets created: {tickets}",
    ]
    if total:
        # Include top-1 event brief
        top = max(
            events,
            key=lambda ev: float(ev.get("threat", {}).get("score", 0.0)),
        )
        parts.append(
            "Top event: "
            f"level={top.get('threat', {}).get('level')}, "
            f"score={top.get('threat', {}).get('score')}, "
            f"distance_m={top.get('distance_m')}"
        )
    return "; ".join(parts)


def summarize_events(data: Dict[str, Any], cfg: Any) -> str:
    """Summarize pipeline results using OpenAI if configured; otherwise return a deterministic summary.

    Requires OPENAI_API_KEY in the environment when cfg.llm.enabled is True.
    """
    # If not enabled, return deterministic summary
    if not getattr(getattr(cfg, "llm", object()), "enabled", False):
        return _deterministic_summary(data)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set; falling back to deterministic summary")
        return _deterministic_summary(data)

    try:
        # Lazy import to avoid dependency for users who don't enable LLM
        from openai import OpenAI  # type: ignore

        client = OpenAI()  # API key picked up from env
        model = getattr(cfg.llm, "model", "gpt-4o-mini")
        max_tokens = int(getattr(cfg.llm, "max_tokens", 400))

        sys = (
            "You summarize pipeline encroachment detection results for right-of-way monitoring. "
            "Be concise and include counts, severity, and any compliance notes."
        )
        user = json.dumps(
            {
                "before": data.get("before"),
                "after": data.get("after"),
                "events": data.get("events", []),
                "alerts": data.get("alerts", []),
                "tickets": data.get("tickets", []),
            }
        )
        # Use chat.completions for broad compatibility; if unavailable, fallback
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": sys},
                    {"role": "user", "content": f"Summarize this JSON: {user}"},
                ],
                max_tokens=max_tokens,
                temperature=0.2,
            )
            text = resp.choices[0].message.content or ""
            return text.strip() or _deterministic_summary(data)
        except Exception:
            # Responses API fallback if needed
            try:
                resp = client.responses.create(
                    model=model,
                    input=f"System: {sys}\nUser: Summarize this JSON: {user}",
                    max_output_tokens=max_tokens,
                )
                # The Responses API returns content in a different structure
                if resp.output_text:
                    return resp.output_text.strip()
            except Exception:
                logger.exception("OpenAI request failed; falling back to deterministic summary")
                return _deterministic_summary(data)
    except Exception:
        logger.exception("OpenAI SDK not available; falling back to deterministic summary")
        return _deterministic_summary(data)

