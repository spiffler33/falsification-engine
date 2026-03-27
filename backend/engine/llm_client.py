# llm_client.py -- Anthropic API client for generation and elimination passes.
# Depends on: config.py (for API key)
# Depended on by: api/pipeline.py (run-via-API endpoints)
#
# Configured to match what you'd get doing it manually in Claude.ai:
# - Opus 4.6 (latest, best adversarial reasoning)
# - Adaptive thinking (model decides depth, same as Claude.ai)
# - Web search on with generous allowance
# - 128K max output (no artificial cap)
from __future__ import annotations

import logging
from typing import Any

import anthropic

from backend.config import settings

logger = logging.getLogger(__name__)

# Opus 4.6 — latest model, supports 128K output + adaptive thinking.
MODEL = "claude-opus-4-6"

# 128K max output — let the model use what it needs.
# With adaptive thinking the model decides how much to think,
# so there's no need to manually budget thinking vs response tokens.
MAX_OUTPUT = 128000


def _get_client() -> anthropic.Anthropic:
    """Create Anthropic client. Raises if no API key configured."""
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set in .env. "
            "Configure it or use copy-paste mode instead."
        )
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _stream_to_text(client: anthropic.Anthropic, kwargs: dict[str, Any]) -> str:
    """Stream an API call and collect text blocks. Required for large prompts."""
    text_parts = []
    input_tokens = 0
    output_tokens = 0

    with client.messages.stream(**kwargs) as stream:
        response = stream.get_final_message()

    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    result = "\n".join(text_parts)
    logger.info(
        "Response: %d chars, usage: input=%d output=%d",
        len(result), input_tokens, output_tokens,
    )
    return result


def run_generation(prompt: str, use_web_search: bool = True) -> str:
    """Run the generation pass via Anthropic API.

    Configured to match Claude.ai: adaptive thinking (model decides depth),
    web search on, full output budget. The model will think as deeply as the
    prompt demands — no artificial thinking cap.

    Args:
        prompt: The full generation prompt (built by prompt_builder).
        use_web_search: Enable web search tool for current data lookups.

    Returns:
        Raw text response from the model (should contain JSON array).
    """
    client = _get_client()

    kwargs: dict[str, Any] = {
        "model": MODEL,
        "max_tokens": MAX_OUTPUT,
        "thinking": {
            "type": "adaptive",
        },
        "messages": [
            {"role": "user", "content": prompt},
        ],
    }

    if use_web_search:
        kwargs["tools"] = [
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 10,
            }
        ]

    logger.info("Calling Anthropic API for generation pass (model=%s, web_search=%s)", MODEL, use_web_search)
    return _stream_to_text(client, kwargs)


def run_elimination(prompt: str, use_web_search: bool = True) -> str:
    """Run the elimination pass via Anthropic API.

    The elimination pass benefits most from deep thinking —
    the model needs to reason carefully about falsifier states
    and cross-theory contradictions. Adaptive thinking lets
    it use as much reasoning as the task demands.

    Args:
        prompt: The full elimination prompt (built by prompt_builder).
        use_web_search: Enable web search to check live falsifier conditions.

    Returns:
        Raw text response from the model (should contain JSON array).
    """
    client = _get_client()

    kwargs: dict[str, Any] = {
        "model": MODEL,
        "max_tokens": MAX_OUTPUT,
        "thinking": {
            "type": "adaptive",
        },
        "messages": [
            {"role": "user", "content": prompt},
        ],
    }

    if use_web_search:
        kwargs["tools"] = [
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 15,  # More searches for falsifier condition checking
            }
        ]

    logger.info("Calling Anthropic API for elimination pass (model=%s, web_search=%s)", MODEL, use_web_search)
    return _stream_to_text(client, kwargs)
