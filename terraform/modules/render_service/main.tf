# Outception Render service setup
#
# Sets up a service, and the specified workers.
# Includes the environment groups

locals {
  environment = var.backend_config.environment == null ? var.environment : var.backend_config.environment
}

resource "render_env_group" "google" {
  environment_id = var.render_environment_id
  name           = "google-${var.environment}"
  env_vars = {
    OUTCEPTION_GOOGLE_CLIENT_ID     = { value = var.google_secrets.client_id }
    OUTCEPTION_GOOGLE_CLIENT_SECRET = { value = var.google_secrets.client_secret }
  }
}

resource "render_env_group" "openai" {
  environment_id = var.render_environment_id
  name           = "openai-${var.environment}"
  env_vars = {
    OUTCEPTION_OPENAI_API_KEY = { value = var.openai_secrets.api_key }
  }
}

resource "render_env_group" "pydantic_ai_gateway" {
  environment_id = var.render_environment_id
  name           = "pydantic-ai-gateway-${var.environment}"
  env_vars = {
    OUTCEPTION_PYDANTIC_AI_GATEWAY_API_KEY = { value = var.pydantic_ai_gateway_secrets.api_key }
  }
}

resource "render_env_group" "backend" {
  environment_id = var.render_environment_id
  name           = "backend-${var.environment}"
  env_vars = merge(
    {
      OUTCEPTION_USER_SESSION_COOKIE_DOMAIN           = { value = var.backend_config.user_session_cookie_domain }
      OUTCEPTION_AUTHENTICATION_SESSION_COOKIE_DOMAIN = { value = var.backend_config.authentication_session_cookie_domain }
      OUTCEPTION_OAUTH2_SESSION_STATE_COOKIE_DOMAIN   = { value = var.backend_config.oauth2_session_state_cookie_domain }
      OUTCEPTION_BASE_URL                             = { value = var.backend_config.base_url }
      OUTCEPTION_EMAIL_SENDER                         = { value = var.backend_config.email_sender }
      OUTCEPTION_EMAIL_FROM_NAME                      = { value = var.backend_config.email_from_name }
      OUTCEPTION_EMAIL_FROM_DOMAIN                    = { value = var.backend_config.email_from_domain }
      OUTCEPTION_ENV                                  = { value = local.environment }
      OUTCEPTION_FRONTEND_BASE_URL                    = { value = var.backend_config.frontend_base_url }
      OUTCEPTION_JWKS                                 = { value = var.backend_config.jwks_path }
      OUTCEPTION_LOG_LEVEL                            = { value = var.backend_config.log_level }
      OUTCEPTION_TESTING                              = { value = var.backend_config.testing }
      OUTCEPTION_AUTH_COOKIE_DOMAIN                   = { value = var.backend_config.auth_cookie_domain }
      OUTCEPTION_CURRENT_JWK_KID                      = { value = var.backend_secrets.current_jwk_kid }
      OUTCEPTION_RESEND_API_KEY                       = { value = var.backend_secrets.resend_api_key }
      OUTCEPTION_RESEND_WEBHOOK_SECRET                = { value = var.backend_secrets.resend_webhook_secret }
      OUTCEPTION_LOGO_DEV_PUBLISHABLE_KEY             = { value = var.backend_secrets.logo_dev_publishable_key }
      OUTCEPTION_SECRET                               = { value = var.backend_secrets.secret }
      OUTCEPTION_SENTRY_DSN                           = { value = var.backend_secrets.sentry_dsn }
    },
    var.backend_config.user_session_cookie_key != "" ? {
      OUTCEPTION_USER_SESSION_COOKIE_KEY = { value = var.backend_config.user_session_cookie_key }
    } : {},
    var.backend_config.auth_cookie_key != "" ? {
      OUTCEPTION_AUTH_COOKIE_KEY = { value = var.backend_config.auth_cookie_key }
    } : {},
  )

  secret_files = {
    "jwks.json" = {
      content = var.backend_secrets.jwks
    }
  }
}

resource "render_env_group" "backend_production" {
  count          = var.environment == "production" ? 1 : 0
  environment_id = var.render_environment_id
  name           = "backend-production-only"
  env_vars = {
    OUTCEPTION_POSTHOG_PROJECT_API_KEY        = { value = var.backend_secrets.posthog_project_api_key }
    OUTCEPTION_PLAIN_REQUEST_SIGNING_SECRET   = { value = var.backend_secrets.plain_request_signing_secret }
    OUTCEPTION_PLAIN_TOKEN                    = { value = var.backend_secrets.plain_token }
    OUTCEPTION_PLAIN_CHAT_SECRET              = { value = var.backend_secrets.plain_chat_secret }
    OUTCEPTION_APP_REVIEW_EMAIL               = { value = var.backend_secrets.app_review_email }
    OUTCEPTION_APP_REVIEW_OTP_CODE            = { value = var.backend_secrets.app_review_otp_code }
    OUTCEPTION_CHARGEBACK_STOP_WEBHOOK_SECRET = { value = var.backend_secrets.chargeback_stop_webhook_secret }
  }
}

