from fastapi import Depends, Request, Response

from outception.kit.http import get_ip_address
from outception.openapi import APITag
from outception.postgres import AsyncSession, get_db_session
from outception.routing import APIRouter

from . import service
from .schemas import FeedbackCreate

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", status_code=204, tags=[APITag.public])
async def submit_feedback(
    body: FeedbackCreate,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """One message from the "Tell us" sheet. No account; the sender's
    address is kept only as a keyed hash for abuse review."""
    await service.submit(session, body, ip=get_ip_address(request))
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
