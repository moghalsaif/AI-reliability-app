"""Utility functions for the reliability platform."""

import hashlib
import time
import uuid
from typing import Any, Dict, Optional


def generate_trace_id() -> str:
    """Generate a unique trace ID."""
    return str(uuid.uuid4())


def generate_span_id() -> str:
    """Generate a unique span ID."""
    return str(uuid.uuid4())[:16]


def current_timestamp_ms() -> float:
    """Current timestamp in milliseconds."""
    return time.time() * 1000


def compute_hash(content: Any) -> str:
    """Compute a stable hash for content (for deduplication, drift detection)."""
    if isinstance(content, (dict, list)):
        content = str(sorted(str(content).split()))
    else:
        content = str(content)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def safe_json_dumps(obj: Any) -> str:
    """Safely serialize to JSON, handling non-serializable types."""
    import json
    
    def default(o: Any) -> Any:
        if hasattr(o, "isoformat"):
            return o.isoformat()
        if hasattr(o, "value"):
            return o.value
        return str(o)
    
    return json.dumps(obj, default=default)


def truncate_text(text: str, max_length: int = 1000) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + f"...[{len(text) - max_length} chars omitted]"


def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result
