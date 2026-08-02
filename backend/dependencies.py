"""
InfraGuard AI — FastAPI Dependency Providers

Centralises all ``Depends()`` callables so routers import from one place
rather than duplicating guard logic across endpoints.

Dependency graph:

    Request
      └─ get_predictor_service()
             └─ reads app.state.predictor_service (set during lifespan)
                    └─ PredictorService
                             └─ Predictor  (YOLO model, loaded once)
"""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from backend.services.predictor_service import PredictorService

logger = logging.getLogger("infraguard.deps")


def get_predictor_service(request: Request) -> PredictorService:
    """
    FastAPI dependency that returns the application-scoped
    :class:`~backend.services.predictor_service.PredictorService`.

    The service is initialised during the lifespan startup and stored in
    ``app.state.predictor_service``.  If startup failed (model not found,
    ultralytics not installed, etc.) the attribute will be ``None`` and
    this dependency raises HTTP 503 so every inference endpoint gets a
    consistent, descriptive error without duplicating the guard.

    Args:
        request: Injected automatically by FastAPI.

    Returns:
        The ready ``PredictorService`` instance.

    Raises:
        :class:`fastapi.HTTPException` 503: If the model failed to load at
            startup.
    """
    service: PredictorService | None = getattr(
        request.app.state, "predictor_service", None
    )
    if service is None:
        logger.error(
            "get_predictor_service: service is None — model did not load at startup."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Inference service is not available.  "
                "The application started in degraded mode because "
                "weights/best.pt could not be loaded.  "
                "Check the server logs for details."
            ),
        )
    return service


# Annotated shorthand used in router endpoint signatures
PredictorServiceDep = Annotated[PredictorService, Depends(get_predictor_service)]
