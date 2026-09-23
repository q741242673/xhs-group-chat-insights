# encoding: utf-8
"""Read-only APIs used by the Xiaohongshu web chat client."""

from loguru import logger

from apis.xhs_live import XHSLiveAPI
from xhs_utils.xhs_pc import XHSPcAuth


class XHS_IM_Apis:
    """Small wrapper around the web IM history endpoint.

    The endpoint is not part of the public Xiaohongshu API. It may change without
    notice and should only be used with an account that can already view the
    requested conversation.
    """

    def __init__(self, auth=None, auth_factory=None, live_api_factory=None):
        self.auth = auth
        self._auth_factory = auth_factory or XHSPcAuth.from_cookie
        self._live_api_factory = live_api_factory or XHSLiveAPI
        self._live_api = self._live_api_factory(auth) if auth is not None else None
        self._cookies_str = None

    def _client(self, cookies_str):
        if self._live_api is None:
            self.auth = self._auth_factory(cookies_str)
            self._live_api = self._live_api_factory(self.auth)
            self._cookies_str = cookies_str
        elif self._cookies_str is not None and cookies_str != self._cookies_str:
            raise ValueError("cannot change cookies during an active group export")
        return self._live_api

    def close(self):
        if self.auth is not None and hasattr(self.auth, "close"):
            self.auth.close()

    def get_group_history_page(
        self,
        group_id: str,
        last_id: str,
        cookies_str: str,
        start_id: str = "0",
        limit: int = 30,
        proxies: dict = None,
    ):
        """Fetch one page of group messages without modifying the conversation."""
        response_json = None
        try:
            if not 1 <= int(limit) <= 30:
                raise ValueError("limit must be between 1 and 30")

            api = "/api/im/web/red/group/messages/history"
            params = {
                "group_id": str(group_id),
                "last_id": str(last_id),
                "start_id": str(start_id),
                "limit": str(limit),
            }
            if proxies:
                logger.warning(
                    "per-call proxies are ignored; pass proxies when creating XHSPcAuth"
                )
            response_json = self._client(cookies_str).get_group_message_history(params)
            success = bool(response_json.get("success"))
            message = response_json.get("msg", "")
            nested_result = (response_json.get("data") or {}).get("result") or {}
            if nested_result and not nested_result.get("success", True):
                success = False
                message = nested_result.get("message") or message
        except Exception as error:
            success = False
            message = str(error)
            logger.exception("XHS group history request failed")
        return success, message, response_json
