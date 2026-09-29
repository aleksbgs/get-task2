resource "aws_sns_topic" "notifications" {
  name         = "${var.name_prefix}-notifications"
  display_name = "GET Task 2"
  fifo_topic   = false
}

# Email subscriptions are created and confirmed manually, as required by the task.
