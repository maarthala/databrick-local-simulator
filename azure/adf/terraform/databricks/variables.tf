variable "subscription_id" {
  description = "Azure subscription id. Leave empty to use ARM_SUBSCRIPTION_ID from the environment."
  type        = string
  default     = ""
}

variable "prefix" {
  description = "Naming prefix (shared via common.tfvars). Workspace becomes <prefix>-dbw."
  type        = string
}

variable "location" {
  description = "Azure region (shared via common.tfvars)."
  type        = string
}

variable "resource_group_name" {
  description = "Shared resource group (created by base-setup)."
  type        = string
}

variable "warehouse_size" {
  description = "SQL warehouse t-shirt size. '2X-Small' is the smallest / cheapest."
  type        = string
  default     = "2X-Small"
}

variable "auto_stop_mins" {
  description = "Idle minutes before the warehouse auto-stops (then costs nothing). Lower = cheaper. Serverless min is 5."
  type        = number
  default     = 5
}

variable "serverless" {
  description = "Use serverless SQL (starts in seconds, no separate VM bill, best for tiny sporadic loads)."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
  default = {
    environment = "dev"
    project     = "adf-training"
    managed_by  = "terraform"
  }
}
