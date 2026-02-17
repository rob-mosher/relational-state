provider "aws" {
  region  = var.aws_region
  profile = trimspace(var.aws_profile) != "" ? trimspace(var.aws_profile) : null
}

moved {
  from = data.archive_file.append_memory_zip
  to   = data.archive_file.add_memory_zip
}

moved {
  from = resource.aws_iam_role.append_memory_lambda_role
  to   = resource.aws_iam_role.add_memory_lambda_role
}

moved {
  from = data.aws_iam_policy_document.append_memory_s3_policy
  to   = data.aws_iam_policy_document.add_memory_s3_policy
}

moved {
  from = resource.aws_iam_role_policy.append_memory_s3
  to   = resource.aws_iam_role_policy.add_memory_s3
}

moved {
  from = resource.aws_iam_role_policy_attachment.append_memory_logs
  to   = resource.aws_iam_role_policy_attachment.add_memory_logs
}

moved {
  from = resource.aws_cloudwatch_log_group.append_memory_lambda
  to   = resource.aws_cloudwatch_log_group.add_memory_lambda
}

moved {
  from = resource.aws_lambda_function.append_memory
  to   = resource.aws_lambda_function.add_memory
}

moved {
  from = resource.aws_apigatewayv2_integration.append_memory
  to   = resource.aws_apigatewayv2_integration.add_memory
}

moved {
  from = resource.aws_apigatewayv2_route.append_memory
  to   = resource.aws_apigatewayv2_route.add_memory
}

