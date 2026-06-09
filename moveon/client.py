"""
MoveOn REST API client.
Handles authentication (JWT token with caching) and all API operations.
"""

import time
from typing import Any, Dict, List, Optional

import requests

from .exceptions import MoveOnAPIError, MoveOnAuthError


class MoveOnClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._token: Optional[str] = None
        self._token_expiry: float = 0

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expiry:
            return self._token

        response = requests.post(
            f"{self.base_url}/auth/token",
            json={"username": self.username, "password": self.password},
            timeout=30,
        )
        if response.status_code == 401:
            raise MoveOnAuthError(401, "Invalid credentials")
        self._raise_for_status(response)
        data = response.json()
        self._token = data["data"]
        self._token_expiry = time.time() + 3540  # 59 minutes
        return self._token

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        if response.status_code >= 400:
            try:
                message = response.json().get("message", response.text)
            except Exception:
                message = response.text
            raise MoveOnAPIError(response.status_code, message)

    # ------------------------------------------------------------------
    # Core HTTP methods
    # ------------------------------------------------------------------

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        response = requests.get(
            f"{self.base_url}/{endpoint}",
            headers=self._headers(),
            params=params,
            timeout=30,
        )
        self._raise_for_status(response)
        return response.json()

    def _post(self, endpoint: str, payload: Dict) -> Dict:
        response = requests.post(
            f"{self.base_url}/{endpoint}",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        self._raise_for_status(response)
        return response.json()

    def _patch(self, endpoint: str, record_id: int, payload: Dict) -> Dict:
        response = requests.patch(
            f"{self.base_url}/{endpoint}/{record_id}",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        self._raise_for_status(response)
        return response.json()

    def _delete(self, endpoint: str, record_id: int) -> Dict:
        response = requests.delete(
            f"{self.base_url}/{endpoint}/{record_id}",
            headers=self._headers(),
            timeout=30,
        )
        self._raise_for_status(response)
        return response.json()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        resource: str,
        criteria: Optional[List[Dict]] = None,
        limit: Optional[int] = None,
        page: int = 1,
        sort: Optional[str] = None,
    ) -> List[Dict]:
        params: Dict[str, Any] = {"page": page, "limit": limit or 250}

        if sort:
            params["sort"] = sort

        for criterion in criteria or []:
            field = criterion["field"]
            operator = criterion.get("operator")
            value = criterion["value"]
            key = f"{field}[{operator}]" if operator else field
            params[key] = value

        data = self._get(resource, params=params)
        records = data.get("data", [])
        if isinstance(records, dict):
            records = [records]
        return records

    def get(self, resource: str, record_id: int) -> Dict:
        data = self._get(f"{resource}/{record_id}")
        return data.get("data", {})

    def create(self, resource: str, payload: Dict) -> Dict:
        return self._post(resource, payload)

    def update(self, resource: str, record_id: int, payload: Dict) -> Dict:
        return self._patch(resource, record_id, payload)

    def delete(self, resource: str, record_id: int) -> Dict:
        return self._delete(resource, record_id)
