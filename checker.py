import re
import json
import httpx
from urllib.parse import urlparse


class InstagramChecker:
    """
    Check Instagram profile qua Claude API.
    Claude sẽ dùng knowledge của mình để xác định verified status.
    """

    def __init__(self, anthropic_api_key: str = None):
        self.api_key = anthropic_api_key

    def extract_username(self, raw: str) -> str | None:
        raw = raw.strip().strip("/")
        if raw.startswith("@"):
            raw = raw[1:]
        if "instagram.com" in raw:
            parsed = urlparse(raw if raw.startswith("http") else "https://" + raw)
            parts = [p for p in parsed.path.strip("/").split("/") if p]
            return parts[0].lower() if parts else None
        if re.match(r"^[\w.]+$", raw):
            return raw.lower()
        return None

    async def check(self, username: str) -> dict:
        empty = {
            "status": "unknown", "verified": None, "full_name": None,
            "follower_count": None, "is_private": None,
            "profile_pic_url": None, "bio": None,
        }

        if not self.api_key:
            return empty

        try:
            return await self._check_via_claude(username)
        except Exception as e:
            return empty

    async def _check_via_claude(self, username: str) -> dict:
        empty = {
            "status": "unknown", "verified": None, "full_name": None,
            "follower_count": None, "is_private": None,
            "profile_pic_url": None, "bio": None,
        }

        prompt = (
            f"Do you know the Instagram account @{username}? "
            f"Based on your knowledge, does this account exist on Instagram "
            f"and does it have a blue verification badge (verified account)?\n\n"
            f"Reply ONLY with valid JSON, nothing else:\n"
            f'If account exists and verified: {{"status":"live","verified":true,"full_name":"Their Name"}}\n'
            f'If account exists but not verified: {{"status":"live","verified":false,"full_name":"Their Name"}}\n'
            f'If account does not exist or was deleted: {{"status":"die","verified":false,"full_name":null}}\n'
            f'If you are not sure: {{"status":"unknown","verified":null,"full_name":null}}'
        )

        payload = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 150,
            "messages": [{"role": "user", "content": prompt}]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                }
            )

        if r.status_code != 200:
            return empty

        data = r.json()
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")

        if not text.strip():
            return empty

        try:
            json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "status": result.get("status", "unknown"),
                    "verified": result.get("verified"),
                    "full_name": result.get("full_name"),
                    "follower_count": None,
                    "is_private": None,
                    "profile_pic_url": None,
                    "bio": None,
                }
        except Exception:
            pass

        return empty

    def format_status(self, info: dict) -> str:
        status   = info.get("status", "unknown")
        verified = info.get("verified")
        if status == "die":
            return "❌ DIE"
        if status == "unknown":
            return "⚪ UNKNOWN"
        verified_str = "🔵 Có tích xanh" if verified else "⚪ Không có tích xanh"
        return f"✅ LIVE | {verified_str}"
