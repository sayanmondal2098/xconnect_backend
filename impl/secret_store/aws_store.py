from __future__ import annotations

import json
import boto3
from botocore.exceptions import ClientError

from impl.config import settings
from impl.secret_store.interfaces import SecretStore


class AWSSecretsManagerStore(SecretStore):
    def __init__(self):
        self.client = boto3.client("secretsmanager", region_name=settings.aws_region)

    def _name(self, user_id: int, name: str) -> str:
        # consistent naming convention
        return f"{settings.aws_secret_prefix}/{user_id}/{name}"

    def put(self, *, user_id: int, name: str, value: str) -> str:
        secret_name = self._name(user_id, name)
        payload = json.dumps({"value": value})
        try:
            self.client.create_secret(Name=secret_name, SecretString=payload)
        except ClientError as e:
            # if exists, update
            if e.response.get("Error", {}).get("Code") in ("ResourceExistsException",):
                self.client.put_secret_value(SecretId=secret_name, SecretString=payload)
            else:
                raise
        return f"aws:{secret_name}"

    def get(self, *, user_id: int, ref: str) -> str:
        if not ref.startswith("aws:"):
            raise ValueError("Invalid aws secret ref")
        secret_name = ref.split(":", 1)[1]
        resp = self.client.get_secret_value(SecretId=secret_name)
        s = resp.get("SecretString") or "{}"
        obj = json.loads(s)
        return str(obj.get("value", ""))
