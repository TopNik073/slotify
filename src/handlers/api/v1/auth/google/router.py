from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi.responses import RedirectResponse

from src.core.logger import get_logger
from src.database.repository import User
from src.exceptions import ClientError
from src.handlers.api.v1.auth.google.models import GoogleLoginResponse
from src.handlers.dependencies.auth import get_current_user
from src.services.auth.google import GoogleAuthService

logger = get_logger(__name__)

google_router = APIRouter(prefix='/google')


@google_router.get('/login', response_model=GoogleLoginResponse)
async def start_google_login(
    service: Annotated[GoogleAuthService, Depends()],
    email: Annotated[str | None, Query()] = None,
    next_path: Annotated[str | None, Query(alias='next', max_length=1024)] = None,
) -> GoogleLoginResponse:
    """
    The consent URL to open in the browser.

    Returned as JSON rather than as a redirect so that the frontend can call it with fetch and
    decide itself whether to open a new tab or navigate.
    """
    return GoogleLoginResponse(authorization_url=await service.start(login_hint=email, next_path=next_path))


@google_router.get('/callback', include_in_schema=False)
async def google_callback(
    service: Annotated[GoogleAuthService, Depends()],
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    """
    Where Google sends the browser back.

    Always answers with a redirect, including on failure: the user is sitting in a browser tab,
    so an error belongs on a page rather than in a JSON body.
    """
    next_path = await service.return_path(state)
    if error is not None:
        await logger.awarning('Google returned an error on callback', error=error)
        return RedirectResponse(service.callback_redirect_url(error=error, next_path=next_path))

    if not code or not state:
        return RedirectResponse(service.callback_redirect_url(error='missing_code', next_path=next_path))

    try:
        tokens = await service.complete(code, state)
    except ClientError as exc:
        await logger.awarning('Google sign-in failed', code=exc.code)
        return RedirectResponse(
            service.callback_redirect_url(error=exc.code or 'google_auth_failed', next_path=next_path)
        )

    return RedirectResponse(service.callback_redirect_url(tokens, next_path=next_path))


@google_router.delete('/', status_code=204)
async def disconnect_google(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[GoogleAuthService, Depends()],
) -> None:
    """Revoke our access to the user's calendar and forget the stored tokens."""
    await service.disconnect(user)
