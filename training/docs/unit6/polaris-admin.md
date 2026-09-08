# 6.10 Administer access: create users & assign RBAC

In 6.9 you *observed* the persona matrix. Now you'll *build* it — create a new
user, give it a role, grant that role access, and watch Polaris enforce it. This
is the day job of a catalog owner.

## Two kinds of identity

Governance has two halves, and Polaris keeps them separate:

| | **Authentication** — *who are you?* | **Authorization** — *what can you touch?* |
|---|---|---|
| Lives in | **Keycloak** (human users) **or** Polaris (service principals) | **Polaris** (principals, roles, grants) |
| Example | `analyst` logs in with a password / SSO | `analyst` principal holds `analyst_role` → `gold` read |

A **user never gets a grant directly.** Access always flows through a role:

```
principal ──assigned──► principal-role ──bound to──► catalog-role ──granted──► privilege on a namespace/table
 (the user)              (what they are)             (a bundle of grants)       (e.g. gold : TABLE_READ_DATA)
```

Why the extra hops? So you grant **once to a role** and reuse it for everyone who
holds it — the same reason every real catalog (UC, Snowflake) works this way.

!!! note "Admin identity"
    Creating users and roles is a **catalog-admin** action. In this training stack
    you act as the bootstrap admin **`root` / `s3cr3t`**. On a real deployment this
    would be a locked-down owner account.

## Set up your shell

All admin actions go through the Polaris **management API**. Paste these helpers
(they fetch an admin token and define `post` / `put` / `del`):

```bash
# API base — local (compose) vs k8s
B=http://localhost:8185                 # k8s: B=http://polaris.de.lan
M=$B/api/management/v1; C=$B/api/catalog/v1

# admin token (root)
RT=$(curl -s "$C/oauth/tokens" --user root:s3cr3t -H 'Polaris-Realm: POLARIS' \
      -d grant_type=client_credentials -d scope=PRINCIPAL_ROLE:ALL \
      | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
H=(-H "Authorization: Bearer $RT" -H "Content-Type: application/json" -H "Polaris-Realm: POLARIS")

post(){ curl -s "${H[@]}" -X POST "$1" -d "$2"; echo; }
put(){  curl -s "${H[@]}" -X PUT  "$1" -d "$2" -o /dev/null -w "%{http_code}\n"; }
del(){  curl -s "${H[@]}" -X DELETE "$1" -o /dev/null -w "%{http_code}\n"; }
```

## Lab A — Create a user and grant it access

We'll onboard a read-only BI user called **`intern`** and give it `gold` access —
the same shape as the `analyst` persona.

### 1 · Create the user (principal)

```bash
post "$M/principals" '{"principal":{"name":"intern"}}'
```
Polaris returns the new principal **and its credentials** — copy these; the secret
is shown **once**:
```json
{ "principal":   { "name": "intern", "clientId": "abfba421afffb419" },
  "credentials": { "clientId": "abfba421afffb419",
                   "clientSecret": "a32258af3b38b906657c72354edf2d89" } }
```
That `clientId`/`clientSecret` is how a **service/automation** logs in. (A **human**
user logs in through Keycloak instead — see Lab B.)

### 2 · Create a role and assign it to the user

```bash
post "$M/principal-roles" '{"principalRole":{"name":"intern_role"}}'
put  "$M/principals/intern/principal-roles" '{"principalRole":{"name":"intern_role"}}'   # 201
```

### 3 · Bundle the grants in a catalog-role and grant `gold` read

```bash
post "$M/catalogs/polaris_lake/catalog-roles" '{"catalogRole":{"name":"intern_cr"}}'
put  "$M/principal-roles/intern_role/catalog-roles/polaris_lake" '{"catalogRole":{"name":"intern_cr"}}'   # 201

for p in TABLE_READ_DATA TABLE_LIST; do
  put "$M/catalogs/polaris_lake/catalog-roles/intern_cr/grants" \
      "{\"grant\":{\"type\":\"namespace\",\"namespace\":[\"gold\"],\"privilege\":\"$p\"}}"   # 201
done
```

### 4 · Prove it — log in *as intern* and test

```bash
CID=abfba421afffb419; CSEC=a32258af3b38b906657c72354edf2d89   # from step 1
IT=$(curl -s "$C/oauth/tokens" --user "$CID:$CSEC" -H 'Polaris-Realm: POLARIS' \
      -d grant_type=client_credentials -d scope=PRINCIPAL_ROLE:ALL \
      | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s -o /dev/null -w "gold   %{http_code}\n" -H "Authorization: Bearer $IT" -H 'Polaris-Realm: POLARIS' "$C/polaris_lake/namespaces/gold/tables"
curl -s -o /dev/null -w "silver %{http_code}\n" -H "Authorization: Bearer $IT" -H 'Polaris-Realm: POLARIS' "$C/polaris_lake/namespaces/silver/tables"
```
```
gold   200      ← granted
silver 403      ← never granted → invisible
```
You just created a user and its access from scratch, and Polaris enforced it
immediately — on **both** Trino and Spark.

