variable "subscription_id" {
  description = "Azure subscription id. Leave empty to use ARM_SUBSCRIPTION_ID from the environment."
  type        = string
  default     = ""
}

variable "location" {
  description = "Azure region. Set in common.tfvars (shared across stacks)."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group for the Data Factory."
  type        = string
  default     = "rg-adf-dev"
}

variable "prefix" {
  description = "Static naming prefix for all resources (e.g. 'epireum'). Names are fixed (no random suffix), so must be GLOBALLY UNIQUE across Azure. Storage account becomes <prefix>dl (3-22 lowercase letters/digits, no hyphens); ADF becomes <prefix>-adf."
  type        = string
  default     = "epireum"

  validation {
    condition     = can(regex("^[a-z][a-z0-9]{2,20}$", var.prefix))
    error_message = "prefix: 3-21 lowercase letters/digits, starting with a letter (no hyphens — storage account names disallow them)."
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
