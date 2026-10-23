"""
InfraGuard AI — Backend Configuration Constants

Single source of truth for server-level settings that are shared across
multiple backend modules.

Change SERVER_BASE_URL when:
  - Deploying to a different machine or network
  - Switching from LAN to a cloud host

Do NOT hardcode this value anywhere else in the backend.
"""

import os

# ---------------------------------------------------------------------------
# Server base URL
#
# Used to build absolute HTTP URLs returned in API responses (e.g. the
# annotated_image field in PredictionResponse).
#
# Can be overridden via INFRAGUARD_SERVER_URL environment variable.
# ---------------------------------------------------------------------------

_DEFAULT_SERVER_URL = "http://10.196.252.38:8000"
SERVER_BASE_URL: str = os.getenv("INFRAGUARD_SERVER_URL", _DEFAULT_SERVER_URL)
