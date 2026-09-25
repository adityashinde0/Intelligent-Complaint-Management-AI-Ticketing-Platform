import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional
from app.core.config import settings

def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _b64decode(data: str) -> bytes:
    padding = "=" * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode(data + padding)

def create_access_token(payload: Dict[str, Any], expires_in_seconds: Optional[int] = None) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    exp = int(time.time()) + (expires_in_seconds or (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60))
    to_encode = {**payload, "exp": exp, "iat": int(time.time())}
    
    header_encoded = _b64encode(json.dumps(header).encode("utf-8"))
    payload_encoded = _b64encode(json.dumps(to_encode).encode("utf-8"))
    
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"{header_encoded}.{payload_encoded}".encode("utf-8"),
        hashlib.sha256
    ).digest()
    signature_encoded = _b64encode(signature)
    
    return f"{header_encoded}.{payload_encoded}.{signature_encoded}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    parts = token.split(".")
    if len(parts) != 3:
        return None
    header_encoded, payload_encoded, signature_encoded = parts
    
    expected_sig = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"{header_encoded}.{payload_encoded}".encode("utf-8"),
        hashlib.sha256
    ).digest()
    
    if not hmac.compare_digest(signature_encoded, _b64encode(expected_sig)):
        return None
        
    try:
        payload = json.loads(_b64decode(payload_encoded).decode("utf-8"))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None
