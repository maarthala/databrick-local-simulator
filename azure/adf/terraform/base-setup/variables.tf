variable "subscription_id" {
  description = "Azure subscription id. Leave empty to use ARM_SUBSCRIPTION_ID from the environment."
  type        = string
  default     = ""
}

variable "location" {
  description = "Azure region."
  type        = string
  default     = "northeurope"
}

variable "resource_group_name" {
  description = "Resource group for the Data Factory."
  type        = string
  default     = "rg-adf-dev"
}

variable "name_prefix" {
  description = "Prefix for the factory name (a random suffix is added — ADF names are globally unique)."
  type        = string
  default     = "adfdev"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,20}$", var.name_prefix))
    error_message = "name_prefix: lowercase letters/digits/hyphen, start with a letter."
  }
}

# --- Git integration (GitHub). Leave git_repository_name empty to create the factory
# --- without Git (live mode); set it to enable Git source control on the factory.
variable "git_account_name" {
  description = "GitHub organization or username that owns the ADF repo."
  type        = string
  default     = "maarthala"
}

variable "git_repository_name" {
  description = "GitHub repository holding the ADF resources. Empty = no Git integration."
  type        = string
  default     = "azure-learning"
}

variable "git_branch_name" {
  description = "Collaboration branch."
  type        = string
  default     = "main"
}

variable "git_root_folder" {
  description = "Folder in the repo where ADF stores its JSON."
  type        = string
  default     = "/adf"
}

# --- ADLS Gen2 data lake (base stack) ---------------------------------------
variable "storage_name_prefix" {
  description = "Prefix for the ADLS Gen2 storage account name (lowercase letters/digits; a random suffix is appended)."
  type        = string
  default     = "adfdevdl"

  validation {
    condition     = can(regex("^[a-z0-9]{3,17}$", var.storage_name_prefix))
    error_message = "storage_name_prefix: 3-17 lowercase letters/digits only."
  }
}

variable "replication_type" {
  description = "Storage replication (LRS is cheapest)."
  type        = string
  default     = "LRS"
}

variable "filesystems" {
  description = "ADLS Gen2 file systems (containers) to create."
  type        = list(string)
  default     = ["landing"]
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
