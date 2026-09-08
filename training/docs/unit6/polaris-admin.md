# 6.10 Create users & assign access (with the UIs)

In 6.9 you *saw* the persona matrix. Here you'll *build* it by clicking — create a
user, give it a role, grant that role access — using the **Polaris Console** and the
**Keycloak** admin console. No command line.

## Two kinds of user

| | **Service / app** | **Person (interactive)** |
|---|---|---|
| Logs in with | a Polaris **client secret** | a **password / SSO** via Keycloak |
| Created in | **Polaris Console** only | **Keycloak** (login) **+** Polaris (grants) |
| Use it for | pipelines, scripts, tools | analysts, engineers, humans |

Either way, access in Polaris always flows through a **role** — you never grant a
user directly:

```
user (principal) ─► principal-role ─► catalog-role ─► privilege on a namespace
   e.g. auditor      auditor_role       auditor_cr      gold : read
```

Open the **Polaris Console** at <http://localhost:8189> (k8s:
`http://polaris-console.de.lan`) and sign in as **`root` / `s3cr3t`** (the admin).

---

## A · A service user — all in the Polaris Console

We'll make a read-only user **`intern`** with access to `gold`.

**1 · Create the user.** Left nav **Access Control → Principals → Create Principal**.
Name it `intern`, choose **Create and generate credentials**. Polaris shows a
**Client ID** and **Client Secret** — **copy them now**, the secret is shown once
(you can **Rotate** it later). That pair is how an app logs in.

**2 · Create a role.** **Access Control → Principal Roles → Create Principal Role**,
name it `intern_role`.

**3 · Give the user the role.** Open `intern_role` → **Assigned Principals →
Grant to Principal → `intern`**. (Same thing from the principal's *Assigned
Principal Roles* tab.)

**4 · Create the grant bundle.** Go to **Catalogs → `polaris_lake` → Catalog Roles
→ Create Catalog Role**, name it `intern_cr`.

**5 · Attach the bundle to the role.** On `intern_cr` → **manage principal roles →
Grant to Principal Role → `intern_role`**.

**6 · Grant the access.** Still on `intern_cr`, add grants: pick **Namespace →
`gold`**, privilege **`TABLE_READ_DATA`**; add another for **`TABLE_LIST`** (so it
can see the tables). Save.

**Done.** `intern` now reads `gold` on both Trino and Spark. To let it also *write*
`silver`, add grants on `intern_cr` for **`silver`**: `TABLE_READ_DATA`,
`TABLE_LIST`, `TABLE_WRITE_DATA`, `TABLE_CREATE`.

!!! tip "Test without curl"
    Hand the app the Client ID/Secret, or point Trino/Spark at the catalog with
    them — the engine sees only `gold`. Reading `silver` returns *not found*.

---

## B · A person who logs in with a password (Keycloak + Polaris)

People authenticate through **Keycloak**, so you touch **both** consoles. The link
is simple: **the names must match.**

| Keycloak | → token claim → | Polaris |
|---|---|---|
| username `auditor` | `principal_name` | principal `auditor` |
| realm role `auditor_role` | `principal_roles` | principal-role `auditor_role` |

**1 · Polaris side (Console).** Do steps 1–6 from Part A for `auditor` /
`auditor_role` / `auditor_cr` with a `gold` read grant. (A human logs in via
Keycloak, so you can skip copying the client secret — it won't be used.)

**2 · Keycloak side (admin console).** Open <http://localhost:8080> (k8s:
`http://auth.de.lan/admin`), sign in **`admin` / `admin`**, pick the **`de-stack`**
realm, then:

  - **Users → Add user** → username **`auditor`** (must match the principal).
  - **Credentials → Set password** → turn **Temporary off**.
  - **Role mapping → Assign role** → select **`auditor_role`**.

**3 · Sign in as the person.** In the Polaris Console choose **Sign in with OIDC**,
log in as `auditor` / (their password). They see exactly `gold`. That's the whole
SSO pattern — and how `analyst` / `engineer` / `lead` were set up.

!!! warning "Order matters"
    Create the **Polaris** principal + role first. If a Keycloak user signs in and
    Polaris has no matching principal holding the claimed role, the login is
    rejected (**401 — principal roles not found**).

!!! danger "Keycloak users here are **temporary**"
    Keycloak runs in dev mode with no database volume, so a user you add in its UI
    is **wiped on the next restart** (the realm re-imports from
    `files/keycloak/de-stack-realm.json`). Perfect for a live demo; to make a user
    **permanent**, add it to that realm file. *Polaris* principals persist to
    Postgres — Console changes survive restarts.

---

## Privileges you'll grant most

| Privilege | Lets the role… |
|---|---|
| `TABLE_LIST` | see that tables exist |
| `TABLE_READ_DATA` | read table data |
| `TABLE_WRITE_DATA` | insert / update / delete rows |
| `TABLE_CREATE` | create new tables |
| `NAMESPACE_CREATE` | create namespaces |
| `CATALOG_MANAGE_CONTENT` | full control of a catalog's content |

Grant on a whole **catalog**, a **namespace** (as above), or a single **table** —
narrower scope = tighter least-privilege.

## Managing access later (all in the Console)

- **Change access** → add/remove grants on the **catalog role** (every holder
  updates at once).
- **Rotate a leaked secret** → the principal's **Rotate** action.
- **Remove access** → revoke the role, or **Delete Principal** to remove the user.

## Prefer to script it?

Every click above is also a REST call, so onboarding can be automated (CI,
reproducible setups). The stack's own `common/polaris/seed-polaris.sh` is a worked
example that creates the personas and grants end-to-end.

## You can now…

- Create a **service user** entirely in the Polaris Console and read back its credentials
- Build the chain **principal → principal-role → catalog-role → grant** by clicking
- Onboard a **person** across Keycloak (login) + Polaris (grants) with matching names
- Grant read vs write at namespace scope, and **rotate / revoke / delete** later
