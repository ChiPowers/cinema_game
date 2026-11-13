import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from ..config import INTERNAL_SECRET
from ..database import is_beta_user

router = APIRouter(prefix="/auth", tags=["auth"])


class BetaCheckRequest(BaseModel):
    email: str


def _require_internal(x_internal_secret: str = Header(..., alias="x-internal-secret")):
    if not INTERNAL_SECRET:
        raise HTTPException(status_code=500, detail="Server misconfigured")
    if not hmac.compare_digest(x_internal_secret, INTERNAL_SECRET):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/check-beta", status_code=200)
async def check_beta(
    body: BetaCheckRequest,
    _: None = Depends(_require_internal),
):
    if not await run_in_threadpool(is_beta_user, body.email):
        raise HTTPException(status_code=403, detail="Not in beta")
    return {"allowed": True}
