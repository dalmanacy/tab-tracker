from typing import Any, Dict, Generator, List, Optional


class Resource:
    RESOURCE = ""

    def __init__(self, client):
        self._client = client

    def list(
        self,
        criteria: Optional[List[Dict]] = None,
        limit: Optional[int] = None,
        page: int = 1,
        sort: Optional[str] = None,
    ) -> List[Dict]:
        return self._client.search(self.RESOURCE, criteria=criteria, limit=limit, page=page, sort=sort)

    def get(self, record_id: int) -> Dict:
        return self._client.get(self.RESOURCE, record_id)

    def create(self, payload: Dict) -> Dict:
        return self._client.create(self.RESOURCE, payload)

    def update(self, record_id: int, payload: Dict) -> Dict:
        return self._client.update(self.RESOURCE, record_id, payload)

    def iter_all(
        self,
        criteria: Optional[List[Dict]] = None,
        sort: Optional[str] = None,
    ) -> Generator[Dict, None, None]:
        page = 1
        while True:
            batch = self.list(criteria=criteria, page=page, sort=sort)
            if not batch:
                break
            yield from batch
            page += 1


class ExternalIdMixin:
    def by_external_id(self, external_id: Any) -> Dict:
        data = self._client._get(f"{self.RESOURCE}/by-external-id/{external_id}")
        return data.get("data", {})
