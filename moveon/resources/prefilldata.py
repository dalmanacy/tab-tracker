from typing import Any, Dict, Optional

from .base import Resource


class Prefilldata(Resource):
    RESOURCE = "prefilldata"

    def list(self, criteria=None, limit=None, page=1, sort=None) -> Dict:
        return self._client._get("prefilldata")

    def by_collection(self, collection: str, identifier: Any) -> Dict:
        data = self._client._get(f"prefilldata/{collection}/{identifier}")
        return data.get("data", {})