locals {
  lambda_source_dir     = "${path.module}/../lambda/mcp_server"
  lambda_zip_path       = "${path.module}/build/mcp_server.zip"
  lambda_log_group_name = "/aws/lambda/${var.lambda_function_name}"
  api_access_log_group  = "/aws/apigateway/${var.api_name}/${var.stage_name}"
  custom_domain_enabled = trimspace(var.custom_domain_name) != "" && trimspace(var.acm_certificate_arn) != ""
  mcp_base_url          = local.custom_domain_enabled ? "https://${var.custom_domain_name}/" : "${trimsuffix(aws_apigatewayv2_stage.this.invoke_url, "/")}/"
  mcp_method            = "POST"
  mcp_path              = ""
  mcp_invoke_arn        = "${aws_apigatewayv2_api.memory_ingress.execution_arn}/${var.stage_name}/${local.mcp_method}/${local.mcp_path}"
  mcp_stage_arn         = "${aws_apigatewayv2_api.memory_ingress.execution_arn}/${var.stage_name}/${local.mcp_method}/*"
  mcp_api_arn           = "${aws_apigatewayv2_api.memory_ingress.execution_arn}/*/${local.mcp_method}/*"
  jwt_issuer            = var.create_cognito_user_pool ? "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.mcp[0].id}" : var.jwt_issuer
  jwt_audiences         = var.create_cognito_user_pool ? [aws_cognito_user_pool_client.mcp[0].id] : var.jwt_audiences
  cognito_domain_enabled = (
    var.create_cognito_user_pool && trimspace(var.cognito_domain_prefix) != ""
  )
  cognito_domain                 = local.cognito_domain_enabled ? "${var.cognito_domain_prefix}.auth.${var.aws_region}.amazoncognito.com" : ""
  cognito_authorization_endpoint = local.cognito_domain_enabled ? "https://${local.cognito_domain}/oauth2/authorize" : ""
  cognito_token_endpoint         = local.cognito_domain_enabled ? "https://${local.cognito_domain}/oauth2/token" : ""
  cognito_userinfo_endpoint      = local.cognito_domain_enabled ? "https://${local.cognito_domain}/oauth2/userInfo" : ""
  oauth_issuer                   = trimspace(var.oauth_issuer) != "" ? var.oauth_issuer : local.jwt_issuer
  oauth_jwks_uri = (
    trimspace(var.oauth_jwks_uri) != ""
    ? var.oauth_jwks_uri
    : "${local.oauth_issuer}/.well-known/jwks.json"
  )
  oauth_authorization_endpoint = (
    trimspace(var.oauth_authorization_endpoint) != ""
    ? var.oauth_authorization_endpoint
    : local.cognito_authorization_endpoint
  )
  oauth_token_endpoint = (
    trimspace(var.oauth_token_endpoint) != ""
    ? var.oauth_token_endpoint
    : local.cognito_token_endpoint
  )
  oauth_userinfo_endpoint = (
    trimspace(var.oauth_userinfo_endpoint) != ""
    ? var.oauth_userinfo_endpoint
    : local.cognito_userinfo_endpoint
  )
  oauth_registration_endpoint = (
    trimspace(var.oauth_registration_endpoint) != ""
    ? var.oauth_registration_endpoint
    : var.enable_dcr_proxy
    ? "${local.mcp_base_url}oauth/register"
    : ""
  )
  oauth_resource = trimspace(var.oauth_resource) != "" ? var.oauth_resource : local.mcp_base_url
  oauth_scopes   = length(var.oauth_scopes) > 0 ? var.oauth_scopes : ["openid", "email", "profile"]
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

data "archive_file" "add_memory_zip" {
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

resource "aws_iam_role" "add_memory_lambda_role" {
  name               = "${var.lambda_function_name}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "add_memory_s3_policy" {
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

  dynamic "statement" {
    for_each = var.create_cognito_user_pool && var.enable_dcr_proxy ? [1] : []
    content {
      sid    = "AllowCognitoClientRegistration"
      effect = "Allow"
      actions = [
        "cognito-idp:CreateUserPoolClient",
        "cognito-idp:DescribeUserPoolClient",
        "cognito-idp:ListUserPoolClients",
        "cognito-idp:DescribeUserPool",
      ]
      resources = [aws_cognito_user_pool.mcp[0].arn]
    }
  }
}

resource "aws_iam_role_policy" "add_memory_s3" {
  name   = "${var.lambda_function_name}-s3"
  role   = aws_iam_role.add_memory_lambda_role.id
  policy = data.aws_iam_policy_document.add_memory_s3_policy.json
}

resource "aws_iam_role_policy_attachment" "add_memory_logs" {
  role       = aws_iam_role.add_memory_lambda_role.name
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

resource "aws_cloudwatch_log_group" "add_memory_lambda" {
  name              = local.lambda_log_group_name
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "api_access" {
  name              = local.api_access_log_group
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "add_memory" {
  function_name = var.lambda_function_name
  role          = aws_iam_role.add_memory_lambda_role.arn
  handler       = "handler.handler"
  runtime       = "python3.11"
  timeout       = 10

  filename         = data.archive_file.add_memory_zip.output_path
  source_code_hash = data.archive_file.add_memory_zip.output_base64sha256

  environment {
    variables = {
      MEMORY_BUCKET_NAME                = aws_s3_bucket.memory.bucket
      OAUTH_ISSUER                      = local.oauth_issuer
      OAUTH_JWKS_URI                    = local.oauth_jwks_uri
      OAUTH_AUTHORIZATION_ENDPOINT      = local.oauth_authorization_endpoint
      OAUTH_TOKEN_ENDPOINT              = local.oauth_token_endpoint
      OAUTH_USERINFO_ENDPOINT           = local.oauth_userinfo_endpoint
      OAUTH_REGISTRATION_ENDPOINT       = local.oauth_registration_endpoint
      OAUTH_RESOURCE                    = local.oauth_resource
      OAUTH_SCOPES                      = join(" ", local.oauth_scopes)
      OAUTH_ALLOWED_REDIRECT_URI_EXACT  = join(",", var.oauth_allowed_redirect_uri_exact)
      OAUTH_ALLOWED_REDIRECT_URI_PREFIX = join(",", var.oauth_allowed_redirect_uri_prefixes)
      ENABLE_DCR_PROXY                  = var.enable_dcr_proxy ? "true" : "false"
      COGNITO_USER_POOL_ID              = try(aws_cognito_user_pool.mcp[0].id, "")
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.add_memory_logs,
    aws_iam_role_policy.add_memory_s3,
    aws_s3_bucket_versioning.memory,
    aws_cloudwatch_log_group.add_memory_lambda,
  ]
}

resource "aws_apigatewayv2_api" "memory_ingress" {
  name          = var.api_name
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "add_memory" {
  api_id                 = aws_apigatewayv2_api.memory_ingress.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.add_memory.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 10000
}

resource "aws_apigatewayv2_authorizer" "jwt" {
  count = var.api_authorization_type == "JWT" ? 1 : 0

  api_id           = aws_apigatewayv2_api.memory_ingress.id
  name             = "${var.api_name}-jwt"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    issuer   = local.jwt_issuer
    audience = local.jwt_audiences
  }
}

resource "aws_apigatewayv2_route" "add_memory" {
  api_id    = aws_apigatewayv2_api.memory_ingress.id
  route_key = "POST /"
  target    = "integrations/${aws_apigatewayv2_integration.add_memory.id}"

  # Switchable for dev convenience.
  authorization_type = var.api_authorization_type
  authorizer_id      = var.api_authorization_type == "JWT" ? aws_apigatewayv2_authorizer.jwt[0].id : null
  authorization_scopes = (
    var.api_authorization_type == "JWT" && length(var.jwt_authorization_scopes) > 0
    ? var.jwt_authorization_scopes
    : null
  )

  # Explicit dependency ensures Terraform updates this route (removing the
  # authorizer reference) before it attempts to destroy the authorizer when
  # switching away from JWT auth.  The ternary above drops the implicit edge.
  depends_on = [aws_apigatewayv2_authorizer.jwt]
}

resource "aws_apigatewayv2_route" "oauth_protected_resource" {
  api_id    = aws_apigatewayv2_api.memory_ingress.id
  route_key = "GET /.well-known/oauth-protected-resource"
  target    = "integrations/${aws_apigatewayv2_integration.add_memory.id}"

  authorization_type = "NONE"
}

resource "aws_apigatewayv2_route" "oauth_authorization_server" {
  api_id    = aws_apigatewayv2_api.memory_ingress.id
  route_key = "GET /.well-known/oauth-authorization-server"
  target    = "integrations/${aws_apigatewayv2_integration.add_memory.id}"

  authorization_type = "NONE"
}

resource "aws_apigatewayv2_route" "oauth_register" {
  count = var.enable_dcr_proxy ? 1 : 0

  api_id    = aws_apigatewayv2_api.memory_ingress.id
  route_key = "POST /oauth/register"
  target    = "integrations/${aws_apigatewayv2_integration.add_memory.id}"

  authorization_type = "NONE"
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

resource "aws_apigatewayv2_domain_name" "custom" {
  count = local.custom_domain_enabled ? 1 : 0

  domain_name = var.custom_domain_name

  domain_name_configuration {
    certificate_arn = var.acm_certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}

resource "aws_apigatewayv2_api_mapping" "custom" {
  count = local.custom_domain_enabled ? 1 : 0

  api_id      = aws_apigatewayv2_api.memory_ingress.id
  domain_name = aws_apigatewayv2_domain_name.custom[0].id
  stage       = aws_apigatewayv2_stage.this.id
}

resource "aws_cognito_user_pool" "mcp" {
  count = var.create_cognito_user_pool ? 1 : 0

  name = var.cognito_user_pool_name

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  admin_create_user_config {
    allow_admin_create_user_only = true
  }
}

resource "aws_cognito_user_pool_domain" "mcp" {
  count = local.cognito_domain_enabled ? 1 : 0

  domain       = var.cognito_domain_prefix
  user_pool_id = aws_cognito_user_pool.mcp[0].id
}

resource "aws_cognito_user_pool_client" "mcp" {
  count = var.create_cognito_user_pool ? 1 : 0

  name         = var.cognito_user_pool_client_name
  user_pool_id = aws_cognito_user_pool.mcp[0].id

  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  allowed_oauth_flows_user_pool_client = length(var.oauth_callback_urls) > 0
  allowed_oauth_flows                  = length(var.oauth_callback_urls) > 0 ? ["code"] : null
  allowed_oauth_scopes                 = length(var.oauth_callback_urls) > 0 ? local.oauth_scopes : null
  callback_urls                        = length(var.oauth_callback_urls) > 0 ? var.oauth_callback_urls : null
  logout_urls                          = length(var.oauth_logout_urls) > 0 ? var.oauth_logout_urls : null
  supported_identity_providers         = length(var.oauth_callback_urls) > 0 ? ["COGNITO"] : null
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
    FunctionName = aws_lambda_function.add_memory.function_name
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
    FunctionName = aws_lambda_function.add_memory.function_name
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
  function_name = aws_lambda_function.add_memory.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.memory_ingress.execution_arn}/*/*"
}