### 5 · Give the user *write* on silver (promote to engineer-like)

Add the write privileges to the **role** — every holder gets them at once:
```bash
for p in TABLE_READ_DATA TABLE_LIST TABLE_WRITE_DATA TABLE_CREATE; do
  put "$M/catalogs/polaris_lake/catalog-roles/intern_cr/grants" \
      "{\"grant\":{\"type\":\"namespace\",\"namespace\":[\"silver\"],\"privilege\":\"$p\"}}"
done
```

## Lab B — Onboard a *human* user with SSO

Service principals log in with a client secret; **people** log in through
**Keycloak**, and Polaris trusts the token. The link is two claims in the token:

- **`principal_name`** → the Polaris **principal** to act as
- **`principal_roles`** → the Polaris **principal-role(s)** to activate

So a human user needs a matching pair: a **Keycloak user** *and* a **Polaris
principal + role** of the same name.

**Names must match across the two systems** — that's the whole trick:

| Keycloak (authN) | → token claim → | Polaris (authZ) |
|---|---|---|
| username `auditor` | `principal_name` | principal `auditor` |
| realm role `auditor_role` | `principal_roles` | principal-role `auditor_role` |

To add a new persona — say an **`auditor`** with read-only `gold`:

1. **In Polaris** — create principal `auditor`, principal-role `auditor_role`,
   assign it, catalog-role + grant `gold` read (Lab A, via API **or** the Console —
   see below).
2. **In Keycloak** — create the user `auditor` and the realm role `auditor_role`,
   and assign the role to the user. The realm's mappers already emit
   `principal_name` (username) and `principal_roles` (realm roles) — no per-user
   wiring needed.

Now `auditor` logs into the **Console** (or any engine) via *Sign in with OIDC*
and sees exactly `gold`. The three built-in personas (`analyst` / `engineer` /
`lead`) are this exact pattern, pre-seeded by `common/polaris/seed-polaris.sh`.

!!! warning "Create the Polaris principal *first*"
    If the token's `principal_name` has no matching Polaris principal holding the
    claimed role, Polaris rejects the call with **401 / "principal roles not
    found"**. Do the Polaris side before the user signs in.

### Do it click-through (both UIs)

You don't have to use the API — both halves have a UI:

- **Keycloak admin console** — <http://localhost:8080> (k8s: `http://auth.de.lan/admin`),
  log in `admin` / `admin` → *Users → Add user*, set a password under *Credentials*,
  then *Role mapping → Assign role* → pick `auditor_role`.
- **Polaris Console** — <http://localhost:8189> (k8s: `polaris-console.de.lan`) →
  **Create Principal**, create/assign roles, and **Manage** a catalog role's grants
  (it does full create/revoke, not just browsing).

!!! danger "Keycloak UI changes are **not persisted** here"
    Keycloak runs in **dev mode** (`start-dev --import-realm`, ephemeral H2) with no
    data volume, so a user you create in its UI **disappears on the next restart** —
    the realm re-imports from `files/keycloak/de-stack-realm.json`. Great for a live
    demo; to make a user **permanent**, add it to that realm JSON. (Polaris, by
    contrast, persists to Postgres — Console changes survive restarts.)

## Privileges you'll grant most

| Privilege | Lets the role… | Persona that needs it |
|---|---|---|
| `TABLE_LIST` | see tables exist in a namespace | everyone with any access |
| `TABLE_READ_DATA` | read table data | analyst (gold) |
| `TABLE_WRITE_DATA` | insert/update/delete rows | engineer (silver) |
| `TABLE_CREATE` | create new tables | engineer / lead |
| `NAMESPACE_CREATE` | create namespaces | lead / owner |
| `CATALOG_MANAGE_CONTENT` | full content control | lead / owner |

Grants can target a whole **catalog**, a **namespace** (`"type":"namespace"`), or a
single **table** — narrower scope = tighter least-privilege.

## Revoking access

Remove a grant, unassign a role, or delete the user entirely — each returns `204`:
```bash
del "$M/catalogs/polaris_lake/catalog-roles/intern_cr"   # drops its grants
del "$M/principal-roles/intern_role"
del "$M/principals/intern"
```

## API vs. Console — when to use which

The Polaris **Console** (localhost:8189 / `polaris-console.de.lan`) does the full
job visually — **Create/Delete Principal**, create catalogs/namespaces, and
**Manage/Revoke** a catalog role's grants — great for one-off changes and for
*seeing* the principal → role → grant chain you built.

The **management API** (this lesson) is the choice for anything **repeatable**:
onboarding scripts, CI, and reproducible environments — which is exactly why the
stack's own `common/polaris/seed-polaris.sh` uses it. Same operations, same result;
pick the UI to explore, the API to automate.

## You can now…

- Create a **user** (principal) and read back its credentials
- Wire the full chain: **principal → principal-role → catalog-role → grant**
- Grant read vs write at **namespace** scope and see it enforced instantly
- Onboard a **human** user via Keycloak SSO (the `principal_name` / `principal_roles` link)
- **Revoke** access by dropping grants, roles, or the principal
