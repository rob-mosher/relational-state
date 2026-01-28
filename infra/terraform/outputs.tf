output "memory_bucket_name" {
  description = "Durable, append-only S3 bucket name."
  value       = aws_s3_bucket.memory.bucket
}

output "mcp_server_lambda_name" {
  description = "Lambda function name for the MCP server."
  value       = aws_lambda_function.append_memory.function_name
}

output "api_stage_invoke_url" {
  description = "Base invoke URL for the deployed API stage."
  value       = aws_apigatewayv2_stage.this.invoke_url
}

output "mcp_url" {
  description = "Base HTTPS endpoint for the MCP server."
  value       = "${trimsuffix(aws_apigatewayv2_stage.this.invoke_url, "/")}/"
}

output "authorization_type" {
  description = "MCP server route authorization type (AWS_IAM requires SigV4 signing)."
  value       = aws_apigatewayv2_route.append_memory.authorization_type
}

output "lambda_log_group_name" {
  description = "CloudWatch log group for the MCP server Lambda."
  value       = aws_cloudwatch_log_group.append_memory_lambda.name
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

output "caller_user_name" {
  description = "Dedicated IAM caller username (if enabled)."
  value       = try(aws_iam_user.caller[0].name, null)
}

output "caller_invoke_arn" {
  description = "Execute API ARN the caller policy allows."
  value       = local.mcp_invoke_arn
}

output "caller_access_key_id" {
  description = "Access key ID for the dedicated caller user (if enabled)."
  value       = try(aws_iam_access_key.caller[0].id, null)
  sensitive   = true
}

output "caller_secret_access_key" {
  description = "Secret access key for the dedicated caller user (if enabled)."
  value       = try(aws_iam_access_key.caller[0].secret, null)
  sensitive   = true
}
