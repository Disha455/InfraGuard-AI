"""
InfraGuard AI — Backend Configuration Constants

Single source of truth for server-level settings that are shared across
multiple backend modules.

Change SERVER_BASE_URL when:
  - Deploying to a different machine or network
  - Switching from LAN to a cloud host

Do NOT hardcode this value anywhere else in the backend.
"""

# ---------------------------------------------------------------------------
# Server base URL
#
# Used to build absolute HTTP URLs returned in API responses (e.g. the
# annotated_image field in PredictionResponse).
#
# Must be reachable by all clients (Flutter app, browser, etc.).
# Do NOT use 127.0.0.1 or localhost — those only resolve on the backend
# machine itself.  Use the LAN IP so Android devices on the same Wi-Fi
# network can fetch static assets.
# ---------------------------------------------------------------------------

SERVER_BASE_URL: str = "http://192.168.29.107:8000"
