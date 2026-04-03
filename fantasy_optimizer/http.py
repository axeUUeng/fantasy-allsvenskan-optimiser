"""Shared HTTP utilities with exponential backoff retry."""

import time

import requests
from loguru import logger


def fetch_with_retry(
    url: str,
    max_attempts: int = 4,
    backoff_base: float = 2.0,
    timeout: int = 15,
) -> dict:
    """GET a URL and return parsed JSON, retrying with exponential backoff on failure."""
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(max_attempts):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except (
            requests.exceptions.HTTPError,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ) as e:
            last_exc = e
            if attempt < max_attempts - 1:
                wait = backoff_base**attempt
                logger.warning(
                    "Request to %s failed (attempt %d/%d): %s — retrying in %.0fs",
                    url,
                    attempt + 1,
                    max_attempts,
                    e,
                    wait,
                )
                time.sleep(wait)
            else:
                logger.error(
                    "Request to %s failed after %d attempts: %s",
                    url,
                    max_attempts,
                    e,
                )
    raise last_exc
