"""Optional GetXAPI backend for the Twitter skills."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://api.getxapi.com"


class GetXAPIError(Exception):
    """Raised when the GetXAPI backend request fails."""

    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(f"GetXAPI error {status}: {message}")


class GetXAPIClient:
    """Async-compatible Twitter helper backed by GetXAPI REST endpoints.

    Environment:
        GETXAPI_API_KEY: API key for authenticated calls.
        GETXAPI_BASE_URL: Optional API origin. Defaults to https://api.getxapi.com.
        GETXAPI_ACCOUNT: Required only for write actions.
        GETXAPI_ENABLE_ACTIONS: Set to true before writes are allowed.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        account: str | None = None,
    ):
        self._api_key = (
            api_key
            or os.getenv("GETXAPI_API_KEY")
            or os.getenv("GETXAPI_KEY")
            or ""
        )
        configured_base_url = (
            base_url or os.getenv("GETXAPI_BASE_URL") or DEFAULT_BASE_URL
        )
        self._base_url = configured_base_url.rstrip("/")
        self._account = account or os.getenv("GETXAPI_ACCOUNT") or ""

    def load_cookies(self, path: str) -> None:
        """Keep API parity with RnetTwitterClient."""

    def get_cookies(self) -> dict[str, str]:
        """Return an empty cookie set because auth comes from an API key."""

        return {}

    async def get_user_by_screen_name(self, screen_name: str) -> dict:
        users = await self.search_users(screen_name)
        normalized = screen_name.lower().lstrip("@")
        for user in users:
            candidate = str(
                user.get("screen_name")
                or user.get("username")
                or user.get("handle")
                or ""
            ).lower().lstrip("@")
            if candidate == normalized:
                return user
        if users:
            return users[0]
        raise GetXAPIError(404, f"User @{screen_name} not found")

    async def search_users(self, query: str) -> list[dict]:
        data = self._request(
            "GET",
            "/twitter/tweet/advanced_search",
            query={"q": f"from:{query.lstrip('@')}", "limit": 5},
        )
        tweets = self._extract_items(data, ("tweets", "results", "data", "items"))
        seen: dict[str, dict] = {}
        for tweet in tweets:
            author = tweet.get("author") or tweet.get("user") or {}
            if not isinstance(author, dict):
                continue
            handle = str(
                author.get("screen_name")
                or author.get("username")
                or author.get("handle")
                or ""
            ).lstrip("@")
            if handle and handle not in seen:
                seen[handle] = author
        return list(seen.values())

    async def get_user_tweets(
        self,
        user_id: str,
        count: int = 10,
    ) -> list[dict]:
        handle = str(user_id).lstrip("@")
        data = self._request(
            "GET",
            "/twitter/tweet/advanced_search",
            query={"q": f"from:{handle}", "limit": count},
        )
        tweets = self._extract_items(data, ("tweets", "results", "data", "items"))
        return [self._normalize_tweet(tweet) for tweet in tweets[:count]]

    async def search_tweets(
        self,
        query: str,
        count: int = 100,
        product: str = "Latest",
    ) -> list[dict]:
        data = self._request(
            "GET",
            "/twitter/tweet/advanced_search",
            query={"q": query, "limit": count, "queryType": product},
        )
        tweets = self._extract_items(data, ("tweets", "results", "data", "items"))
        return [self._normalize_tweet(tweet) for tweet in tweets[:count]]

    async def create_tweet(
        self,
        text: str,
        reply_to: str | None = None,
    ) -> dict:
        body: dict[str, Any] = {"account": self._required_account(), "text": text}
        if reply_to is not None:
            body["replyTo"] = reply_to
        return self._request("POST", "/twitter/tweet/create", body=body)

    async def favorite_tweet(self, tweet_id: str) -> dict:
        return self._request(
            "POST",
            f"/twitter/tweet/{tweet_id}/like",
            body={"account": self._required_account()},
        )

    async def delete_tweet(self, tweet_id: str) -> dict:
        return self._request(
            "DELETE",
            f"/twitter/tweet/{tweet_id}",
            body={"account": self._required_account()},
        )

    @staticmethod
    def extract_tweet_id(result: dict) -> str | None:
        for path in (
            ("id",),
            ("tweet", "id"),
            ("data", "id"),
            ("data", "tweet", "id"),
            ("tweet", "rest_id"),
            ("data", "tweet", "rest_id"),
        ):
            value = GetXAPIClient._get_path(result, path)
            if value:
                return str(value)
        return None

    def _request(
        self,
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict:
        if not self._api_key:
            raise GetXAPIError(401, "GETXAPI_API_KEY is not configured")
        actions_enabled = os.getenv("GETXAPI_ENABLE_ACTIONS", "").lower()
        if method != "GET" and actions_enabled != "true":
            raise GetXAPIError(
                403,
                "Set GETXAPI_ENABLE_ACTIONS=true before write actions",
            )

        url = f"{self._base_url}{path}"
        if query:
            cleaned = {
                key: value
                for key, value in query.items()
                if value is not None
            }
            if cleaned:
                url = f"{url}?{urlencode(cleaned)}"

        payload = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(url, data=payload, method=method)
        request.add_header("accept", "application/json")
        if payload is not None:
            request.add_header("content-type", "application/json")
        request.add_header("authorization", f"Bearer {self._api_key}")

        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")[:500]
            raise GetXAPIError(exc.code, message) from exc
        except URLError as exc:
            raise GetXAPIError(0, str(exc.reason)) from exc

        if not raw:
            return {}
        return json.loads(raw)

    def _required_account(self) -> str:
        if not self._account:
            raise GetXAPIError(400, "Set GETXAPI_ACCOUNT before write actions")
        return self._account

    @staticmethod
    def _extract_items(data: Any, keys: tuple[str, ...]) -> list[dict]:
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if not isinstance(data, dict):
            return []

        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                nested = GetXAPIClient._extract_items(value, keys)
                if nested:
                    return nested
        return []

    @staticmethod
    def _normalize_tweet(tweet: dict) -> dict:
        author = tweet.get("author") or tweet.get("user") or {}
        if isinstance(author, dict):
            author_name = (
                author.get("screen_name")
                or author.get("username")
                or author.get("handle")
                or ""
            )
            display_name = author.get("name") or author.get("display_name") or ""
        else:
            author_name = str(author)
            display_name = ""

        raw_tweet_id = tweet.get("id") or tweet.get("tweet_id") or tweet.get("rest_id")
        tweet_id = str(raw_tweet_id or "")
        return {
            "id": tweet_id,
            "text": tweet.get("text") or tweet.get("full_text") or "",
            "author": str(author_name).lstrip("@"),
            "display_name": display_name,
            "favorite_count": int(
                tweet.get("favorite_count") or tweet.get("likes") or 0
            ),
            "reply_count": int(tweet.get("reply_count") or tweet.get("replies") or 0),
            "retweet_count": int(
                tweet.get("retweet_count") or tweet.get("retweets") or 0
            ),
            "views": int(tweet.get("views") or tweet.get("view_count") or 0),
            "created_at": tweet.get("created_at") or tweet.get("createdAt") or "",
            "url": tweet.get("url")
            or GetXAPIClient._tweet_url(author_name, tweet_id),
            "is_reply": bool(tweet.get("is_reply") or tweet.get("reply_to")),
            "is_quote": bool(tweet.get("is_quote") or tweet.get("quote")),
        }

    @staticmethod
    def _tweet_url(author: Any, tweet_id: str) -> str:
        if not author or not tweet_id:
            return ""
        return f"https://x.com/{str(author).lstrip('@')}/status/{tweet_id}"

    @staticmethod
    def _get_path(data: dict, path: tuple[str, ...]) -> Any:
        current: Any = data
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current