resource "render_env_group" "aws_s3" {
  environment_id = var.render_environment_id
  name           = "aws-s3-${var.environment}"
  env_vars = {
    OUTCEPTION_AWS_REGION                       = { value = var.aws_s3_config.region }
    OUTCEPTION_AWS_SIGNATURE_VERSION            = { value = var.aws_s3_config.signature_version }
    OUTCEPTION_S3_FILES_BUCKET_NAME             = { value = "outception-${var.environment}-files" }
    OUTCEPTION_S3_FILES_PRESIGN_TTL             = { value = var.aws_s3_config.files_presign_ttl }
    OUTCEPTION_S3_FILES_PUBLIC_BUCKET_NAME      = { value = var.aws_s3_config.files_public_bucket_name }
    OUTCEPTION_S3_CUSTOMER_INVOICES_BUCKET_NAME = { value = var.aws_s3_config.customer_invoices_bucket_name }
    OUTCEPTION_S3_CUSTOMER_RECEIPTS_BUCKET_NAME = { value = var.aws_s3_config.customer_receipts_bucket_name }
    OUTCEPTION_S3_PAYOUT_INVOICES_BUCKET_NAME   = { value = var.aws_s3_config.payout_invoices_bucket_name }
    OUTCEPTION_S3_LOGS_BUCKET_NAME              = { value = var.aws_s3_config.logs_bucket_name }
    OUTCEPTION_AWS_ACCESS_KEY_ID                = { value = var.aws_s3_secrets.access_key_id }
    OUTCEPTION_AWS_SECRET_ACCESS_KEY            = { value = var.aws_s3_secrets.secret_access_key }
    OUTCEPTION_S3_FILES_DOWNLOAD_SALT           = { value = var.aws_s3_secrets.files_download_salt }
    OUTCEPTION_S3_FILES_DOWNLOAD_SECRET         = { value = var.aws_s3_secrets.files_download_secret }
  }
}

resource "render_env_group" "github" {
  environment_id = var.render_environment_id
  name           = "github-${var.environment}"
  env_vars = {
    OUTCEPTION_GITHUB_CLIENT_ID                           = { value = var.github_secrets.client_id }
    OUTCEPTION_GITHUB_CLIENT_SECRET                       = { value = var.github_secrets.client_secret }
    OUTCEPTION_GITHUB_REPOSITORY_BENEFITS_APP_IDENTIFIER  = { value = var.github_secrets.repository_benefits_app_identifier }
    OUTCEPTION_GITHUB_REPOSITORY_BENEFITS_APP_NAMESPACE   = { value = var.github_secrets.repository_benefits_app_namespace }
    OUTCEPTION_GITHUB_REPOSITORY_BENEFITS_APP_PRIVATE_KEY = { value = var.github_secrets.repository_benefits_app_private_key }
    OUTCEPTION_GITHUB_REPOSITORY_BENEFITS_CLIENT_ID       = { value = var.github_secrets.repository_benefits_client_id }
    OUTCEPTION_GITHUB_REPOSITORY_BENEFITS_CLIENT_SECRET   = { value = var.github_secrets.repository_benefits_client_secret }
  }
}

resource "render_env_group" "logfire" {
  count          = var.logfire_config != null ? 1 : 0
  environment_id = var.render_environment_id
  name           = "logfire-${var.environment}"
  env_vars = {
    OUTCEPTION_LOGFIRE_PROJECT_NAME = { value = var.logfire_config.project_name }
    OUTCEPTION_LOGFIRE_TOKEN        = { value = var.logfire_config.token }
  }
}


resource "render_env_group" "apple" {
  environment_id = var.render_environment_id
  name           = "apple-${var.environment}"
  env_vars = {
    OUTCEPTION_APPLE_CLIENT_ID = { value = var.apple_secrets.client_id }
    OUTCEPTION_APPLE_TEAM_ID   = { value = var.apple_secrets.team_id }
    OUTCEPTION_APPLE_KEY_ID    = { value = var.apple_secrets.key_id }
    OUTCEPTION_APPLE_KEY_VALUE = { value = var.apple_secrets.key_value }
  }
}

