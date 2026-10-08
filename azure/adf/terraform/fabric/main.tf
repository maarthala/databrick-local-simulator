# Look up an EXISTING capacity (your free Trial) by name. We only reference it —
# we never create azurerm_fabric_capacity — so this module has no Azure bill.
data "fabric_capacity" "cap" {
  count        = var.capacity_display_name != "" ? 1 : 0
  display_name = var.capacity_display_name
}

# The workspace — the one thing you destroy/recreate to keep things clean.
resource "fabric_workspace" "ws" {
  display_name = var.workspace_display_name
  description  = var.workspace_description

  # Bind to the trial capacity when provided (required to host Fabric items).
  capacity_id                    = var.capacity_display_name != "" ? data.fabric_capacity.cap[0].id : null
  skip_capacity_state_validation = var.skip_capacity_state_validation
}

# A Lakehouse inside it (free on the trial capacity). Only when a capacity is set.
resource "fabric_lakehouse" "lh" {
  count        = var.create_lakehouse && var.capacity_display_name != "" ? 1 : 0
  workspace_id = fabric_workspace.ws.id
  display_name = var.lakehouse_display_name
  description  = "Created by Terraform — ephemeral."

  configuration = {
    enable_schemas = var.lakehouse_enable_schemas
  }
}

# --- Git integration (GitHub) ----------------------------------------------
# Fabric only accepts GitHub through a "configured connection": a cloud
# connection holding a GitHub PAT. The token is a write-only attribute, so it is
# sent to Fabric but never written to terraform.tfstate.
locals {
  git_enabled = var.enable_git && var.capacity_display_name != ""
}

resource "fabric_connection" "github" {
  count             = local.git_enabled ? 1 : 0
  display_name      = "${var.workspace_display_name}-github"
  connectivity_type = "ShareableCloud"
  privacy_level     = "Organizational"

  connection_details = {
    type            = "GitHubSourceControl"
    creation_method = "GitHubSourceControl.Contents"
    parameters = [{
      name  = "url"
      value = "https://github.com/${var.git_account_name}/${var.git_repository_name}"
    }]
  }

  credential_details = {
    credential_type = "Key"
    key_credentials = {
      key_wo         = var.github_token
      key_wo_version = var.github_token_version
    }
  }
}

# Connect the workspace to the repo folder. PreferWorkspace = the workspace's
# current items (e.g. the lakehouse) win on first sync and get committed.
resource "fabric_workspace_git" "ws" {
  count                   = local.git_enabled ? 1 : 0
  workspace_id            = fabric_workspace.ws.id
  initialization_strategy = var.git_initialization_strategy

  git_provider_details = {
    git_provider_type = "GitHub"
    owner_name        = var.git_account_name
    repository_name   = var.git_repository_name
    branch_name       = var.git_branch_name
    directory_name    = var.fabric_git_directory
  }

  git_credentials = {
    source        = "ConfiguredConnection"
    connection_id = fabric_connection.github[0].id
  }

  depends_on = [fabric_lakehouse.lh]
}
