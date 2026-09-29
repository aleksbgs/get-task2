variable "account_id" {
  description = "AWS account authorized to receive the deployment."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Provide a 12-digit AWS account ID."
  }
}

variable "region" {
  type    = string
  default = "eu-central-1"
}

variable "name_prefix" {
  type    = string
  default = "get-task2"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,29}$", var.name_prefix))
    error_message = "Use 2-30 lowercase letters, digits or hyphens, starting with a letter."
  }
}

variable "schedule_timezone" {
  description = "IANA time zone used for the daily 01:00 schedule."
  type        = string
  default     = "Europe/Belgrade"
}

variable "schedule_enabled" {
  description = "Disable to stop daily invocations without deleting the lab."
  type        = bool
  default     = true
}
