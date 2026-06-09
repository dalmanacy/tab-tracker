"""
Load MoveOn credentials from environment variables.

Set these before running:
    export MOVEON_BASE_URL="https://myinstance.restapi.moveonfr.com/api/v1/"
    export MOVEON_USERNAME="user@example.com"
    export MOVEON_PASSWORD="secret"
"""

import os

from moveon import MoveOn


def get_client() -> MoveOn:
    base_url = os.environ["MOVEON_BASE_URL"]
    username = os.environ["MOVEON_USERNAME"]
    password = os.environ["MOVEON_PASSWORD"]
    return MoveOn(base_url, username, password)
