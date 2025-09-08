variable "launchdarkly_access_token" {
  description = "LaunchDarkly API access token with write permissions"
  type        = string
  sensitive   = true
}

variable "project_key" {
  description = "LaunchDarkly project key"
  type        = string
}

variable "environment_key" {
  description = "LaunchDarkly environment key"
  type        = string
}

// No longer needed: flags are explicitly defined in main.tf


