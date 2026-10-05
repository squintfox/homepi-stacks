# Creating a new stack

A stack is a folder in this repo that defines one Docker Swarm stack, deployed through Portainer by OpenTofu. Use a kebab-case name (e.g. `remote-access`, `infra-monitor`) and use the **same name** everywhere below.

## Folder layout

```
<stack>/
  docker-compose.yml     # the swarm stack (required)
  migrate.sh             # creates /local-data folders, copies defaults (required, executable)
  tofu/main.tf           # portainer_stack resource (required)
  tofu/variables.tf      # one variable per env var passed to the stack (required)
  configtool_db.yml      # only if the stack needs its own config/secrets
  default_files/         # optional; seed config copied by migrate.sh
```

Do not create or commit `terraform.tfstate*`; they are generated on deploy.

The easiest start is to copy a small existing stack (`files/` for a secret + web app, `tools/` for no secrets) and edit the `# EDIT:` markers in `tofu/main.tf`.

## Steps

1. **docker-compose.yml**
   - Swarm syntax: use `deploy:` (not `restart:`/`container_name`). No `privileged`, `cap_add`, or `devices`.
   - Persistent data: `${HPI_LOCAL_DATA_PATH}/<service>:/path`.
   - Common env vars available: `HPI_LOCAL_DATA_PATH`, `HPI_DNS_DOMAIN`, `HPI_HTTPS_PORT`, `HPI_DESEC_TOKEN`, `HPI_APP_UID`, `HPI_APP_GID`. Any other env var must be added to `main.tf`, `variables.tf` and `configtool_db.yml` (see below).
   - Web UI behind Caddy: join the external network `webproxy-backend` and add labels on the service:
     ```yaml
     caddy: <name>.${HPI_DNS_DOMAIN}
     caddy.reverse_proxy: "{{upstreams <port>}}"
     caddy.tls.propagation_delay: 120s
     caddy.tls.dns: desec
     caddy.tls.dns.token: ${HPI_DESEC_TOKEN}
     ```
     and declare the network at the bottom: `networks: { webproxy-backend: { external: true } }`.
   - Dashboard tile: add under `deploy.labels`: `homepage.group`, `homepage.name`, `homepage.icon`, `homepage.href: https://<name>.${HPI_DNS_DOMAIN}:${HPI_HTTPS_PORT}/`.
   - Services without a UI (e.g. VPN agents) need no caddy/homepage labels or network.

2. **migrate.sh** — `set -euo pipefail`, set `STACK_NAME` and `SERVICE_FOLDERS`, `mkdir -p /local-data/$folder` for each, copy defaults with `cp -n ./default_files/* /local-data/<service>/`, echo `"$STACK_NAME: migration complete."`. `chmod +x` it. Must be idempotent.

3. **tofu/main.tf** — copy from an existing stack and change: the resource label, `name`, and `file_path_in_repository = "<stack>/docker-compose.yml"`. Add one `env { name = ... value = var.... }` block per env var the compose file uses. Keep the `lifecycle { ignore_changes = [repository_reference_name] }`.

4. **tofu/variables.tf** — declare a `variable` for every `var.*` used in `main.tf`; mark secrets `sensitive = true`.

5. **configtool_db.yml** (only when the stack has new env vars/secrets):
   ```yaml
   homepi:
     environments:
       base:
         - <stack>.default
     config:
       <stack>:
         default:
           hpi_<thing>:
             value: hpi_<thing>
             secret_namespace: homepi_secrets.vault
             env:
               - HPI_<THING>
               - TF_VAR_HPI_<THING>
   ```
   Every secret needs both the `HPI_` and `TF_VAR_HPI_` env names. The user must then populate the secret value in the vault.

6. **Register the stack** by adding `('<stack>', '<stack>', base_config),` to `stack_specs` in `/opt/homepi/homepi/homepi/load.py`, in the right group (default / recommended / optional). Comment it out to leave it disabled by default.

## Checklist

- Names match across folder, `configtool_db.yml`, `migrate.sh`, `main.tf`, `load.py`.
- Every `${HPI_*}` in the compose file is passed by an `env` block in `main.tf` and declared in `variables.tf`.
- `migrate.sh` is executable and idempotent.
- Nothing deployed or committed with real secrets; tell the user which vault secrets they need to set.
- Stacks are pulled from the `release` branch of the repo (`sync_main_to_release.ps1`), so changes only deploy after syncing.
