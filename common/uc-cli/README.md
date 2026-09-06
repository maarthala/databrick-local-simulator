# Unity Catalog CLI — per-user access with Keycloak

The `uc` CLI on your Mac authenticates against **Keycloak** (`auth.de.lan`) and talks
to the Unity Catalog server over its **NodePort** (`uc.de.lan:30808` — the nginx
ingress mangles chunked responses that the CLI's HTTP client rejects).

## One-time setup

```bash
brew install unitycatalog        # provides the `uc` CLI
```

DNS: `auth.de.lan` and `uc.de.lan` resolve to the node via the Pi-hole `*.de.lan`
wildcard. Confirm with `curl -s http://auth.de.lan/realms/de-stack/.well-known/openid-configuration`.

## Login (use the helper)

> **The `uc auth login` command is broken in Homebrew `uc` 0.6.0** — both the
> browser and `--identity_token` paths throw `NoSuchMethodError:
> OAuth*Form.toUrlQueryString()` (missing from `controlapi-0.6.0.jar`). So we do
> the OIDC exchange with `curl` via `login.sh` and use `uc --auth_token` for the
> rest. `etc/conf/server.properties` here is only for a future fixed CLI.

```bash
export T=$(common/uc-cli/login.sh analyst)          # sign in as analyst (password=analyst)
uc --server http://uc.de.lan:30808 --auth_token "$T" catalog list

export T=$(common/uc-cli/login.sh engineer bobsecret)  # explicit password
```

Convenience wrapper (add to `~/.zshrc`):

```bash
uca() { command uc --server http://uc.de.lan:30808 --auth_token "$T" "$@"; }
# export T=$(~/.../common/uc-cli/login.sh analyst); uca catalog list
```

`login.sh` = Keycloak password grant → id_token → UC token-exchange (`POST
/api/1.0/unity-control/auth/tokens`). Override `KC_URL` / `UC_URL` /
`UC_CLIENT_ID` / `UC_CLIENT_SECRET` via env if needed.

## Admin token

The metastore-admin token (bypasses external auth) is generated in the pod:

```bash
kubectl -n de-stack exec deploy/unity-catalog -- cat etc/conf/token.txt
```

Use it to manage users and grants:

```bash
uc --server http://uc.de.lan:30808 --auth_token "$ADMIN" user list
uc --server http://uc.de.lan:30808 --auth_token "$ADMIN" permission create \
   --securable_type catalog --name lakehouse --privilege "USE CATALOG" \
   --principal analyst@dev-epireum.com
```

## Users & mapping

Keycloak users (realm `de-stack`, defined in
`k8s/helm/de-stack/files/keycloak/de-stack-realm.json`) map to UC users by **email**:

| Keycloak login | email (UC principal)      | password | role |
|----------------|---------------------------|----------|------|
| analyst        | analyst@dev-epireum.com   | analyst  | reads Gold |
| engineer       | engineer@dev-epireum.com  | engineer | builds Silver, reads Gold |
| lead           | lead@dev-epireum.com      | lead     | full access (owner) |

Grants target the email. To add a user: add them to the realm JSON **and**
`uc user create --name <n> --email <email>`, then grant privileges.

> Roles/groups are not modeled in Unity Catalog OSS — grant per user. (Deferred.)
