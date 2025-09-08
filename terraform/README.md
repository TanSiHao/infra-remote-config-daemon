# Terraform: LaunchDarkly demo flags

Creates three string-variation flags whose keys match the Python daemon's env keys, with explicit variation names and URLs.

## Prereqs

- Terraform >= 1.4
- LaunchDarkly access token with write permissions

## Variables

- `launchdarkly_access_token` (sensitive): API token
- `project_key`: LaunchDarkly project key
- `environment_key`: LaunchDarkly environment key

## Example usage

Create a `terraform.tfvars`:

```hcl
launchdarkly_access_token = "ldapi-xxxx..."
project_key               = "default"
environment_key           = "production"
```

Then run:

```bash
terraform init
terraform plan -out tfplan
terraform apply tfplan
```

Flags will be created with variations:

- default: https://api-default.example.com
- v1: https://api-v1.example.com
- v2: https://api-v2.example.com


