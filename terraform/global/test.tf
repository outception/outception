# Bootstrap test variables

data "tfe_project" "test" {
  name         = "test"
  organization = "outception-com"
}

resource "tfe_variable_set" "test" {
  name              = "Test Settings"
  description       = "Variables specific to the test environment"
  organization      = "outception-com"
  parent_project_id = data.tfe_project.test.id
}

resource "tfe_variable" "google_client_id_test" {
  key             = "google_client_id"
  category        = "terraform"
  description     = "Google Client ID for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "google_client_secret_test" {
  key             = "google_client_secret"
  category        = "terraform"
  description     = "Google Client Secret for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "openai_api_key_test" {
  key             = "openai_api_key"
  category        = "terraform"
  description     = "OpenAI API Key for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "pydantic_ai_gateway_api_key_test" {
  key             = "pydantic_ai_gateway_api_key"
  category        = "terraform"
  description     = "Pydantic AI Gateway API Key for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "backend_current_jwk_kid_test" {
  key             = "backend_current_jwk_kid"
  category        = "terraform"
  description     = "Current JWK KID for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "backend_discord_bot_token_test" {
  key             = "backend_discord_bot_token"
  category        = "terraform"
  description     = "Discord Bot Token for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "backend_discord_client_id_test" {
  key             = "backend_discord_client_id"
  category        = "terraform"
  description     = "Discord Client ID for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "backend_discord_client_secret_test" {
  key             = "backend_discord_client_secret"
  category        = "terraform"
  description     = "Discord Client Secret for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "backend_resend_api_key_test" {
  key             = "backend_resend_api_key"
  category        = "terraform"
  description     = "Resend API Key for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "backend_resend_webhook_secret_test" {
  key             = "backend_resend_webhook_secret"
  category        = "terraform"
  description     = "Resend Webhook Secret for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "backend_logo_dev_publishable_key_test" {
  key             = "backend_logo_dev_publishable_key"
  category        = "terraform"
  description     = "Logo.dev Publishable Key for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "backend_secret_test" {
  key             = "backend_secret"
  category        = "terraform"
  description     = "Backend Secret for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "backend_sentry_dsn_test" {
  key             = "backend_sentry_dsn"
  category        = "terraform"
  description     = "Sentry DSN for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "backend_jwks_test" {
  key             = "backend_jwks"
  category        = "terraform"
  description     = "Backend JWKS content for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "aws_access_key_id_test" {
  key             = "aws_access_key_id"
  category        = "terraform"
  description     = "AWS Access Key ID for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "aws_secret_access_key_test" {
  key             = "aws_secret_access_key"
  category        = "terraform"
  description     = "AWS Secret Access Key for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "s3_files_download_salt_test" {
  key             = "s3_files_download_salt"
  category        = "terraform"
  description     = "S3 Files Download Salt for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "s3_files_download_secret_test" {
  key             = "s3_files_download_secret"
  category        = "terraform"
  description     = "S3 Files Download Secret for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "github_client_id_test" {
  key             = "github_client_id"
  category        = "terraform"
  description     = "GitHub Client ID for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "github_client_secret_test" {
  key             = "github_client_secret"
  category        = "terraform"
  description     = "GitHub Client Secret for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "github_repository_benefits_app_identifier_test" {
  key             = "github_repository_benefits_app_identifier"
  category        = "terraform"
  description     = "GitHub Repository Benefits App Identifier for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "github_repository_benefits_app_namespace_test" {
  key             = "github_repository_benefits_app_namespace"
  category        = "terraform"
  description     = "GitHub Repository Benefits App Namespace for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "github_repository_benefits_app_private_key_test" {
  key             = "github_repository_benefits_app_private_key"
  category        = "terraform"
  description     = "GitHub Repository Benefits App Private Key for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "github_repository_benefits_client_id_test" {
  key             = "github_repository_benefits_client_id"
  category        = "terraform"
  description     = "GitHub Repository Benefits Client ID for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "github_repository_benefits_client_secret_test" {
  key             = "github_repository_benefits_client_secret"
  category        = "terraform"
  description     = "GitHub Repository Benefits Client Secret for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}



resource "tfe_variable" "tinybird_api_token_test" {
  key             = "tinybird_api_token"
  category        = "terraform"
  description     = "Tinybird API Token for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "tinybird_workspace_test" {
  key             = "tinybird_workspace"
  category        = "terraform"
  description     = "Tinybird Workspace for test"
  variable_set_id = tfe_variable_set.test.id

  lifecycle {
    ignore_changes = [value]
  }
}

resource "tfe_variable" "tinybird_clickhouse_username_test" {
  key             = "tinybird_clickhouse_username"
  category        = "terraform"
  description     = "Tinybird ClickHouse Username for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "tinybird_clickhouse_token_test" {
  key             = "tinybird_clickhouse_token"
  category        = "terraform"
  description     = "Tinybird ClickHouse Token for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "tinybird_read_token_test" {
  key             = "tinybird_read_token"
  category        = "terraform"
  description     = "Tinybird Read Token for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "backend_discord_proxy_url_test" {
  key             = "backend_discord_proxy_url"
  category        = "terraform"
  description     = "Discord Proxy URL for test"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "outception_access_token_test" {
  key             = "outception_access_token"
  category        = "terraform"
  description     = "Outception API access token"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "outception_webhook_secret_test" {
  key             = "outception_webhook_secret"
  category        = "terraform"
  description     = "Outception webhook secret"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "outception_organization_id_test" {
  key             = "outception_organization_id"
  category        = "terraform"
  description     = "Outception organization ID"
  variable_set_id = tfe_variable_set.test.id

  lifecycle {
    ignore_changes = [value]
  }
}

resource "tfe_variable" "outception_free_product_id_test" {
  key             = "outception_free_product_id"
  category        = "terraform"
  description     = "Outception free-tier product ID"
  variable_set_id = tfe_variable_set.test.id

  lifecycle {
    ignore_changes = [value]
  }
}

resource "tfe_variable" "outception_scale_product_id_test" {
  key             = "outception_scale_product_id"
  category        = "terraform"
  description     = "Outception Scale-tier product ID for test"
  variable_set_id = tfe_variable_set.test.id
}

# Vercel frontend
resource "tfe_variable" "vercel_mintlify_assistant_api_key_test" {
  key             = "mintlify_assistant_api_key"
  category        = "terraform"
  description     = "Mintlify assistant API key for the Vercel test frontend"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "vercel_gram_api_key_test" {
  key             = "gram_api_key"
  category        = "terraform"
  description     = "Gram API key for the Vercel test frontend"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "vercel_sentry_auth_token_test" {
  key             = "sentry_auth_token"
  category        = "terraform"
  description     = "Sentry auth token for the Vercel test frontend build"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "vercel_outception_preview_access_token_test" {
  key             = "outception_preview_access_token"
  category        = "terraform"
  description     = "Outception preview access token for the Vercel test frontend"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "vercel_mcp_oauth2_client_id_test" {
  key             = "mcp_oauth2_client_id"
  category        = "terraform"
  description     = "MCP OAuth2 client ID for the Vercel test frontend"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "vercel_mcp_oauth2_client_secret_test" {
  key             = "mcp_oauth2_client_secret"
  category        = "terraform"
  description     = "MCP OAuth2 client secret for the Vercel test frontend"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "vercel_next_public_sentry_dsn_test" {
  key             = "next_public_sentry_dsn"
  category        = "terraform"
  description     = "Sentry DSN for the Vercel test frontend"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "vercel_next_public_posthog_token_test" {
  key             = "next_public_posthog_token"
  category        = "terraform"
  description     = "PostHog token for the Vercel test frontend"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

resource "tfe_variable" "vercel_next_public_apple_domain_association_test" {
  key             = "next_public_apple_domain_association"
  category        = "terraform"
  description     = "Apple Pay domain association for the Vercel test frontend"
  sensitive       = true
  variable_set_id = tfe_variable_set.test.id
}

