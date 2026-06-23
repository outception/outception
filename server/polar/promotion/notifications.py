"""Transactional emails to a promoter when their promotion goes live or
expires.

Sent through the kept ``email.send`` task with inline HTML — the React email
templates package isn't wired for promotion templates, and these are simple
one-off transactional messages.
"""

from html import escape

from polar.config import settings
from polar.models import Promotion
from polar.worker import enqueue_job


def notify(promotion: Promotion, kind: str) -> None:
    """Enqueue a go-live (``activated``) or end (``expired``) email to the
    promotion's author."""
    enqueue_job(
        "promotion.send_lifecycle_email",
        promotion_id=str(promotion.id),
        kind=kind,
    )


def build_email(promotion: Promotion, kind: str) -> tuple[str, str]:
    """Return ``(subject, html)`` for a promotion lifecycle email."""
    title = escape(promotion.title)
    category = escape(promotion.category)

    if kind == "activated":
        subject = f"Your promotion is live: {promotion.title}"
        heading = "Your promotion is live"
        body = (
            f"“{title}” is now the featured promotion in "
            f"<strong>{category}</strong> for the next "
            f"{promotion.duration_minutes} minutes."
        )
    elif kind == "queued":
        subject = f"Your promotion is queued: {promotion.title}"
        heading = "Your promotion is queued"
        body = (
            f"“{title}” is queued in <strong>{category}</strong> and will go "
            "live automatically as soon as the current featured slot frees up. "
            "We’ll email you when it does."
        )
    else:
        subject = f"Your promotion has ended: {promotion.title}"
        heading = "Your promotion has ended"
        body = (
            f"“{title}” has finished its featured run in "
            f"<strong>{category}</strong>. It drew {promotion.impressions} "
            f"impressions and {promotion.clicks} clicks."
        )

    return subject, _render(heading, body)


def _render(heading: str, body: str) -> str:
    dashboard_url = f"{settings.FRONTEND_BASE_URL}/dashboard"
    return (
        "<!doctype html>"
        '<html><body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;'
        'background:#0b0b0c;color:#e7e7e9;margin:0;padding:24px;">'
        '<div style="max-width:480px;margin:0 auto;background:#161618;'
        'border:1px solid #2a2a2e;border-radius:16px;padding:32px;">'
        '<div style="font-size:18px;font-weight:600;margin-bottom:16px;">'
        "Outception</div>"
        f'<h1 style="font-size:20px;margin:0 0 12px;">{heading}</h1>'
        f'<p style="font-size:15px;line-height:1.5;color:#b9b9bd;margin:0 0 24px;">'
        f"{body}</p>"
        f'<a href="{dashboard_url}" style="display:inline-block;background:#e7e7e9;'
        "color:#0b0b0c;text-decoration:none;padding:10px 18px;border-radius:10px;"
        'font-weight:600;font-size:14px;">View your promotions</a>'
        "</div></body></html>"
    )
