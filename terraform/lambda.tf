resource "aws_lambda_function" "hello" {
  function_name    = "${var.name_prefix}-hello"
  description      = "Publish Hello, world! to the manually subscribed SNS topic."
  role             = aws_iam_role.lambda.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.14"
  architectures    = ["arm64"]
  memory_size      = 128
  timeout          = 10
  filename         = "${path.module}/../build/lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/../build/lambda.zip")
  environment {
    variables = { SNS_TOPIC_ARN = aws_sns_topic.notifications.arn }
  }
  depends_on = [aws_iam_role_policy.lambda, aws_cloudwatch_log_group.lambda]
}

resource "aws_lambda_function_event_invoke_config" "hello" {
  function_name                = aws_lambda_function.hello.function_name
  maximum_event_age_in_seconds = 300
  maximum_retry_attempts       = 2
}
