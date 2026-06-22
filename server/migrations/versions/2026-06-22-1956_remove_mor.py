"""remove mor

Revision ID: b7d59566274a
Revises: 88b8a2396a0e
Create Date: 2026-06-22 19:56:00.000000

Drops the entire Merchant-of-Record schema. Tables are dropped with CASCADE so
their triggers, foreign keys, and owned sequences go with them; the few
standalone plpgsql functions/sequences left behind are dropped explicitly. This
migration is irreversible — the MoR feature set has been removed from the
codebase, so there are no models to recreate on downgrade.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b7d59566274a"
down_revision = "88b8a2396a0e"
branch_labels = None
depends_on = None


MOR_TABLES = [
    "account_credits", "accounts", "benefit_grants", "benefits", "billing_entry",
    "campaigns", "checkout_link_products", "checkout_links", "checkout_products",
    "checkouts", "customer_email_verifications", "customer_meters", "customers",
    "customer_seats", "customer_session_codes", "customer_sessions", "custom_fields",
    "discount_products", "discount_redemptions", "discounts", "disputes",
    "downloadables", "events", "event_types", "external_events", "files",
    "issue_rewards", "license_key_activations", "license_keys", "members",
    "member_sessions", "meter_events", "meters", "metric_dashboards", "order_items",
    "orders", "organization_agent_reviews", "organization_review_feedback",
    "organization_reviews", "payment_methods", "payments", "payout_accounts",
    "payout_attempts", "payouts", "pledges", "pledge_transactions",
    "processor_transactions", "product_benefits", "product_custom_fields",
    "product_medias", "product_prices", "products", "refunds", "subscription_meters",
    "subscription_product_prices", "subscriptions", "subscription_updates",
    "support_case_attachments", "support_case_messages", "support_case_participants",
    "support_cases", "transactions", "trial_redemptions", "wallets",
    "wallet_transactions", "webhook_deliveries", "webhook_endpoints", "webhook_events",
]

MOR_FUNCTIONS = [
    "generate_customer_short_id(timestamp with time zone)",
    "benefits_search_vector_update()",
    "products_search_vector_update()",
    "customers_search_vector_update()",
    "discount_redemptions_count_increment()",
    "discount_redemptions_count_decrement()",
    "orders_search_vector_update()",
    "payout_status_update()",
]

MOR_SEQUENCES = [
    "customer_short_id_seq",
]


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")

    # Drop the MoR foreign-key columns from the kept tables first.
    op.drop_column("organizations", "account_id")
    op.drop_column("organizations", "payout_account_id")
    op.drop_column("users", "account_id")
    op.drop_column("users", "stripe_customer_id")

    # Drop every MoR table; CASCADE removes dependent triggers, FKs and owned
    # sequences regardless of inter-table ordering.
    for table in MOR_TABLES:
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')

    # Standalone functions/sequences that the tables didn't own.
    for function in MOR_FUNCTIONS:
        op.execute(f"DROP FUNCTION IF EXISTS {function} CASCADE")
    for sequence in MOR_SEQUENCES:
        op.execute(f'DROP SEQUENCE IF EXISTS "{sequence}" CASCADE')


def downgrade() -> None:
    raise NotImplementedError(
        "remove_mor is irreversible: the Merchant-of-Record models were removed "
        "from the codebase."
    )
