provider "aws" {
  region  = var.aws_region
  profile = trimspace(var.aws_profile) != "" ? trimspace(var.aws_profile) : null
}

locals {
  lambda_source_dir     = "${path.module}/../lambda/mcp_server"
  lambda_zip_path       = "${path.module}/build/mcp_server.zip"
  lambda_log_group_name = "/aws/lambda/${var.lambda_function_name}"
  api_access_log_group  = "/aws/apigateway/${var.api_name}/${var.stage_name}"
  mcp_method            = "POST"
  mcp_path              = ""
  mcp_invoke_arn        = "${aws_apigatewayv2_api.memory_ingress.execution_arn}/${var.stage_name}/${local.mcp_method}/${local.mcp_path}"
  mcp_stage_arn         = "${aws_apigatewayv2_api.memory_ingress.execution_arn}/${var.stage_name}/${local.mcp_method}/*"
  mcp_api_arn           = "${aws_apigatewayv2_api.memory_ingress.execution_arn}/*/${local.mcp_method}/*"
  api_access_log_format = jsonencode(
    {
      requestId          = "$context.requestId"
      ip                 = "$context.identity.sourceIp"
      requestTime        = "$context.requestTime"
      httpMethod         = "$context.httpMethod"
      routeKey           = "$context.routeKey"
      status             = "$context.status"
      protocol           = "$context.protocol"
      responseLength     = "$context.responseLength"
      integrationError   = "$context.integrationErrorMessage"
      integrationStatus  = "$context.integrationStatus"
      integrationLatency = "$context.integrationLatency"
    }
  )
}

data "archive_file" "append_memory_zip" {
  type        = "zip"
  source_dir  = local.lambda_source_dir
  output_path = local.lambda_zip_path
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "append_memory_lambda_role" {
  name               = "${var.lambda_function_name}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "append_memory_s3_policy" {
  statement {
    sid     = "AllowPutMemoryObjects"
    effect  = "Allow"
    actions = ["s3:PutObject"]
    resources = [
      "${aws_s3_bucket.memory.arn}/*",
    ]
  }

  statement {
    sid     = "AllowListMemoryPrefixes"
    effect  = "Allow"
    actions = ["s3:ListBucket"]
    resources = [
      aws_s3_bucket.memory.arn,
    ]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["memories/*"]
    }
  }

  statement {
    sid     = "AllowGetBucketLocation"
    effect  = "Allow"
    actions = ["s3:GetBucketLocation"]
    resources = [
      aws_s3_bucket.memory.arn,
    ]
  }
}

resource "aws_iam_role_policy" "append_memory_s3" {
  name   = "${var.lambda_function_name}-s3"
  role   = aws_iam_role.append_memory_lambda_role.id
  policy = data.aws_iam_policy_document.append_memory_s3_policy.json
}

resource "aws_iam_role_policy_attachment" "append_memory_logs" {
  role       = aws_iam_role.append_memory_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_s3_bucket" "memory" {
  bucket = var.memory_bucket_name
}

resource "aws_s3_bucket_versioning" "memory" {
  bucket = aws_s3_bucket.memory.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_cloudwatch_log_group" "append_memory_lambda" {
  name              = local.lambda_log_group_name
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "api_access" {
  name              = local.api_access_log_group
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "append_memory" {
  function_name = var.lambda_function_name
  role          = aws_iam_role.append_memory_lambda_role.arn
  handler       = "handler.handler"
  runtime       = "python3.11"
  timeout       = 10

  filename         = data.archive_file.append_memory_zip.output_path
  source_code_hash = data.archive_file.append_memory_zip.output_base64sha256

  environment {
    variables = {
      MEMORY_BUCKET_NAME = aws_s3_bucket.memory.bucket
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.append_memory_logs,
    aws_iam_role_policy.append_memory_s3,
    aws_s3_bucket_versioning.memory,
    aws_cloudwatch_log_group.append_memory_lambda,
  ]
}

resource "aws_apigatewayv2_api" "memory_ingress" {
  name          = var.api_name
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "append_memory" {
  api_id                 = aws_apigatewayv2_api.memory_ingress.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.append_memory.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 10000
}

resource "aws_apigatewayv2_route" "append_memory" {
  api_id    = aws_apigatewayv2_api.memory_ingress.id
  route_key = "POST /"
  target    = "integrations/${aws_apigatewayv2_integration.append_memory.id}"

  # Switchable for dev convenience.
  authorization_type = var.api_authorization_type
}

resource "aws_apigatewayv2_stage" "this" {
  api_id      = aws_apigatewayv2_api.memory_ingress.id
  name        = var.stage_name
  auto_deploy = true

  default_route_settings {
    detailed_metrics_enabled = true
    throttling_burst_limit   = var.throttling_burst_limit
    throttling_rate_limit    = var.throttling_rate_limit
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_access.arn
    format          = local.api_access_log_format
  }
}

data "aws_iam_policy_document" "caller_invoke_api" {
  count = var.create_caller_user ? 1 : 0

  statement {
    sid    = "AllowInvokeMcpServer"
    effect = "Allow"
    actions = [
      "execute-api:Invoke",
    ]
    resources = [
      var.caller_policy_scope == "exact"
      ? local.mcp_invoke_arn
      : var.caller_policy_scope == "stage"
      ? local.mcp_stage_arn
      : local.mcp_api_arn,
    ]
  }
}

resource "aws_iam_user" "caller" {
  count = var.create_caller_user ? 1 : 0

  name          = var.caller_user_name
  force_destroy = true
}

resource "aws_iam_user_policy" "caller_invoke_api" {
  count = var.create_caller_user ? 1 : 0

  name   = "${var.caller_user_name}-invoke-${var.lambda_function_name}"
  user   = aws_iam_user.caller[0].name
  policy = data.aws_iam_policy_document.caller_invoke_api[0].json
}

resource "aws_iam_access_key" "caller" {
  count = var.create_caller_user && var.create_caller_access_key ? 1 : 0

  user = aws_iam_user.caller[0].name
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.lambda_function_name}-errors"
  alarm_description   = "Lambda ${var.lambda_function_name} returned errors."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.alarm_actions

  dimensions = {
    FunctionName = aws_lambda_function.append_memory.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "${var.lambda_function_name}-throttles"
  alarm_description   = "Lambda ${var.lambda_function_name} is being throttled."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.alarm_actions

  dimensions = {
    FunctionName = aws_lambda_function.append_memory.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "api_5xx" {
  alarm_name          = "${var.api_name}-${var.stage_name}-5xx"
  alarm_description   = "API Gateway stage is returning 5xx responses."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "5xx"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.alarm_actions

  dimensions = {
    ApiId = aws_apigatewayv2_api.memory_ingress.id
    Stage = var.stage_name
  }
}

resource "aws_lambda_permission" "allow_apigateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.append_memory.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.memory_ingress.execution_arn}/*/*"
}
