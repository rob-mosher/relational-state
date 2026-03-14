output "memory_bucket_name" {
  description = "Durable, append-only S3 bucket name."
  value       = aws_s3_bucket.memory.bucket
}

output "aws_region" {
  description = "AWS region for this deployment."
  value       = var.aws_region
}

output "mcp_server_lambda_name" {
  description = "Lambda function name for the MCP server."
  value       = aws_lambda_function.add_memory.function_name
}

output "api_stage_invoke_url" {
  description = "Base invoke URL for the deployed API stage."
  value       = aws_apigatewayv2_stage.this.invoke_url
}

output "custom_domain_target" {
  description = "Target domain name for custom domain DNS (if enabled)."
  value       = try(aws_apigatewayv2_domain_name.custom[0].domain_name_configuration[0].target_domain_name, null)
}

output "custom_domain_zone_id" {
  description = "Hosted zone ID for custom domain alias record (if enabled)."
  value       = try(aws_apigatewayv2_domain_name.custom[0].domain_name_configuration[0].hosted_zone_id, null)
}

output "mcp_url" {
  description = "Base HTTPS endpoint for the MCP server."
  value       = local.mcp_base_url
}

output "authorization_type" {
  description = "MCP server route authorization type (JWT uses bearer tokens, NONE for dev)."
  value       = aws_apigatewayv2_route.add_memory.authorization_type
}

output "jwt_issuer" {
  description = "JWT issuer URL."
  value       = local.jwt_issuer
}

output "jwt_audiences" {
  description = "JWT audience list enforced by the API."
  value       = local.jwt_audiences
}

output "jwt_jwks_url" {
  description = "JWKS endpoint for the configured JWT issuer."
  value       = "${local.jwt_issuer}/.well-known/jwks.json"
}

output "oauth_protected_resource_url" {
  description = "OAuth protected resource metadata URL."
  value       = "${local.mcp_base_url}.well-known/oauth-protected-resource"
}

output "oauth_authorization_endpoint" {
  description = "OAuth authorization endpoint."
  value       = local.oauth_authorization_endpoint
}

output "oauth_token_endpoint" {
  description = "OAuth token endpoint."
  value       = local.oauth_token_endpoint
}

output "oauth_registration_endpoint" {
  description = "OAuth dynamic client registration endpoint (if configured)."
  value       = local.oauth_registration_endpoint
}

output "oauth_device_authorization_endpoint" {
  description = "OAuth device authorization endpoint for CLI/TUI clients."
  value       = local.oauth_device_authorization_endpoint
}

output "oauth_issuer" {
  description = "OAuth issuer used for the MCP resource."
  value       = local.oauth_issuer
}

output "lambda_log_group_name" {
  description = "CloudWatch log group for the MCP server Lambda."
  value       = aws_cloudwatch_log_group.add_memory_lambda.name
}

output "api_access_log_group_name" {
  description = "CloudWatch log group receiving API Gateway access logs."
  value       = aws_cloudwatch_log_group.api_access.name
}

output "lambda_errors_alarm_name" {
  description = "Alarm name for Lambda errors."
  value       = aws_cloudwatch_metric_alarm.lambda_errors.alarm_name
}

output "api_5xx_alarm_name" {
  description = "Alarm name for API Gateway 5xx responses."
  value       = aws_cloudwatch_metric_alarm.api_5xx.alarm_name
}

