# =============================================================================
# Vercel — Test frontend (test.outception.com)
# =============================================================================

import {
  to = module.vercel.cloudflare_dns_record.this["test.outception.com"]
  id = "22bcd1b07ec25452aab472486bc8df94/7eee3c07157a8904f30fc3fd27b7ba27"
}

module "vercel" {
  source = "../modules/vercel"

  name     = "outception-test"
  git_repo = "outception/outception"

  domains = [
    {
      name = "test.outception.com"
      dns = {
        zone_id = "22bcd1b07ec25452aab472486bc8df94"
        content = "9b3437429d7388f1.vercel-dns-016.com"
        ttl     = 600
      }
    },
  ]

  config = {
    next_public_api_url                             = "https://test-api.outception.com"
    next_public_backoffice_url                      = "https://test-api.outception.com/backoffice"
    next_public_sentry_dsn                          = var.next_public_sentry_dsn
    next_public_posthog_token                       = var.next_public_posthog_token
    next_public_apple_domain_association            = var.next_public_apple_domain_association
    next_public_checkout_embed_script_src           = "https://cdn.jsdelivr.net/npm/@outception-com/checkout@0.1/dist/embed.global.js"
    s3_public_images_bucket_protocol                = "https"
    s3_public_images_bucket_hostname                = "outception-test-public-files.s3.amazonaws.com"
    s3_public_images_bucket_port                    = null
    s3_public_images_bucket_pathname                = "/product_media/**"
    s3_upload_origins                               = "https://outception-test-files.s3.amazonaws.com https://outception-test-files.s3.us-east-2.amazonaws.com https://outception-test-public-files.s3.amazonaws.com https://outception-test-public-files.s3.us-east-2.amazonaws.com"
    outception_checkout_embed_script_allowed_origins     = "https://outception.com,https://sandbox.outception.com,https://test.outception.com"
    outception_openapi_schema_url                        = "https://api.outception.com/openapi.json"
    enable_experimental_corepack                    = "1"
  }

  secrets = {
    pydantic_ai_gateway_api_key = var.pydantic_ai_gateway_api_key
    mintlify_assistant_api_key  = var.mintlify_assistant_api_key
    gram_api_key                = var.gram_api_key
    sentry_auth_token           = var.sentry_auth_token
    outception_preview_access_token  = var.outception_preview_access_token
  }

  # Environment-specific or target-varies-by-env.
  environment_variables = [
    { key = "NEXT_PUBLIC_FRONTEND_BASE_URL", value = "https://test.outception.com" },
    { key = "NEXT_PUBLIC_ENVIRONMENT", value = "test" },
    { key = "OUTCEPTION_AUTH_COOKIE_KEY", value = "outception_test_session" },
    { key = "NEXT_PUBLIC_PRODUCT_LINK_BASE_URL", value = "https://test.outception.com/api/checkout?price=" },
    { key = "OUTCEPTION_PREVIEW_BACKEND_HOST", value = "", target = ["preview"] },
    { key = "MCP_OAUTH2_CLIENT_ID", value = var.mcp_oauth2_client_id, target = ["production", "preview", "development"] },
    { key = "MCP_OAUTH2_CLIENT_SECRET", value = var.mcp_oauth2_client_secret, target = ["production", "preview", "development"] },
  ]
}
