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
  description = "Name of the append_memory Lambda function."
  type        = string
  default     = "append-memory"
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
  description = "API Gateway route authorization type (AWS_IAM or NONE)."
  type        = string
  default     = "AWS_IAM"

  validation {
    condition     = contains(["AWS_IAM", "NONE"], var.api_authorization_type)
    error_message = "api_authorization_type must be one of: AWS_IAM, NONE."
  }
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
