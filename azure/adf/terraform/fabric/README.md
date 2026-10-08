# Fabric — ephemeral workspace (free)

Creates a **Microsoft Fabric workspace** (and optionally a **Lakehouse**) on your
**existing free Trial capacity**. It deliberately does **not** create a paid
`azurerm_fabric_capacity`, so `apply` / `destroy` costs nothing — spin it up to
learn, tear it down when done.

## Why this is free
The only billable Fabric resource is a **capacity** (F-SKU). This module never
creates one — it *references* your **Trial** capacity by name and puts a
workspace + lakehouse on it. Workspaces and items don't bill; they consume the
trial capacity's CUs (free for the 60-day trial).

## Prerequisites
- A **Fabric Trial** active in your tenant (portal → Account manager → *Start trial*).
- **Terraform ≥ 1.11** and **Azure CLI**; run `az login` (the provider uses that identity).
- You must be a member/admin of the tenant's Fabric with rights to create workspaces.

## Use
```bash
cd azure/adf/terraform/fabric

# find your trial capacity name: Fabric portal → workspace → Settings (license/capacity),
# or Admin portal → Capacity settings (often "Trial-xxxx").

terraform init
terraform apply -var-file=../common.tfvars \
                -var 'workspace_display_name=learn-fabric-ws'

# ... learn ...

terraform destroy -var-file=../common.tfvars
```
Leave `capacity_display_name` empty to create the workspace with **no** capacity
(you can assign one in the portal), but then a Lakehouse can't be created.

## What it makes
| Resource | Free? | Notes |
|---|---|---|
| `fabric_workspace` | ✅ | bound to your trial capacity |
| `fabric_lakehouse` | ✅ | schema-enabled Delta; toggle with `create_lakehouse` |
| `fabric_connection` + `fabric_workspace_git` | ✅ | GitHub sync, only when `enable_git = true` |
| *(capacity)* | — | **not created** — referenced only, so no bill |

## Git integration (GitHub)
Off by default. When on, the workspace syncs with
`<git_account_name>/<git_repository_name>` on `git_branch_name`, in the folder
`fabric_git_directory` (default `/fabric`, kept apart from ADF's `/adf`).

1. Create a GitHub **fine-grained PAT** for that repo with *Contents: Read and write*.
2. Pass it through the environment, never a tfvars file:
   ```bash
   export TF_VAR_github_token=github_pat_xxx
   terraform apply -var-file=../common.tfvars -var enable_git=true
   ```
The token is a **write-only** attribute: Fabric gets it, `terraform.tfstate` never does.
To rotate it, export the new token and bump `github_token_version`.

On first connect `git_initialization_strategy = "PreferWorkspace"` commits the
workspace's items (the lakehouse) to the repo; use `PreferRemote` to load the repo
into the workspace instead. Needs a capacity (`capacity_display_name`).

## Variables (common)
- `capacity_display_name` — existing trial capacity to bind to (required for a lakehouse)
- `workspace_display_name` / `workspace_description`
- `create_lakehouse` (default `true`), `lakehouse_display_name`, `lakehouse_enable_schemas`
- `enable_git` (default `false`), `git_account_name`, `git_repository_name`, `git_branch_name`, `fabric_git_directory`, `git_initialization_strategy`, `github_token` (env only)
- `skip_capacity_state_validation` (default `true`) — trial capacities can fail state validation

## Notes
- Uses the official **`microsoft/fabric`** provider (Fabric content) — not `azurerm`.
- `terraform destroy` removes the workspace + lakehouse cleanly. Nothing lingers to bill.
- For CI/service-principal auth, enable the tenant setting **"Service principals can use Fabric APIs"** and set the `FABRIC_*`/`ARM_*` env vars.
