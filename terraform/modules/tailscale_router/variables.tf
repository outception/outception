variable "environment" {
  description = "Environment name (production)"
  type        = string

  validation {
    condition     = contains(["production"], var.environment)
    error_message = "Must be \"production\"."
  }
}

variable "render_environment_id" {
  description = "The environment ID in Render"
  type        = string
}

variable "registry_credential_id" {
  description = "Render registry credential ID for GHCR"
  type        = string
  sensitive   = true
}

variable "image_url" {
  description = "Docker image URL for the Tailscale router"
  type        = string
  default     = "ghcr.io/outception/outception-tailscale"
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}

variable "tailscale_authkey" {
  description = "Tailscale auth key (tskey-auth-...)"
  type        = string
  sensitive   = true
}

variable "advertise_routes" {
  description = "Comma-separated CIDR routes to advertise"
  type        = string
}

variable "tailscale_version" {
  description = "Tailscale version to install"
  type        = string
  default     = "1.94.2"
}

variable "plan" {
  description = "Render service plan"
  type        = string
  default     = "starter"
}
