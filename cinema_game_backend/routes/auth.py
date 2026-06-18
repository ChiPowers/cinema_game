import logging
from fastapi import APIRouter, HTTPException, Header, status
from ..config import INTERNAL_SECRET

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/verify")
def verify_internal(
    x_internal_secret: str = Header(default="", alias="X-Internal-Secret"),
):
    """Verify the caller holds the shared INTERNAL_SECRET.

    Called by the Next.js backend to confirm the game API is reachable and
    that the secret is correctly provisioned on both sides.
    Returns 200 on success, 401 on mismatch.
    """
    if not x_internal_secret or x_internal_secret != INTERNAL_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal secret",
        )
    return {"authenticated": True}
