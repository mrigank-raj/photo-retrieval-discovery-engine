"""Thin Gemini client for the free tier: paced requests, JSON-schema output, backoff, and a stop when the daily quota is gone.

Billing is never enabled anywhere; when a per-day quota is exhausted we raise DailyQuotaExhausted and resume tomorrow.
"""
import json
import os
import time

import requests

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
usage = {"requests": 0, "retries": 0, "prompt_tokens": 0, "output_tokens": 0}
_last_call = [0.0]


class DailyQuotaExhausted(RuntimeError):
    pass


def generate_json(model, prompt, schema, *, rpm=10, max_output_tokens=8192, thinking_budget=None, retries=5):
    """Return the parsed JSON answer. Sleeps to stay under `rpm` requests per minute."""
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema,
                                 "maxOutputTokens": max_output_tokens, "temperature": 0}}
    if thinking_budget is not None:
        body["generationConfig"]["thinkingConfig"] = {"thinkingBudget": thinking_budget}
    for attempt in range(retries + 1):
        wait = 60.0 / rpm - (time.time() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.time()
        try:
            r = requests.post(f"{BASE}/{model}:generateContent", params={"key": os.environ["GEMINI_API_KEY"]},
                              json=body, timeout=180)
        except (requests.Timeout, requests.ConnectionError):
            if attempt == retries:
                raise
            usage["retries"] += 1
            time.sleep(min(60, 5 * 2 ** attempt))
            continue
        usage["requests"] += 1
        if r.status_code == 200:
            j = r.json()
            u = j.get("usageMetadata", {})
            usage["prompt_tokens"] += u.get("promptTokenCount", 0)
            usage["output_tokens"] += u.get("candidatesTokenCount", 0)
            try:
                return json.loads(j["candidates"][0]["content"]["parts"][0]["text"])
            except (KeyError, IndexError, ValueError) as e:
                if attempt == retries:
                    raise RuntimeError(f"unusable model answer: {e}; finishReason="
                                       f"{j.get('candidates', [{}])[0].get('finishReason')}") from e
        elif r.status_code == 429 and _is_daily(r.text):
            raise DailyQuotaExhausted(f"model {model}: {_quota_detail(r)}")
        elif r.status_code in (429, 500, 503) and attempt < retries:
            pass
        else:
            raise RuntimeError(f"gemini {r.status_code}: {r.text[:300].replace(os.environ['GEMINI_API_KEY'], '<key>')}")
        usage["retries"] += 1
        time.sleep(min(60, 5 * 2 ** attempt))
    raise RuntimeError("gemini: retries exhausted")


def _quota_detail(r):
    """Name the exhausted quota and its limit, e.g. 'GenerateRequestsPerDayPerProjectPerModel-FreeTier limit 20'."""
    try:
        for d in r.json()["error"].get("details", []):
            for v in d.get("violations", []):
                return f"{v.get('quotaId')} limit {v.get('quotaValue')}"
    except (ValueError, KeyError, TypeError):
        pass
    return r.text[:200].replace(os.environ["GEMINI_API_KEY"], "<key>")


def _is_daily(text):
    t = text.lower()
    return "perday" in t or "per day" in t or "daily" in t
