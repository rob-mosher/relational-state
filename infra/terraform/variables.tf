variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "Optional AWS profile name to use for credentials resolution."
  type        = string
  default     = ""
}

variable "memory_bucket_name" {
  description = "Globally unique S3 bucket name for durable memory storage."
  type        = string
}

variable "lambda_function_name" {
  description = "Name of the MCP server Lambda function."
  type        = string
  default     = "mcp-server"
}

variable "api_name" {
  description = "Name of the HTTP API Gateway."
  type        = string
  default     = "mcp-memory-ingress"
}

variable "stage_name" {
  description = "API Gateway stage name."
  type        = string
  default     = "prod"
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period in days."
  type        = number
  default     = 7
}

variable "alarm_actions" {
  description = "Optional list of ARNs to notify when alarms fire."
  type        = list(string)
  default     = []
}

variable "api_authorization_type" {
  description = "API Gateway route authorization type (JWT or NONE)."
  type        = string
  default     = "NONE"

  validation {
    condition     = contains(["JWT", "NONE"], var.api_authorization_type)
    error_message = "api_authorization_type must be one of: JWT, NONE."
  }
}

variable "oauth_scopes" {
  description = "OAuth scopes to allow for the MCP client."
  type        = list(string)
  default     = ["openid", "email", "profile"]
}

variable "oauth_resource" {
  description = "Optional OAuth resource identifier (defaults to MCP base URL)."
  type        = string
  default     = ""
}

variable "oauth_issuer" {
  description = "OAuth issuer URL (defaults to jwt_issuer). Example: https://YOUR_TENANT.auth0.com/"
  type        = string
  default     = ""
}

variable "oauth_authorization_endpoint" {
  description = "OAuth authorization endpoint. Example: https://YOUR_TENANT.auth0.com/authorize"
  type        = string
  default     = ""
}

variable "oauth_token_endpoint" {
  description = "OAuth token endpoint. Example: https://YOUR_TENANT.auth0.com/oauth/token"
  type        = string
  default     = ""
}

variable "oauth_userinfo_endpoint" {
  description = "OAuth userinfo endpoint. Example: https://YOUR_TENANT.auth0.com/userinfo"
  type        = string
  default     = ""
}

variable "oauth_jwks_uri" {
  description = "OAuth JWKS endpoint (defaults to {oauth_issuer}/.well-known/jwks.json)."
  type        = string
  default     = ""
}

variable "oauth_registration_endpoint" {
  description = "OAuth dynamic client registration endpoint (if supported by IdP)."
  type        = string
  default     = ""
}

variable "oauth_device_authorization_endpoint" {
  description = "OAuth device authorization endpoint for CLI/TUI clients. Example: https://YOUR_TENANT.auth0.com/oauth/device/code"
  type        = string
  default     = ""
}

variable "jwt_issuer" {
  description = "JWT issuer URL (required when api_authorization_type = JWT). Example: https://YOUR_TENANT.auth0.com/"
  type        = string
  default     = ""

  validation {
    condition     = var.api_authorization_type != "JWT" || trimspace(var.jwt_issuer) != ""
    error_message = "jwt_issuer must be set when api_authorization_type is JWT."
  }
}

variable "jwt_audiences" {
  description = "JWT audience list (required when api_authorization_type = JWT). Example: your Auth0 API identifier."
  type        = list(string)
  default     = []

  validation {
    condition     = var.api_authorization_type != "JWT" || length(var.jwt_audiences) > 0
    error_message = "jwt_audiences must be set when api_authorization_type is JWT."
  }
}

variable "jwt_authorization_scopes" {
  description = "Optional JWT scopes required by API Gateway (empty list means no scope checks)."
  type        = list(string)
  default     = []
}

variable "throttling_burst_limit" {
  description = "Optional API Gateway burst limit (requests). Null leaves AWS default."
  type        = number
  default     = null
}

variable "throttling_rate_limit" {
  description = "Optional API Gateway steady-state rate limit (requests per second). Null leaves AWS default."
  type        = number
  default     = null
}

variable "custom_domain_name" {
  description = "Optional custom domain name for the API Gateway."
  type        = string
  default     = ""

  validation {
    condition = (
      trimspace(var.custom_domain_name) == "" && trimspace(var.acm_certificate_arn) == ""
      ) || (
      trimspace(var.custom_domain_name) != "" && trimspace(var.acm_certificate_arn) != ""
    )
    error_message = "custom_domain_name and acm_certificate_arn must both be set or both be empty."
  }
}

variable "acm_certificate_arn" {
  description = "Optional ACM certificate ARN for the custom domain (must be in aws_region)."
  type        = string
  default     = ""
}
