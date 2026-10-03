import typing

from fastapi import Depends, Request, Response
from fastapi.responses import RedirectResponse
from reauth.authentication_session import (
    AuthenticationSession,
    FactorsRemainingException,
    IdentityNotAttachedException,
)
from reauth.factors.backup_codes import (
    AlreadyUsedBackupCodeException,
    InvalidBackupCodeException,
)
from reauth.factors.email_otp import ExpiredOTPException, InvalidOTPException
from reauth.factors.totp import (
    AlreadyEnabledTOTPException,
    AlreadyEnrolledTOTPException,
    InvalidTOTPCodeException,
    NotEnrolledTOTPException,
)

from outception.auth.dependencies import (
    WebUserOrAnonymous,
    WebUserRead,
    WebUserWriteFresh,
)
from outception.auth.exceptions import (
    OutceptionAuthError,
    OutceptionAuthRedirectionError,
    SessionNotFreshError,
    UnavailableFactorError,
)
from outception.auth.models import is_user
from outception.auth.oauth2.google import get_google_factor
from outception.auth.oauth2.microsoft import get_microsoft_factor
from outception.config import settings
from outception.exceptions import NotPermitted, ResourceNotFound
from outception.kit.http import get_ip_address, get_safe_return_url
from outception.openapi import APITag
from outception.postgres import AsyncSession, get_db_session
from outception.redis import Redis, get_redis
from outception.routing import APIRouter
from outception.user.repository import UserRepository
from outception.user.service import user as user_service

from . import lockout
from .authentication_session import (
    AuthenticationSessionService,
    InvalidAuthenticationSession,
    get_authentication_session,
    get_authentication_session_service,
    get_optional_authentication_session,
)
from .factors import (
    BackupCodesFactor,
    EmailOTPFactor,
    TOTPFactor,
    get_backup_codes_factor,
    get_email_otp_factor,
    get_totp_factor,
)
from .oauth2.apple import get_apple_factor
from .oauth2.router import get_oauth_link_router, get_oauth_login_router
from .schemas import AuthenticationSession as AuthenticationSessionSchema
from .schemas import (
    BackupCodesEnrollment,
    BackupCodesStatus,
    BackupCodesVerify,
    EmailOTPRequest,
    EmailOTPVerify,
    GlobalAuthenticationSessionStart,
    LoginMethod,
    TOTPEnable,
    TOTPEnrollment,
    TOTPStatus,
)
from .service import auth as auth_service
from .turnstile import verify_turnstile

TOTP_ISSUER = (
    "Outception"
    if settings.is_production()
    else f"Outception {settings.ENV.value.capitalize()}"
)

router = APIRouter(prefix="/auth", tags=["auth", APITag.private])
router.include_router(
    get_oauth_login_router(get_apple_factor, "apple", callback_method="POST")
)
router.include_router(get_oauth_login_router(get_google_factor, "google"))
router.include_router(get_oauth_link_router(get_google_factor, "google"))
router.include_router(get_oauth_login_router(get_microsoft_factor, "microsoft"))
router.include_router(get_oauth_link_router(get_microsoft_factor, "microsoft"))


@router.get("/logout")
async def logout(
    request: Request, session: AsyncSession = Depends(get_db_session)
) -> RedirectResponse:
    user_session = await auth_service.authenticate(session, request)
    return await auth_service.get_logout_response(session, request, user_session)


@router.post("/start", status_code=201)
async def start(
    authentication_session_start: GlobalAuthenticationSessionStart,
    request: Request,
    response: Response,
    authentication_session_service: AuthenticationSessionService = Depends(
        get_authentication_session_service
    ),
) -> AuthenticationSessionSchema:
    token, authentication_session = await authentication_session_service.start(
        return_to=authentication_session_start.return_to,
    )
    await authentication_session_service.set_cookie(
        request, response, token, authentication_session.expires_at
    )
    return await authentication_session_service.to_schema(authentication_session)


@router.get(
    "/status",
    responses={
        401: {
            "description": "No active authentication session",
            "model": InvalidAuthenticationSession.schema(),
        }
    },
)
async def status(
    authentication_session: AuthenticationSession = Depends(get_authentication_session),
    authentication_session_service: AuthenticationSessionService = Depends(
        get_authentication_session_service
    ),
) -> AuthenticationSessionSchema:
    return await authentication_session_service.to_schema(authentication_session)


