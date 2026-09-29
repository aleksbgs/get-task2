resource "aws_scheduler_schedule_group" "daily" {
  name = var.name_prefix
}

resource "aws_scheduler_schedule" "daily" {
  name                         = "${var.name_prefix}-daily-0100"
  group_name                   = aws_scheduler_schedule_group.daily.name
  description                  = "Run the Task 2 Lambda daily at 01:00 local time."
  schedule_expression          = "cron(0 1 * * ? *)"
  schedule_expression_timezone = var.schedule_timezone
  state                        = var.schedule_enabled ? "ENABLED" : "DISABLED"
  flexible_time_window { mode = "OFF" }
  target {
    arn      = aws_lambda_function.hello.arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ source = "daily-schedule" })
    retry_policy {
      maximum_event_age_in_seconds = 300
      maximum_retry_attempts       = 2
    }
  }
  depends_on = [aws_iam_role_policy.scheduler, aws_lambda_function_event_invoke_config.hello]
}