resource "render_env_group" "prometheus" {
  count          = var.prometheus_config != null ? 1 : 0
  environment_id = var.render_environment_id
  name           = "prometheus-${var.environment}"
  env_vars = merge(
    {
      OUTCEPTION_GRAFANA_CLOUD_PROMETHEUS_WRITE_URL      = { value = "${var.prometheus_config.url}/api/prom/push" }
      OUTCEPTION_GRAFANA_CLOUD_PROMETHEUS_WRITE_USERNAME = { value = var.prometheus_config.username }
      OUTCEPTION_GRAFANA_CLOUD_PROMETHEUS_WRITE_PASSWORD = { value = var.prometheus_config.password }
      OUTCEPTION_GRAFANA_CLOUD_PROMETHEUS_WRITE_INTERVAL = { value = var.prometheus_config.interval }
    },
    var.prometheus_config.query_key != null ? {
      OUTCEPTION_GRAFANA_CLOUD_PROMETHEUS_QUERY_URL  = { value = "${var.prometheus_config.url}/api/prom" }
      OUTCEPTION_GRAFANA_CLOUD_PROMETHEUS_QUERY_USER = { value = var.prometheus_config.username }
      OUTCEPTION_GRAFANA_CLOUD_PROMETHEUS_QUERY_KEY  = { value = var.prometheus_config.query_key }
    } : {}
  )
}

resource "render_env_group" "slo_report" {
  count          = var.slo_report_config != null ? 1 : 0
  environment_id = var.render_environment_id
  name           = "slo-report-${var.environment}"
  env_vars = {
    OUTCEPTION_SLACK_BOT_TOKEN = { value = var.slo_report_config.slack_bot_token }
    OUTCEPTION_SLACK_CHANNEL   = { value = var.slo_report_config.slack_channel }
  }
}

resource "render_env_group" "tinybird" {
  count          = var.tinybird_config != null ? 1 : 0
  environment_id = var.render_environment_id
  name           = "tinybird-${var.environment}"
  env_vars = {
    OUTCEPTION_TINYBIRD_API_URL             = { value = var.tinybird_config.api_url }
    OUTCEPTION_TINYBIRD_CLICKHOUSE_URL      = { value = var.tinybird_config.clickhouse_url }
    OUTCEPTION_TINYBIRD_API_TOKEN           = { value = var.tinybird_config.api_token }
    OUTCEPTION_TINYBIRD_READ_TOKEN          = { value = var.tinybird_config.read_token }
    OUTCEPTION_TINYBIRD_CLICKHOUSE_USERNAME = { value = var.tinybird_config.clickhouse_username }
    OUTCEPTION_TINYBIRD_CLICKHOUSE_TOKEN    = { value = var.tinybird_config.clickhouse_token }
    OUTCEPTION_TINYBIRD_WORKSPACE           = { value = var.tinybird_config.workspace }
  }
}

resource "render_env_group" "outception_self" {
  count          = var.outception_self_config != null ? 1 : 0
  environment_id = var.render_environment_id
  name           = "outception-self-${var.environment}"
  env_vars = {
    OUTCEPTION_OUTCEPTION_ACCESS_TOKEN     = { value = var.outception_self_config.access_token }
    OUTCEPTION_OUTCEPTION_WEBHOOK_SECRET   = { value = var.outception_self_config.webhook_secret }
    OUTCEPTION_OUTCEPTION_ORGANIZATION_ID  = { value = var.outception_self_config.organization_id }
    OUTCEPTION_OUTCEPTION_API_URL          = { value = var.outception_self_config.api_url }
  }
}

resource "render_env_group" "memory_profile" {
  count          = var.memory_profile_config != null ? 1 : 0
  environment_id = var.render_environment_id
  name           = "memory-profile-${var.environment}"
  env_vars = {
    OUTCEPTION_MEMORY_PROFILE_ENABLED        = { value = "true" }
    OUTCEPTION_MEMORY_PROFILE_S3_BUCKET_NAME = { value = var.memory_profile_config.s3_bucket_name }
    OUTCEPTION_MEMORY_PROFILE_INTERVAL       = { value = var.memory_profile_config.interval }
  }
}

