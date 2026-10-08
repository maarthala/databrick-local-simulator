output "workspace_id" {
  value       = fabric_workspace.ws.id
  description = "GUID of the created Fabric workspace."
}

output "workspace_name" {
  value       = fabric_workspace.ws.display_name
  description = "Display name of the created workspace."
}

output "capacity" {
  value = var.capacity_display_name != "" ? {
    id    = data.fabric_capacity.cap[0].id
    sku   = data.fabric_capacity.cap[0].sku
    state = data.fabric_capacity.cap[0].state
  } : null
  description = "The existing (trial) capacity the workspace is bound to, if any."
}

output "lakehouse_id" {
  value       = var.create_lakehouse && var.capacity_display_name != "" ? fabric_lakehouse.lh[0].id : null
  description = "GUID of the created Lakehouse, if any."
}

output "git" {
  value = local.git_enabled ? {
    connection_id = fabric_connection.github[0].id
    state         = fabric_workspace_git.ws[0].git_connection_state
    repo          = "${var.git_account_name}/${var.git_repository_name}@${var.git_branch_name}${var.fabric_git_directory}"
  } : null
  description = "GitHub connection of the workspace, if enabled."
}
