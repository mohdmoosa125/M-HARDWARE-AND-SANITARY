"""
image_generation.py
-------------------
Provider adapters behind ONE interface.

    generate_image(prompt, negative_prompt=None, reference_image=None, provider=None) -> dict
        {"success": bool, "image_bytes": bytes|None, "provider": str, "model": str,
         "metadata": {...}, "error": str|None}

    generate_with_fallback(prompt, negative_prompt, reference_image, providers, log) -> dict

COST SAFETY: only providers listed in .env are ever called, in this order:
    IMAGE_PROVIDER=gemini
    IMAGE_FALLBACK_PROVIDERS=openai        (empty = no fallback)
A listed provider without its API key is skipped (no request is made). With nothing
configured, no network call happens at all.

API status (checked against the official docs on 2026-10-07):
    gemini    VERIFIED   POST /v1beta/interactions, header x-goog-api-key
    openai    VERIFIED   POST /v1/images/generations and /v1/images/edits, field b64_json
    stability UNVERIFIED written from the public Stable Image "core" API; docs not reachable
    replicate UNVERIFIED written from the public predictions API; docs not reachable
Model names change often: set IMAGE_MODEL (primary) or <PROVIDER>_IMAGE_MODEL in .env.
Secrets are read from the environment only and are redacted from every error message.
"""
import base64
import os
import time

import requests

import config  # noqa: F401  (importing it loads backend/.env)

TIMEOUT = 120
MAX_PROVIDERS_PER_PRODUCT = 3

KEY_VARS = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "stability": "STABILITY_API_KEY",
    "replicate": "REPLICATE_API_TOKEN",
}
DEFAULT_MODELS = {
    "gemini": "gemini-nano-banana-2.1",
    "openai": "gpt-image-2.5-flare",
    "stability": "stable-image-core",
    "replicate": "black-forest-labs/flux-schnell",
}

# per-run state, reset by reset_run_state()
_rate_hits = {}
_disabled = set()           # providers switched off for this run (auth failure / repeated 429)


class ProviderError(Exception):
    def __init__(self, message, transient=False, fatal=False):
        super().__init__(message)
        self.transient, self.fatal = transient, fatal


def reset_run_state():
    _rate_hits.clear()
    _disabled.clear()


# ------------------------------------------------------------------ configuration
def _names(value):
    return [n.strip().lower() for n in (value or "").split(",") if n.strip()]


def configured_chain(forced=None):
    """Provider names to try, in order, exactly as configured (never auto-extended)."""
    if forced:
        return [forced.lower()]
    chain = []
    for n in _names(os.getenv("IMAGE_PROVIDER")) + _names(os.getenv("IMAGE_FALLBACK_PROVIDERS")):
        if n in KEY_VARS and n not in chain:
            chain.append(n)
    return chain


def has_credentials(provider):
    return bool(os.getenv(KEY_VARS.get(provider, ""), "").strip())


def usable_chain(forced=None):
    """Configured providers that actually have credentials."""
    return [p for p in configured_chain(forced) if has_credentials(p)][:MAX_PROVIDERS_PER_PRODUCT]


def model_for(provider):
    primary = (_names(os.getenv("IMAGE_PROVIDER")) or [None])[0]
    if provider == primary and os.getenv("IMAGE_MODEL"):
        return os.getenv("IMAGE_MODEL").strip()
    return os.getenv(f"{provider.upper()}_IMAGE_MODEL") or DEFAULT_MODELS[provider]


def _redact(text):
    text = str(text)
    for var in KEY_VARS.values():
        secret = os.getenv(var)
        if secret:
            text = text.replace(secret, "***")
    return text[:160]


# ------------------------------------------------------------------ HTTP helper
def _request(provider, method, url, **kwargs):
    """HTTP call with 429 backoff. Auth errors disable the provider for this run."""
    kwargs.setdefault("timeout", TIMEOUT)
    for attempt in range(3):
        try:
            r = requests.request(method, url, **kwargs)
        except (requests.Timeout, requests.ConnectionError) as e:
            raise ProviderError(f"network error: {type(e).__name__}", transient=True)
        if r.status_code == 429:
            _rate_hits[provider] = _rate_hits.get(provider, 0) + 1
            if _rate_hits[provider] >= 3:
                _disabled.add(provider)
                raise ProviderError("rate limited 3 times; skipped for this run", fatal=True)
            time.sleep(2 ** attempt)
            continue
        _rate_hits[provider] = 0
        if r.status_code in (401, 403):
            _disabled.add(provider)
            raise ProviderError(f"authentication failed (HTTP {r.status_code})", fatal=True)
        if r.status_code >= 500:
            raise ProviderError(f"provider error HTTP {r.status_code}", transient=True)
        if r.status_code >= 400:
            raise ProviderError(f"HTTP {r.status_code}: {_redact(r.text)}")
        return r
    raise ProviderError("rate limited", transient=True)


def _download(url):
    r = requests.get(url, timeout=TIMEOUT)
    if r.status_code != 200 or not r.content:
        raise ProviderError("could not download generated image")
    return r.content


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _find_image_b64(node):
    """Gemini interactions: locate base64 image data anywhere in the response JSON."""
    if isinstance(node, dict):
        for key in ("outputImage", "output_image"):
            if isinstance(node.get(key), dict) and node[key].get("data"):
                return node[key]["data"]
        if node.get("type") == "image" and isinstance(node.get("data"), str):
            return node["data"]
        for v in node.values():
            found = _find_image_b64(v)
            if found:
                return found
    elif isinstance(node, list):
        for v in node:
            found = _find_image_b64(v)
            if found:
                return found
    return None