@router.get("/complete", include_in_schema=False)
async def complete(
    request: Request,
    auth_subject: WebUserOrAnonymous,
    authentication_session: AuthenticationSession | None = Depends(
        get_optional_authentication_session
    ),
    authentication_session_service: AuthenticationSessionService = Depends(
        get_authentication_session_service
    ),
    session: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    if authentication_session is None:
        if is_user(auth_subject):
            return RedirectResponse(get_safe_return_url(None), 303)
        raise InvalidAuthenticationSession()

    try:
        identity_id, _ = await authentication_session_service.complete(
            authentication_session
        )
    except (IdentityNotAttachedException, FactorsRemainingException) as e:
        raise OutceptionAuthRedirectionError(
            "Authentication session cannot be completed"
        ) from e

    user_repository = UserRepository.from_session(session)
    user = await user_repository.get_by_id(identity_id)
    if user is None:
        raise OutceptionAuthRedirectionError(
            "User not found for authenticated identity"
        )

    context = authentication_session.context or {}
    factor = typing.cast(LoginMethod, authentication_session.used_factors[0])

    response = await auth_service.get_login_response(
        session,
        request,
        user,
        return_to=context.get("return_to"),
        factor=factor,
    )
    await authentication_session_service.set_cookie(request, response, "", 0)
    return response


@router.post(
    "/email-otp/request",
    status_code=202,
    responses={
        403: {
            "description": "Turnstile verification failed",
            "model": NotPermitted.schema(),
        },
    },
)
async def email_otp_request(
    email_otp_request: EmailOTPRequest,
    request: Request,
    authentication_session: AuthenticationSession = Depends(get_authentication_session),
    authentication_session_service: AuthenticationSessionService = Depends(
        get_authentication_session_service
    ),
    email_otp_factor: EmailOTPFactor = Depends(get_email_otp_factor),
) -> None:
    await verify_turnstile(email_otp_request.turnstile_token, get_ip_address(request))

    factors = await authentication_session_service.get_available_factors(
        authentication_session
    )
    if email_otp_factor not in factors:
        raise UnavailableFactorError(email_otp_factor.identifier)

    await email_otp_factor.request(email_otp_request, authentication_session)


@router.post(
    "/email-otp/verify",
    responses={
        403: {"description": "Invalid or expired OTP", "model": NotPermitted.schema()}
    },
)
async def email_otp_verify(
    email_otp_verify: EmailOTPVerify,
    authentication_session: AuthenticationSession = Depends(get_authentication_session),
    authentication_session_service: AuthenticationSessionService = Depends(
        get_authentication_session_service
    ),
    email_otp_factor: EmailOTPFactor = Depends(get_email_otp_factor),
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> AuthenticationSessionSchema:
    factors = await authentication_session_service.get_available_factors(
        authentication_session
    )
    if email_otp_factor not in factors:
        raise UnavailableFactorError(email_otp_factor.identifier)
    if await lockout.is_locked(redis, str(authentication_session.id)):
        raise OutceptionAuthError("Invalid or expired OTP", 403)

    try:
        identity_id, email = await email_otp_factor.consume(
            email_otp_verify.code, authentication_session.id
        )
    except (InvalidOTPException, ExpiredOTPException) as e:
        await lockout.note_failure(redis, str(authentication_session.id))
        raise OutceptionAuthError("Invalid or expired OTP", 403) from e
    await lockout.clear(redis, str(authentication_session.id))

    # New user
    if identity_id is None:
        user, _ = await user_service.get_by_email_or_create(session, email)
        user.email_verified = True
        session.add(user)
        identity_id = user.id

    authentication_session = await authentication_session_service.advance(
        authentication_session, identity_id, email_otp_factor
    )
    return await authentication_session_service.to_schema(authentication_session)


@router.get("/totp", responses={404: {"description": "TOTP factor not enrolled"}})
async def totp_status(
    auth_subject: WebUserRead,
    totp_factor: TOTPFactor = Depends(get_totp_factor),
) -> TOTPStatus:
    user = auth_subject.subject
    enrollment = await totp_factor.get_enrollment(user.id)
    if enrollment is None:
        raise ResourceNotFound()
    return TOTPStatus(enabled=enrollment.enabled)


@router.post(
    "/totp",
    status_code=201,
    responses={403: {"model": SessionNotFreshError.schema()}},
)
async def totp_enroll(
    auth_subject: WebUserWriteFresh,
    totp_factor: TOTPFactor = Depends(get_totp_factor),
) -> TOTPEnrollment:
    user = auth_subject.subject

    try:
        enrollment = await totp_factor.enroll(user.id)
    except AlreadyEnrolledTOTPException as e:
        raise OutceptionAuthError("TOTP factor already enrolled", 409) from e

    return TOTPEnrollment(
        secret=enrollment.secret,
        algorithm=enrollment.algorithm,
        digits=enrollment.code_length,
        period=enrollment.time_step,
        provisioning_uri=enrollment.get_provisioning_uri(user.email, TOTP_ISSUER),
    )


@router.post(
    "/totp/enable",
    status_code=202,
    responses={
        403: {
            "description": (
                "Session is not fresh, TOTP factor not enrolled, or invalid TOTP code."
            ),
            "model": SessionNotFreshError.schema() | OutceptionAuthError.schema(),
        }
    },
)
async def totp_enable(
    enable: TOTPEnable,
    auth_subject: WebUserWriteFresh,
    totp_factor: TOTPFactor = Depends(get_totp_factor),
) -> None:
    user = auth_subject.subject
    try:
        await totp_factor.enable(user.id, enable.code)
    except NotEnrolledTOTPException as e:
        raise OutceptionAuthError("TOTP factor not enrolled", 403) from e
    except AlreadyEnabledTOTPException as e:
        raise OutceptionAuthError("TOTP factor already enabled", 409) from e
    except InvalidTOTPCodeException as e:
        raise OutceptionAuthError("Invalid TOTP code", 403) from e


@router.delete(
    "/totp",
    status_code=204,
    responses={403: {"model": SessionNotFreshError.schema()}},
)
async def totp_delete(
    auth_subject: WebUserWriteFresh,
    totp_factor: TOTPFactor = Depends(get_totp_factor),
    backup_codes_factor: BackupCodesFactor = Depends(get_backup_codes_factor),
) -> None:
    user = auth_subject.subject
    enrollment = await totp_factor.get_by_identity_id(user.id)
    if enrollment is None:
        raise ResourceNotFound()
    await totp_factor.delete(enrollment)

    # Disable backup codes as well since they are meant to be used as a backup for TOTP
    backup_codes_enrollment = await backup_codes_factor.get_enrollment(user.id)
    if backup_codes_enrollment is not None:
        await backup_codes_factor.delete(backup_codes_enrollment)


@router.post("/totp/verify")
async def totp_verify(
    enable: TOTPEnable,
    authentication_session: AuthenticationSession = Depends(get_authentication_session),
    authentication_session_service: AuthenticationSessionService = Depends(
        get_authentication_session_service
    ),
    totp_factor: TOTPFactor = Depends(get_totp_factor),
    redis: Redis = Depends(get_redis),
) -> AuthenticationSessionSchema:
    factors = await authentication_session_service.get_available_factors(
        authentication_session
    )
    if totp_factor not in factors:
        raise UnavailableFactorError(totp_factor.identifier)
    if await lockout.is_locked(redis, str(authentication_session.id)):
        raise OutceptionAuthError("Invalid TOTP code", 403)

    try:
        await totp_factor.verify(authentication_session.identity_id, enable.code)
    except NotEnrolledTOTPException as e:
        raise OutceptionAuthError("TOTP factor not enrolled", 403) from e
    except InvalidTOTPCodeException as e:
        await lockout.note_failure(redis, str(authentication_session.id))
        raise OutceptionAuthError("Invalid TOTP code", 403) from e
    await lockout.clear(redis, str(authentication_session.id))

    authentication_session = await authentication_session_service.advance(
        authentication_session, authentication_session.identity_id, totp_factor
    )
    return await authentication_session_service.to_schema(authentication_session)


@router.get(
    "/backup-codes",
    responses={404: {"description": "Backup codes factor not enrolled"}},
)
async def backup_codes_status(
    auth_subject: WebUserRead,
    backup_codes_factor: BackupCodesFactor = Depends(get_backup_codes_factor),
) -> BackupCodesStatus:
    user = auth_subject.subject
    enrollment = await backup_codes_factor.get_enrollment(user.id)
    if enrollment is None:
        raise ResourceNotFound()
    return BackupCodesStatus(
        codes=len(enrollment.codes_hashes), used_codes=len(enrollment.used_codes_hashes)
    )


@router.post(
    "/backup-codes",
    status_code=201,
    responses={403: {"model": SessionNotFreshError.schema()}},
)
async def backup_codes_enroll(
    auth_subject: WebUserWriteFresh,
    backup_codes_factor: BackupCodesFactor = Depends(get_backup_codes_factor),
) -> BackupCodesEnrollment:
    user = auth_subject.subject
    codes, _ = await backup_codes_factor.enroll(user.id)
    return BackupCodesEnrollment(codes=codes)


@router.post("/backup-codes/verify")
async def backup_codes_verify(
    verify: BackupCodesVerify,
    authentication_session: AuthenticationSession = Depends(get_authentication_session),
    authentication_session_service: AuthenticationSessionService = Depends(
        get_authentication_session_service
    ),
    backup_codes_factor: BackupCodesFactor = Depends(get_backup_codes_factor),
    redis: Redis = Depends(get_redis),
) -> AuthenticationSessionSchema:
    factors = await authentication_session_service.get_available_factors(
        authentication_session
    )
    if backup_codes_factor not in factors:
        raise UnavailableFactorError(backup_codes_factor.identifier)
    if await lockout.is_locked(redis, str(authentication_session.id)):
        raise OutceptionAuthError("Invalid or expired backup code", 400)

    try:
        await backup_codes_factor.verify(
            authentication_session.identity_id, verify.code
        )
    except (InvalidBackupCodeException, AlreadyUsedBackupCodeException) as e:
        await lockout.note_failure(redis, str(authentication_session.id))
        raise OutceptionAuthError("Invalid or expired backup code", 400) from e
    await lockout.clear(redis, str(authentication_session.id))

    authentication_session = await authentication_session_service.advance(
        authentication_session, authentication_session.identity_id, backup_codes_factor
    )
    return await authentication_session_service.to_schema(authentication_session)
