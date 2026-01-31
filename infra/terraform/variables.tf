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

variable "create_caller_user" {
  description = "Whether to create a dedicated IAM caller user for invoking the API."
  type        = bool
  default     = true
}

variable "create_caller_access_key" {
  description = "Whether to create an access key for the caller user (stored in state)."
  type        = bool
  default     = true
}

variable "caller_user_name" {
  description = "IAM username for the dedicated API caller."
  type        = string
  default     = "relational-state-caller"
}

variable "caller_policy_scope" {
  description = "Scope for the caller invoke policy: exact, stage, or api."
  type        = string
  default     = "stage"

  validation {
    condition     = contains(["exact", "stage", "api"], var.caller_policy_scope)
    error_message = "caller_policy_scope must be one of: exact, stage, api."
  }
}

variable "api_authorization_type" {
  description = "API Gateway route authorization type (AWS_IAM, JWT, or NONE)."
  type        = string
  default     = "AWS_IAM"

  validation {
    condition     = contains(["AWS_IAM", "JWT", "NONE"], var.api_authorization_type)
    error_message = "api_authorization_type must be one of: AWS_IAM, JWT, NONE."
  }
}

variable "create_cognito_user_pool" {
  description = "Whether to create a Cognito User Pool for JWT auth."
  type        = bool
  default     = false
}

variable "cognito_user_pool_name" {
  description = "Cognito User Pool name (when create_cognito_user_pool = true)."
  type        = string
  default     = "relational-state-mcp"
}

variable "cognito_user_pool_client_name" {
  description = "Cognito User Pool app client name (when create_cognito_user_pool = true)."
  type        = string
  default     = "relational-state-mcp-client"
}

variable "jwt_issuer" {
  description = "JWT issuer URL (used when api_authorization_type = JWT and not creating a Cognito pool)."
  type        = string
  default     = ""

  validation {
    condition = (
      var.api_authorization_type != "JWT"
      || var.create_cognito_user_pool
      || trimspace(var.jwt_issuer) != ""
    )
    error_message = "jwt_issuer must be set when api_authorization_type is JWT and create_cognito_user_pool is false."
  }
}

variable "jwt_audiences" {
  description = "JWT audience list (used when api_authorization_type = JWT and not creating a Cognito pool)."
  type        = list(string)
  default     = []

  validation {
    condition = (
      var.api_authorization_type != "JWT"
      || var.create_cognito_user_pool
      || length(var.jwt_audiences) > 0
    )
    error_message = "jwt_audiences must be set when api_authorization_type is JWT and create_cognito_user_pool is false."
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
