from fastapi import APIRouter

from outception.account.endpoints import router as accounts_router
from outception.auth.endpoints import router as auth_router
from outception.benefit.endpoints import router as benefits_router
from outception.benefit.grant.endpoints import router as benefit_grants_router
from outception.benefit.strategies.slack_shared_channel.endpoints import (
    router as slack_shared_channel_benefit_router,
)
from outception.checkout.endpoints import router as checkout_router
from outception.checkout_link.endpoints import router as checkout_link_router
from outception.cli.endpoints import router as cli_router
from outception.compass.endpoints import router as compass_router
from outception.custom_field.endpoints import router as custom_field_router
from outception.customer.endpoints import router as customer_router
from outception.customer_meter.endpoints import router as customer_meter_router
from outception.customer_portal.endpoints import router as customer_portal_router
from outception.customer_seat.endpoints import router as customer_seat_router
from outception.customer_session.endpoints import router as customer_session_router
from outception.discount.endpoints import router as discount_router
from outception.dispute.endpoints import router as dispute_router
from outception.email_update.endpoints import router as email_update_router
from outception.event.endpoints import router as event_router
from outception.event_type.endpoints import router as event_type_router
from outception.eventstream.endpoints import router as stream_router
from outception.feedback.endpoints import router as feedback_router
from outception.file.endpoints import router as files_router
from outception.integrations.chargeback_stop.endpoints import (
    router as chargeback_stop_router,
)
from outception.integrations.discord.endpoints import router as discord_router
from outception.integrations.github.endpoints import router as github_router
from outception.integrations.github_repository_benefit.endpoints import (
    router as github_repository_benefit_router,
)
from outception.integrations.plain.endpoints import router as plain_router
from outception.integrations.outception.endpoints import router as outception_self_router
from outception.integrations.resend.endpoints import router as resend_router
from outception.integrations.slack.endpoints import router as slack_router
from outception.integrations.stripe.endpoints import router as stripe_router
from outception.license_key.endpoints import router as license_key_router
from outception.member.endpoints import customer_members_router
from outception.member.endpoints import router as member_router
from outception.merchant_migration.endpoints import router as merchant_migration_router
from outception.meter.endpoints import router as meter_router
from outception.metrics.endpoints import router as metrics_router
from outception.notifications.endpoints import router as notifications_router
from outception.oauth2.endpoints.oauth2 import router as oauth2_router
from outception.order.endpoints import router as order_router
from outception.organization.endpoints import router as organization_router
from outception.organization_access_token.endpoints import (
    router as organization_access_token_router,
)
from outception.payment.endpoints import router as payment_router
from outception.payout.endpoints import router as payout_router
from outception.payout_account.endpoints import router as payout_account_router
from outception.personal_access_token.endpoints import router as pat_router
from outception.product.endpoints import router as product_router
from outception.refund.endpoints import router as refund_router
from outception.search.endpoints import router as search_router
from outception.sso.endpoints import domain_router as sso_domain_router
from outception.sso.endpoints import router as sso_router
from outception.subscription.endpoints import router as subscription_router
from outception.support_case.endpoints import router as support_case_router
from outception.tax.endpoints import router as tax_router
from outception.transaction.endpoints import router as transaction_router
from outception.user.endpoints import router as user_router
from outception.wallet.endpoints import router as wallet_router
from outception.webhook.endpoints import router as webhook_router

router = APIRouter(prefix="/v1")

# /users
router.include_router(user_router)
# /integrations/github
router.include_router(github_router)
# /integrations/github_repository_benefit
router.include_router(github_repository_benefit_router)
# /integrations/stripe
router.include_router(stripe_router)
# /integrations/discord
router.include_router(discord_router)
# /integrations/slack
router.include_router(slack_router)
# /notifications
router.include_router(notifications_router)
# /personal_access_tokens
router.include_router(pat_router)
# /accounts
router.include_router(accounts_router)
# /stream
router.include_router(stream_router)
# /organizations
router.include_router(organization_router)
# /organizations/{id}/sso-connections
router.include_router(sso_router)
# /organizations/{id}/sso-domains
router.include_router(sso_domain_router)
# /subscriptions
router.include_router(subscription_router)
# /transactions
router.include_router(transaction_router)
# /taxes
router.include_router(tax_router)
# /auth
router.include_router(auth_router)
# /oauth2
router.include_router(oauth2_router)
# /benefits
router.include_router(benefits_router)
# /benefits/slack
router.include_router(slack_shared_channel_benefit_router)
# /benefit-grants
router.include_router(benefit_grants_router)
# /webhooks
router.include_router(webhook_router)
# /products
router.include_router(product_router)
# /orders
router.include_router(order_router)
# /refunds
router.include_router(refund_router)
# /disputes
router.include_router(dispute_router)
# /support-cases
router.include_router(support_case_router)
# /checkouts
router.include_router(checkout_router)
# /cli
router.include_router(cli_router)
# /files
router.include_router(files_router)
# /metrics
router.include_router(metrics_router)
# /compass
router.include_router(compass_router)
# /license-keys
router.include_router(license_key_router)
# /checkout-links
router.include_router(checkout_link_router)
# /custom-fields
router.include_router(custom_field_router)
# /discounts
router.include_router(discount_router)
# /customers
router.include_router(customer_router)
# /members
router.include_router(member_router)
# /customers/{id}/members (nested member CRUD; defined in the member module)
router.include_router(customer_members_router)
# /customer-portal
router.include_router(customer_portal_router)
# /seats
router.include_router(customer_seat_router)
# /merchant-migrations
router.include_router(merchant_migration_router)
# /update-email
router.include_router(email_update_router)
# /customer-sessions
router.include_router(customer_session_router)
# /integrations/plain
router.include_router(plain_router)
# /events
router.include_router(event_router)
# /event-types
router.include_router(event_type_router)
# /meters
router.include_router(meter_router)
# /organization-access-tokens
router.include_router(organization_access_token_router)
# /customer-meters
router.include_router(customer_meter_router)
# /payments
router.include_router(payment_router)
# /payouts
router.include_router(payout_router)
# /search
router.include_router(search_router)
# /wallets
router.include_router(wallet_router)
# /integrations/resend
router.include_router(resend_router)
# /integrations/chargeback-stop
router.include_router(chargeback_stop_router)
# /integrations/outception
router.include_router(outception_self_router)
# /payout-accounts
router.include_router(payout_account_router)
# /feedbacks
router.include_router(feedback_router)
