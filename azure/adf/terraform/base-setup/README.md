# Base setup — Azure Data Factory + ADLS Gen2 (Terraform)

Provisions an **empty Azure Data Factory** with a system-assigned managed identity and
optional **GitHub** source control. Cost: **$0** until pipelines actually run.

Creates: resource group → Data Factory (system-assigned identity) → (optional) GitHub integration.

## Use it

```bash
cd microsoft/adf/terraform/base-setup
az login
export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)   # azur-learning

cp terraform.tfvars.example terraform.tfvars   # edit git_account_name / git_repository_name
terraform init
terraform plan
terraform apply
```

Then:

```bash
terraform output adf_studio_url          # open the factory in ADF Studio
terraform output identity_principal_id   # the factory's MI (grant it roles later)
```

## Git integration

- Set `git_repository_name` (+ `git_account_name`) to enable GitHub source control; leave
  it empty to create the factory in **live mode** (author directly, no repo).
- The **repo and collaboration branch should exist** before you apply (an empty repo with a
  `main` branch is fine — ADF publishes into it).
- The first time you open the factory in **ADF Studio**, you'll be asked to **authorize
  GitHub** (OAuth) — Terraform only sets the repo pointer, not the credentials.

## Notes

- This is a separate stack from `../sql` (its own state) so you deploy/destroy them
  independently.
- The factory uses the default **AutoResolve (Azure) integration runtime** — managed and
  free until activities run. No self-hosted IR (would need a VM).
- To connect the factory to data stores, grant its **managed identity** (`identity_principal_id`)
  the right role (e.g. *Storage Blob Data Contributor*, or a SQL user) when you add those.
- `terraform destroy` removes it (an empty factory costs nothing, so you can also just leave it).
