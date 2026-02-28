"""Health check router for container orchestration."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Return application health status.

    Used by container orchestrators (Kubernetes, ECS, Docker)
    to determine if the application is ready to receive traffic.
    """
    return {
        "status": "healthy",
        "checks": {
            "app": "ok",
        },
    }
