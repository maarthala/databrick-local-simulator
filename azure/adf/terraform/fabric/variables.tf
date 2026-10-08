variable "tenant_id" {
  type        = string
  default     = ""
  description = "Entra tenant ID. Optional — inferred from your az login if empty."
}

variable "workspace_display_name" {
  type        = string
  default     = "learn-fabric-ws"
  description = "Display name for the Fabric workspace to create."
}

variable "workspace_description" {
  type        = string
  default     = "Ephemeral learning workspace — safe to destroy and recreate."
  description = "Workspace description."
}

variable "capacity_display_name" {
  type        = string
  default     = ""
  description = <<-EOT
    Display name of an EXISTING Fabric capacity to bind the workspace to — e.g.
    your free Trial capacity. Leave "" to create the workspace with no capacity
    (you can assign one later in the portal). A capacity IS required to create a
    Lakehouse. Find the name in the Fabric portal: your workspace → Settings →
    "License info"/capacity, or Admin portal → Capacity settings (trial shows as
    something like "Trial-...").
  EOT
}

variable "create_lakehouse" {
  type        = bool
  default     = true
  description = "Create a Lakehouse in the workspace (requires a capacity)."
}

variable "lakehouse_display_name" {
  type        = string
  default     = "bronze_lh"
  description = "Lakehouse display name."
}

variable "lakehouse_enable_schemas" {
  type        = bool
  default     = true
  description = "Create the lakehouse with schema support (schema-enabled Delta)."
}

variable "skip_capacity_state_validation" {
  type        = bool
  default     = true
  description = "Trial capacities can report a state that fails validation; skip it."
}

# --- Git integration (GitHub). Off by default; needs a capacity. ------------
# The repo settings reuse the git_* names from common.tfvars (shared with ADF);
# Fabric gets its own folder so it never mixes with ADF's /adf JSON.
variable "enable_git" {
  type        = bool
  default     = false
  description = "Connect the workspace to GitHub (requires capacity_display_name and github_token)."
}

variable "git_account_name" {
  type        = string
  default     = "maarthala"
  description = "GitHub owner (user or org) of the repo."
}

variable "git_repository_name" {
  type        = string
  default     = "azure-learning"
  description = "GitHub repository the workspace syncs with."
}

variable "git_branch_name" {
  type        = string
  default     = "main"
  description = "Branch the workspace syncs with."
}

variable "fabric_git_directory" {
  type        = string
  default     = "/fabric"
  description = "Folder in the repo for Fabric items (must start with '/')."
}

variable "git_initialization_strategy" {
  type        = string
  default     = "PreferWorkspace"
  description = "On first connect: PreferWorkspace (workspace wins) or PreferRemote (repo wins)."

  validation {
    condition     = contains(["PreferWorkspace", "PreferRemote"], var.git_initialization_strategy)
    error_message = "git_initialization_strategy must be PreferWorkspace or PreferRemote."
  }
}

variable "github_token" {
  type        = string
  default     = null
  sensitive   = true
  ephemeral   = true
  description = <<-EOT
    GitHub fine-grained PAT with Contents: Read and write on the repo. Pass it via
    the environment (export TF_VAR_github_token=...), never in a tfvars file.
    Write-only: it is never stored in terraform.tfstate.
  EOT
}

variable "github_token_version" {
  type        = number
  default     = 1
  description = "Bump this to push a new github_token to the existing connection."
}
