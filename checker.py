import re
import json
import httpx
from urllib.parse import urlparse
import asyncio

class InstagramChecker:
    """
    Check trạng thái public Instagram profile:
    - Tài khoản còn tồn tại không (live/die)
    - Có tích xanh (verified) không
    """

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }

    HEADERS_API = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "X-IG-App-ID": "936619743392459",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.instagram.com/",
        "Origin": "https://www.instagram.com",
    }

    def extract_username(self, raw: str) -> str | None:
        """Trích xuất username từ URL hoặc @username hoặc username."""
        raw = raw.strip().strip("/")

        # Bỏ @ nếu có
        if raw.startswith("@"):
            raw = raw[1:]

        # Nếu là URL
        if "instagram.com" in raw:
            parsed = urlparse(raw if raw.startswith("http") else "https://" + raw)
            parts = [p for p in parsed.path.strip("/").split("/") if p]
            if parts:
                return parts[0].lower()
            return None

        # Username thuần
        if re.match(r"^[\w.]+$", raw):
            return raw.lower()

        return None

    async def check(self, username: str) -> dict:
        """
        Kiểm tra Instagram profile.
        
        Trả về dict:
        {
            "status": "live" | "die" | "unknown",
            "verified": True | False | None,
            "full_name": str | None,
            "follower_count": int | None,
            "is_private": bool | None,
            "profile_pic_url": str | None,
            "bio": str | None,
        }
        """
        result = {
            "status": "unknown",
            "verified": None,
            "full_name": None,
            "follower_count": None,
            "is_private": None,
            "profile_pic_url": None,
            "bio": None,
        }

        # Thử API endpoint trước
        api_result = await self._check_api(username)
        if api_result["status"] != "unknown":
            return api_result

        # Fallback: scrape trang HTML
        html_result = await self._check_html(username)
        if html_result["status"] != "unknown":
            return html_result

        return result

    async def _check_api(self, username: str) -> dict:
        """Dùng Instagram internal API."""
        result = {"status": "unknown", "verified": None, "full_name": None,
                  "follower_count": None, "is_private": None, "profile_pic_url": None, "bio": None}
        try:
            url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
            async with httpx.AsyncClient(
                headers=self.HEADERS_API, follow_redirects=True, timeout=15.0
            ) as client:
                r = await client.get(url)

            if r.status_code == 404:
                result["status"] = "die"
                return result

            if r.status_code != 200:
                return result

            data = r.json()
            user = data.get("data", {}).get("user")

            if not user:
                result["status"] = "die"
                return result

            result["status"] = "live"
            result["verified"] = bool(user.get("is_verified", False))
            result["full_name"] = user.get("full_name") or None
            result["follower_count"] = user.get("edge_followed_by", {}).get("count")
            result["is_private"] = bool(user.get("is_private", False))
            result["bio"] = user.get("biography") or None
            result["profile_pic_url"] = user.get("profile_pic_url_hd") or user.get("profile_pic_url")
            return result

        except Exception:
            return result

    async def _check_html(self, username: str) -> dict:
        """Scrape từ trang HTML Instagram."""
        result = {"status": "unknown", "verified": None, "full_name": None,
                  "follower_count": None, "is_private": None, "profile_pic_url": None, "bio": None}
        try:
            url = f"https://www.instagram.com/{username}/"
            async with httpx.AsyncClient(
                headers=self.HEADERS, follow_redirects=True, timeout=15.0
            ) as client:
                r = await client.get(url)

            if r.status_code == 404:
                result["status"] = "die"
                return result

            if r.status_code != 200:
                return result

            body = r.text

            # Tài khoản không tồn tại
            die_patterns = [
                "Sorry, this page isn't available",
                "The link you followed may be broken",
                "Trang này không khả dụng",
            ]
            for p in die_patterns:
                if p.lower() in body.lower():
                    result["status"] = "die"
                    return result

            # Tìm JSON data trong _sharedData hoặc script tags
            # Cách 1: window._sharedData
            shared_match = re.search(r'window\._sharedData\s*=\s*({.*?});</script>', body, re.DOTALL)
            if shared_match:
                try:
                    shared = json.loads(shared_match.group(1))
                    user = (shared.get("entry_data", {})
                                  .get("ProfilePage", [{}])[0]
                                  .get("graphql", {})
                                  .get("user", {}))
                    if user:
                        result["status"] = "live"
                        result["verified"] = bool(user.get("is_verified", False))
                        result["full_name"] = user.get("full_name") or None
                        result["is_private"] = bool(user.get("is_private", False))
                        result["profile_pic_url"] = user.get("profile_pic_url_hd")
                        result["bio"] = user.get("biography") or None
                        result["follower_count"] = (user.get("edge_followed_by") or {}).get("count")
                        return result
                except Exception:
                    pass

            # Cách 2: Tìm "is_verified" trong script tags
            verified_match = re.search(r'"is_verified"\s*:\s*(true|false)', body)
            if verified_match:
                result["status"] = "live"
                result["verified"] = verified_match.group(1) == "true"

                # Lấy thêm full_name
                name_match = re.search(r'"full_name"\s*:\s*"([^"]*)"', body)
                if name_match:
                    result["full_name"] = name_match.group(1)

                # Followers
                follower_match = re.search(r'"edge_followed_by"\s*:\s*\{"count"\s*:\s*(\d+)', body)
                if follower_match:
                    result["follower_count"] = int(follower_match.group(1))

                return result

            # Cách 3: Check meta tags
            if 'property="og:title"' in body or "instagram.com" in r.url.host:
                title_match = re.search(r'<title[^>]*>([^<]+)</title>', body)
                if title_match and "instagram" in title_match.group(1).lower():
                    result["status"] = "live"
                    return result

            # 200 nhưng không parse được → coi là live
            if r.status_code == 200:
                result["status"] = "live"
                return result

        except Exception:
            pass

        return result

    def format_status(self, info: dict) -> str:
        """Format thông tin profile thành text đẹp."""
        status = info.get("status", "unknown")
        verified = info.get("verified")

        if status == "die":
            return "❌ DIE"
        if status == "unknown":
            return "⚪ UNKNOWN"

        # Live
        verified_str = "🔵 Có tích xanh" if verified else "⚪ Không có tích xanh"
        return f"✅ LIVE | {verified_str}"