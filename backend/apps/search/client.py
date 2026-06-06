import json
import logging
from urllib import error, parse, request

from django.conf import settings


logger = logging.getLogger(__name__)


class SearchClient:
    def __init__(self, url=None, master_key=None, timeout=5):
        self.url = (url if url is not None else getattr(settings, "MEILI_URL", "")).strip().rstrip("/")
        self.master_key = master_key if master_key is not None else getattr(settings, "MEILI_MASTER_KEY", "")
        self.timeout = timeout

    @property
    def enabled(self):
        return bool(self.url)

    def add_documents(self, index_name, documents):
        if not self.enabled:
            return None
        response = self._request(
            "POST",
            f"/indexes/{parse.quote(index_name)}/documents?primaryKey=id",
            list(documents),
        )
        return response if isinstance(response, dict) else None

    def search(self, index_name, query, **params):
        if not self.enabled:
            return {"hits": []}
        payload = {"q": query, **params}
        response = self._request("POST", f"/indexes/{parse.quote(index_name)}/search", payload)
        if not isinstance(response, dict) or not isinstance(response.get("hits"), list):
            return {"hits": []}
        return response

    def delete_all_documents(self, index_name):
        if not self.enabled:
            return None
        response = self._request("DELETE", f"/indexes/{parse.quote(index_name)}/documents")
        return response if isinstance(response, dict) else None

    def _request(self, method, path, payload=None):
        data = None
        headers = {"Content-Type": "application/json"}
        if self.master_key:
            headers["Authorization"] = f"Bearer {self.master_key}"
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        req = request.Request(
            f"{self.url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                body = response.read()
        except (error.HTTPError, error.URLError, TimeoutError):
            logger.warning("Meilisearch request failed", exc_info=True)
            return None

        if not body:
            return None
        try:
            return json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("Meilisearch returned an invalid JSON response", exc_info=True)
            return None


def get_search_client():
    return SearchClient()
