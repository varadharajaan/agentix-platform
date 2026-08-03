"""Keycloak client-credentials token acquisition.

North-south traffic through the ingress gateway requires a JWT from the
platform's Keycloak ``agents`` realm (the gateway enforces
``jwtAuthentication: Strict`` plus an ``organization`` claim). East-west
traffic inside the mesh needs no token. ``get_platform_token`` performs
the OAuth2 client-credentials grant for workloads that call in from
outside the cluster (CI pipelines, local development).
"""

from __future__ import annotations

import httpx

from synapse.config import SynapseConfig, get_config


async def get_platform_token(config: SynapseConfig | None = None) -> str:
    """Fetch a short-lived access token from the platform Keycloak realm.

    Requires ``SYNAPSE_KEYCLOAK_CLIENT_ID`` and
    ``SYNAPSE_KEYCLOAK_CLIENT_SECRET`` in the environment (or a config
    carrying them). Tokens live 300s by realm default — fetch per session,
    not per request.
    """
    cfg = config or get_config()
    if not (cfg.keycloak_client_id and cfg.keycloak_client_secret):
        raise ValueError(
            "Keycloak client credentials not configured — set "
            "SYNAPSE_KEYCLOAK_CLIENT_ID and SYNAPSE_KEYCLOAK_CLIENT_SECRET"
        )
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            cfg.keycloak_token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": cfg.keycloak_client_id,
                "client_secret": cfg.keycloak_client_secret,
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]
