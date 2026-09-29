variables { account_id = "123456789012" }

mock_provider "aws" {
  mock_resource "aws_iam_role" {
    defaults = { arn = "arn:aws:iam::123456789012:role/mock-role" }
  }
  mock_resource "aws_sns_topic" {
    defaults = { arn = "arn:aws:sns:eu-central-1:123456789012:mock-topic" }
  }
  mock_resource "aws_lambda_function" {
    defaults = { arn = "arn:aws:lambda:eu-central-1:123456789012:function:mock-function" }
  }
  mock_resource "aws_cloudwatch_log_group" {
    defaults = { arn = "arn:aws:logs:eu-central-1:123456789012:log-group:mock-logs" }
  }
  mock_resource "aws_scheduler_schedule_group" {
    defaults = { arn = "arn:aws:scheduler:eu-central-1:123456789012:schedule-group/mock-group" }
  }
}

run "daily_notification_contract" {
  command = apply # Mocked provider: this never calls AWS.
  assert {
    condition     = aws_scheduler_schedule.daily.schedule_expression == "cron(0 1 * * ? *)" && aws_scheduler_schedule.daily.schedule_expression_timezone == "Europe/Belgrade" && aws_scheduler_schedule.daily.flexible_time_window[0].mode == "OFF"
    error_message = "The schedule must run daily at 01:00 Belgrade time without a flexible window."
  }
  assert {
    condition     = !aws_sns_topic.notifications.fifo_topic && aws_lambda_function.hello.runtime == "python3.14" && aws_lambda_function.hello.timeout == 10 && aws_cloudwatch_log_group.lambda.retention_in_days == 7
    error_message = "Email needs a Standard SNS topic; Lambda and logging must use the lab defaults."
  }
  assert {
    condition     = jsondecode(aws_iam_role_policy.lambda.policy).Statement[0].Action == ["sns:Publish"] && jsondecode(aws_iam_role_policy.scheduler.policy).Statement[0].Action == ["lambda:InvokeFunction"]
    error_message = "The Lambda and Scheduler roles must have separate, restricted permissions."
  }
  assert {
    condition     = jsondecode(aws_iam_role_policy.lambda.policy).Statement[0].Resource == aws_sns_topic.notifications.arn && jsondecode(aws_iam_role_policy.scheduler.policy).Statement[0].Resource == aws_lambda_function.hello.arn && jsondecode(aws_iam_role.scheduler.assume_role_policy).Statement[0].Condition.StringEquals["aws:SourceArn"] == aws_scheduler_schedule_group.daily.arn
    error_message = "IAM must restrict publishing, invoking and role assumption to the lab resources."
  }
  assert {
    condition     = aws_scheduler_schedule.daily.target[0].arn == aws_lambda_function.hello.arn && aws_lambda_function.hello.environment[0].variables["SNS_TOPIC_ARN"] == aws_sns_topic.notifications.arn
    error_message = "The schedule must invoke Lambda, and Lambda must publish to the expected SNS topic."
  }
}

run "disable_daily_delivery" {
  command = plan
  variables { schedule_enabled = false }
  assert {
    condition     = aws_scheduler_schedule.daily.state == "DISABLED"
    error_message = "The daily schedule must be switchable without deleting resources."
  }
}
