#!/usr/bin/env python3
"""OpenAI-compatible LLM client used by the executor role."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROLE_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROLE_DIR.parents[1]
DEFAULT_CONFIG = {
    "api_type": "openai",
    "model": "gpt-5.4-nano",
    "base_url": "https://api.openai.com/v1",
    "api_key": "${OPENAI_API_KEY}",
}


def _load_env_files(paths: list[Path]) -> None:
    """Load local .env values without overriding explicit shell variables."""
    for path in paths:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_env_files([REPO_ROOT / ".env", REPO_ROOT.parent / ".env"])


def _expand_env(value: str) -> str:
    if value.startswith("${") and value.endswith("}"):
        return os.environ.get(value[2:-1], "")
    return value


def load_llm_config(config_path: str | None = None) -> dict[str, Any]:
    config = DEFAULT_CONFIG.copy()
    candidates = []
    if config_path:
        candidates.append(Path(config_path))
    candidates.extend(
        [
            ROLE_DIR / "llm_config.json",
            Path("llm_config.json"),
            Path("llm_config.example.json"),
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            with candidate.open("r", encoding="utf-8-sig") as handle:
                loaded = json.load(handle)
            if not isinstance(loaded, dict):
                raise ValueError(f"LLM config must be a JSON object: {candidate}")
            config.update(loaded)
            break

    if os.environ.get("EXECUTOR_LLM_BASE_URL"):
        config["base_url"] = os.environ["EXECUTOR_LLM_BASE_URL"]
    elif os.environ.get("OPENAI_BASE_URL"):
        config["base_url"] = os.environ["OPENAI_BASE_URL"]
    if os.environ.get("EXECUTOR_LLM_MODEL"):
        config["model"] = os.environ["EXECUTOR_LLM_MODEL"]
    elif os.environ.get("OPENAI_MODEL"):
        config["model"] = os.environ["OPENAI_MODEL"]
    if os.environ.get("EXECUTOR_LLM_API_KEY"):
        config["api_key"] = os.environ["EXECUTOR_LLM_API_KEY"]
    elif os.environ.get("OPENAI_API_KEY"):
        config["api_key"] = os.environ["OPENAI_API_KEY"]
        if not os.environ.get("EXECUTOR_LLM_BASE_URL") and not os.environ.get("OPENAI_BASE_URL"):
            config["base_url"] = "https://api.openai.com/v1"
        if str(config.get("model", "")).startswith(("openrouter/", "inclusionai/")):
            config["model"] = os.environ.get("EXECUTOR_LLM_MODEL") or os.environ.get("OPENAI_MODEL") or DEFAULT_CONFIG["model"]
    elif (
        os.environ.get("OPENROUTER_API_KEY")
        and (
            "openrouter.ai" in str(config.get("base_url", ""))
            or str(config.get("model", "")).startswith(("openrouter/", "inclusionai/"))
        )
    ):
        config["api_key"] = os.environ["OPENROUTER_API_KEY"]

    api_key = config.get("api_key", "")
    if isinstance(api_key, str):
        config["api_key"] = _expand_env(api_key)
    return config


def has_llm_credentials(config: dict[str, Any]) -> bool:
    return bool(config.get("api_key"))


def chat_completion(
    config: dict[str, Any],
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 1500,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    if config.get("api_type", "openai") != "openai":
        raise ValueError(f"unsupported api_type: {config.get('api_type')}")

    base_url = str(config.get("base_url", "")).rstrip("/")
    model = str(config.get("model", ""))
    api_key = str(config.get("api_key", ""))
    if not base_url or not model or not api_key:
        raise ValueError("LLM config requires base_url, model, and api_key")

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if "openrouter.ai" in base_url:
        headers.update(
            {
                "HTTP-Referer": "https://github.com/BrianPengT/multi-agent-hackathon",
                "X-Title": "multi-agent-hackathon executor",
            }
        )

    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers=headers,
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM HTTP error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    data = json.loads(body)
    if not isinstance(data, dict):
        raise RuntimeError("LLM response was not a JSON object")
    return data


def extract_text(completion: dict[str, Any]) -> str:
    choices = completion.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return content if isinstance(content, str) else ""