resource "render_env_group" "database" {
  environment_id = var.render_environment_id
  name           = "database-${var.environment}"
  env_vars = {
    OUTCEPTION_POSTGRES_DATABASE      = { value = var.api_service_config.postgres_database }
    OUTCEPTION_POSTGRES_HOST          = { value = var.postgres_config.host }
    OUTCEPTION_POSTGRES_PORT          = { value = var.postgres_config.port }
    OUTCEPTION_POSTGRES_USER          = { value = var.postgres_config.user }
    OUTCEPTION_POSTGRES_PWD           = { value = var.postgres_config.password }
    OUTCEPTION_POSTGRES_READ_DATABASE = { value = var.api_service_config.postgres_read_database }
    OUTCEPTION_POSTGRES_READ_HOST     = { value = var.postgres_config.read_host }
    OUTCEPTION_POSTGRES_READ_PORT     = { value = var.postgres_config.read_port }
    OUTCEPTION_POSTGRES_READ_USER     = { value = var.postgres_config.read_user }
    OUTCEPTION_POSTGRES_READ_PWD      = { value = var.postgres_config.read_password }
  }
}

resource "render_env_group" "redis" {
  environment_id = var.render_environment_id
  name           = "redis-${var.environment}"
  env_vars = {
    OUTCEPTION_REDIS_HOST = { value = var.redis_config.host }
    OUTCEPTION_REDIS_PORT = { value = var.redis_config.port }
    OUTCEPTION_REDIS_DB   = { value = var.api_service_config.redis_db }
  }
}

# Services


resource "render_web_service" "api" {
  environment_id     = var.render_environment_id
  name               = "api${local.env_suffix}"
  plan               = var.api_service_config.plan
  region             = "ohio"
  health_check_path  = "/healthz"
  pre_deploy_command = "uv run task pre_deploy"

  # Deploy from the "latest" tag so newly created services come up on the most
  # recent main build. CI deploys specific digests out-of-band (deploy_server.sh),
  # so ignore_changes below keeps Terraform from reverting them.
  runtime_source = {
    image = {
      image_url              = split("@", var.api_service_config.image_url)[0]
      registry_credential_id = var.registry_credential_id
      tag                    = "latest"
    }
  }

  lifecycle {
    ignore_changes = [runtime_source.image]
  }

  autoscaling = var.environment == "production" ? {
    enabled = true
    min     = 2
    max     = 4
    criteria = {
      cpu = {
        enabled    = true
        percentage = 90
      }
      memory = {
        enabled    = true
        percentage = 90
      }
    }
    } : var.environment == "sandbox" ? {
    enabled = true
    min     = 2
    max     = 2
    criteria = {
      cpu = {
        enabled    = true
        percentage = 90
      }
      memory = {
        enabled    = true
        percentage = 90
      }
    }
  } : null

  custom_domains = var.api_service_config.custom_domains

  env_vars = {
    SERVICE_NAME             = { value = "api${local.env_suffix}" }
    WEB_CONCURRENCY          = { value = var.api_service_config.web_concurrency }
    FORWARDED_ALLOW_IPS      = { value = var.api_service_config.forwarded_allow_ips }
    OUTCEPTION_ALLOWED_HOSTS      = { value = var.api_service_config.allowed_hosts }
    OUTCEPTION_CORS_ORIGINS       = { value = var.api_service_config.cors_origins }
    OUTCEPTION_DATABASE_POOL_SIZE = { value = var.api_service_config.database_pool_size }
  }
}

resource "render_web_service" "worker" {
  for_each = var.workers

  environment_id    = var.render_environment_id
  name              = each.key
  plan              = each.value.plan
  region            = "ohio"
  health_check_path = "/"
  start_command     = each.value.start_command
  num_instances     = each.value.num_instances

  # Deploy from the "latest" tag so newly created services come up on the most
  # recent main build. CI deploys specific digests out-of-band (deploy_server.sh),
  # so ignore_changes below keeps Terraform from reverting them.
  runtime_source = {
    image = {
      image_url              = split("@", each.value.image_url)[0]
      registry_credential_id = var.registry_credential_id
      tag                    = "latest"
    }
  }

  lifecycle {
    ignore_changes = [runtime_source.image]
  }

  custom_domains = length(each.value.custom_domains) > 0 ? each.value.custom_domains : null

  env_vars = {
    SERVICE_NAME             = { value = each.key }
    dramatiq_prom_port       = { value = each.value.dramatiq_prom_port }
    OUTCEPTION_DATABASE_POOL_SIZE = { value = each.value.database_pool_size }
  }
}