# ------------------------------------------------------------------ adapters
# Each returns raw image bytes. Providers without a negative-prompt parameter get
# the "avoid" list folded into the text prompt instead of an unsupported field.
def _gemini(prompt, negative, ref, model):
    text = f"{prompt} Avoid: {negative}." if negative else prompt
    content = [{"type": "text", "text": text}]
    if ref:
        content.append({"type": "image", "mime_type": "image/png",
                        "data": base64.b64encode(_read(ref)).decode()})
    r = _request("gemini", "POST", "https://generativelanguage.googleapis.com/v1beta/interactions",
                 headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
                 json={"model": model, "input": content,
                       "response_format": {"type": "image", "mime_type": "image/png",
                                           "aspect_ratio": "1:1", "image_size": "1K"}})
    b64 = _find_image_b64(r.json())
    if not b64:
        raise ProviderError("no image in response")
    return base64.b64decode(b64)


def _openai(prompt, negative, ref, model):
    headers = {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}
    text = f"{prompt} Avoid: {negative}." if negative else prompt
    if ref:
        with open(ref, "rb") as f:
            r = _request("openai", "POST", "https://api.openai.com/v1/images/edits", headers=headers,
                         data={"model": model, "prompt": text, "size": "1024x1024"}, files={"image": f})
    else:
        r = _request("openai", "POST", "https://api.openai.com/v1/images/generations", headers=headers,
                     json={"model": model, "prompt": text, "size": "1024x1024"})
    items = r.json().get("data") or []
    if not items or not items[0].get("b64_json"):
        raise ProviderError("no image in response")
    return base64.b64decode(items[0]["b64_json"])


def _stability(prompt, negative, ref, model):                    # UNVERIFIED (see module doc)
    data = {"prompt": prompt, "aspect_ratio": "1:1", "output_format": "png"}
    if negative:
        data["negative_prompt"] = negative
    r = _request("stability", "POST", "https://api.stability.ai/v2beta/stable-image/generate/core",
                 headers={"Authorization": f"Bearer {os.environ['STABILITY_API_KEY']}",
                          "Accept": "image/*"},
                 files={"none": ""}, data=data)
    return r.content


def _replicate(prompt, negative, ref, model):                    # UNVERIFIED (see module doc)
    headers = {"Authorization": f"Bearer {os.environ['REPLICATE_API_TOKEN']}", "Prefer": "wait"}
    r = _request("replicate", "POST", f"https://api.replicate.com/v1/models/{model}/predictions",
                 headers=headers, json={"input": {"prompt": prompt, "aspect_ratio": "1:1",
                                                  "output_format": "png"}})
    pred = r.json()
    for _ in range(60):
        if pred.get("status") == "succeeded":
            out = pred.get("output")
            return _download(out[0] if isinstance(out, list) else out)
        if pred.get("status") in ("failed", "canceled"):
            raise ProviderError("prediction " + pred["status"])
        time.sleep(2)
        pred = _request("replicate", "GET", pred["urls"]["get"], headers=headers).json()
    raise ProviderError("timed out waiting for prediction", transient=True)


ADAPTERS = {"gemini": _gemini, "openai": _openai, "stability": _stability, "replicate": _replicate}


# ------------------------------------------------------------------ public interface
def generate_image(prompt, negative_prompt=None, reference_image=None, provider=None):
    """Call ONE provider (default: the primary) with a single short retry on transient errors."""
    provider = (provider or (configured_chain() or [""])[0]).lower()
    result = {"success": False, "image_bytes": None, "provider": provider,
              "model": None, "metadata": {}, "error": None}
    if provider not in ADAPTERS:
        result["error"] = "no provider configured"
        return result
    if not has_credentials(provider):
        result["error"] = f"no API key ({KEY_VARS[provider]})"
        return result
    if provider in _disabled:
        result["error"] = "disabled for this run"
        return result

    model = result["model"] = model_for(provider)
    for attempt in (1, 2):
        try:
            raw = ADAPTERS[provider](prompt, negative_prompt, reference_image, model)
        except ProviderError as e:
            result["error"] = _redact(e)
            if e.transient and attempt == 1:
                time.sleep(2)
                continue
            return result
        except Exception as e:                       # parsing / unexpected
            result["error"] = _redact(f"{type(e).__name__}: {e}")
            return result
        if not raw:
            result["error"] = "empty response"
            return result
        result.update(success=True, image_bytes=raw, error=None,
                      metadata={"reference_used": bool(reference_image)})
        return result
    return result


def generate_with_fallback(prompt, negative_prompt=None, reference_image=None, providers=None,
                           log=print, accept=None):
    """Try each provider in order; `accept(bytes) -> (ok, reason)` can reject low-quality output.
    Returns the first good result, or the last failure (success False)."""
    last = {"success": False, "image_bytes": None, "provider": None, "model": None,
            "metadata": {}, "error": "no provider available"}
    for name in providers if providers is not None else usable_chain():
        res = generate_image(prompt, negative_prompt, reference_image, name)
        if res["success"] and accept:
            ok, reason = accept(res["image_bytes"])
            if not ok:
                res.update(success=False, image_bytes=None, error=f"low quality: {reason}")
        log(f"           Provider: {name} -> " + ("OK" if res["success"] else f"failed ({res['error']})"))
        if res["success"]:
            return res
        last = res
    return last
