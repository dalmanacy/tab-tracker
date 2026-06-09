from pathlib import Path
from typing import Union

import requests

from .base import Resource


class Communications(Resource):
    RESOURCE = "communications"

    def upload(self, file_path: Union[str, Path]) -> dict:
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{self._client.base_url}/communications/upload",
                headers={"Authorization": f"Bearer {self._client._get_token()}"},
                files={"file": f},
                timeout=60,
            )
        response.raise_for_status()
        return response.json()

    def download(self, communication_id: int, dest_path: Union[str, Path]) -> None:
        response = requests.get(
            f"{self._client.base_url}/communications/download",
            headers=self._client._headers(),
            params={"id": communication_id},
            timeout=60,
        )
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(response.content)