resource "render_cron_job" "cron" {
  for_each = var.cron_jobs

  environment_id = var.render_environment_id
  name           = each.key
  plan           = each.value.plan
  region         = "ohio"
  schedule       = each.value.schedule
  start_command  = each.value.start_command

  # Cron jobs use tag "latest" instead of a pinned digest so Render
  # automatically pulls the newest image before each run.
  runtime_source = {
    image = {
      image_url              = split("@", coalesce(each.value.image_url, var.api_service_config.image_url))[0]
      registry_credential_id = var.registry_credential_id
      tag                    = "latest"
    }
  }

  # Cron jobs don't support Render secret_files, so we pass JWKS as an env var
  # and write it to a temp file in the start command. OUTCEPTION_JWKS is set here
  # to override the env group value (/etc/secrets/jwks.json) which doesn't exist.
  env_vars = {
    SERVICE_NAME             = { value = each.key }
    OUTCEPTION_DATABASE_POOL_SIZE = { value = each.value.database_pool_size }
    OUTCEPTION_JWKS               = { value = "/tmp/jwks.json" }
    OUTCEPTION_JWKS_CONTENT       = { value = var.backend_secrets.jwks }
  }
}

locals {
  env_suffix      = var.environment == "production" ? "" : "-${var.environment}"
  worker_ids      = [for w in render_web_service.worker : w.id]
  cron_job_ids    = [for c in render_cron_job.cron : c.id]
  all_service_ids = concat([render_web_service.api.id], local.worker_ids, local.cron_job_ids)
}

# Env group links
resource "render_env_group_link" "database" {
  env_group_id = render_env_group.database.id
  service_ids  = local.all_service_ids
}

resource "render_env_group_link" "redis" {
  env_group_id = render_env_group.redis.id
  service_ids  = local.all_service_ids
}

resource "render_env_group_link" "aws_s3" {
  env_group_id = render_env_group.aws_s3.id
  service_ids  = local.all_service_ids
}

resource "render_env_group_link" "google" {
  env_group_id = render_env_group.google.id
  service_ids  = local.all_service_ids
}

resource "render_env_group_link" "github" {
  env_group_id = render_env_group.github.id
  service_ids  = local.all_service_ids
}

resource "render_env_group_link" "backend" {
  env_group_id = render_env_group.backend.id
  service_ids  = local.all_service_ids
}

resource "render_env_group_link" "backend_production" {
  count        = var.environment == "production" ? 1 : 0
  env_group_id = render_env_group.backend_production[0].id
  service_ids  = local.all_service_ids
}

resource "render_env_group_link" "logfire" {
  count        = var.logfire_config != null ? 1 : 0
  env_group_id = render_env_group.logfire[0].id
  service_ids  = local.all_service_ids
}

resource "render_env_group_link" "openai" {
  env_group_id = render_env_group.openai.id
  service_ids  = local.all_service_ids
}

resource "render_env_group_link" "pydantic_ai_gateway" {
  env_group_id = render_env_group.pydantic_ai_gateway.id
  service_ids  = local.all_service_ids
}

resource "render_env_group_link" "apple" {
  env_group_id = render_env_group.apple.id
  service_ids  = [render_web_service.api.id]
}

resource "render_env_group_link" "prometheus" {
  count        = var.prometheus_config != null ? 1 : 0
  env_group_id = render_env_group.prometheus[0].id
  service_ids  = local.all_service_ids
}

resource "render_env_group_link" "slo_report" {
  count        = var.slo_report_config != null ? 1 : 0
  env_group_id = render_env_group.slo_report[0].id
  service_ids  = local.all_service_ids
}

resource "render_env_group_link" "tinybird" {
  count        = var.tinybird_config != null ? 1 : 0
  env_group_id = render_env_group.tinybird[0].id
  service_ids  = local.all_service_ids
}

resource "render_env_group_link" "outception_self" {
  count        = var.outception_self_config != null ? 1 : 0
  env_group_id = render_env_group.outception_self[0].id
  service_ids  = local.all_service_ids
}

resource "render_env_group_link" "memory_profile" {
  count        = var.memory_profile_config != null ? 1 : 0
  env_group_id = render_env_group.memory_profile[0].id
  service_ids  = concat([render_web_service.api.id], local.worker_ids)
}

resource "cloudflare_dns_record" "resend_dkim" {
  zone_id = var.resend_domain.zone_id
  name    = "resend._domainkey.${var.backend_config.email_from_domain}"
  type    = "TXT"
  content = var.resend_domain.dkim_public_key
  ttl     = 1
}

resource "cloudflare_dns_record" "resend_spf_mx" {
  zone_id  = var.resend_domain.zone_id
  name     = "send.${var.backend_config.email_from_domain}"
  type     = "MX"
  content  = "feedback-smtp.us-east-1.amazonses.com"
  priority = 10
  ttl      = 1
}

resource "cloudflare_dns_record" "resend_spf_txt" {
  zone_id = var.resend_domain.zone_id
  name    = "send.${var.backend_config.email_from_domain}"
  type    = "TXT"
  content = var.resend_domain.spf_policy
  ttl     = 1
}
