# 0.3 Personas & roles

You **don't create users** to get started — you *act as* one of three fixed **personas** that already
exist in the stack. Each persona is a real **Polaris principal** (a login with a client ID + secret)
mapped to a real set of **grants** — so when you sign in as one, you see exactly what that role is
allowed to see. That's the whole point: you *experience* governance from inside a role, the way a
real teammate would. (Creating your *own* users is Unit 6.2.)

!!! tip "Username = role, on purpose"
    In a real company people have names and get permissions through their *role*. Here we make the
    login **be** the role (`analyst`, `engineer`, `lead`) so it's always obvious who you are and what
    you can do.

## The three personas

| Login (Client ID) | Secret | Role | Can do |
|---|---|---|---|
| `analyst` | `analyst` | Analyst / BI | **Read the 🥇 Gold layer** — the finished, business-ready marts. Nothing else. |
| `engineer` | `engineer` | Data Engineer | **Build in 🥈 Silver** (read/write/create tables) and **read Gold**. Cannot touch raw Bronze. |
| `lead` | `lead` | Data Lead / Owner | **Full access to every layer** — Bronze, Silver, Gold. The owner who can also grant to others. |

The secret is the same as the login for every persona.

```mermaid
flowchart TB
  subgraph L["🥉 Bronze (raw)"]
  end
  subgraph S["🥈 Silver (clean)"]
  end
  subgraph G["🥇 Gold (marts)"]
  end
  A([analyst]) --> G
  E([engineer]) --> S
  E --> G
  D([lead]) --> L
  D --> S
  D --> G
  style G fill:#fff3cd
  style S fill:#e2e3e5
  style L fill:#f8d7da
```

This is the **medallion access policy** — least privilege by layer. An analyst can't see half-cleaned
Silver or raw Bronze; an engineer can build Silver but can't rummage in raw Bronze; only the lead
sees everything. You'll see and build these exact grants in
[Unit 6 — Data governance](../unit6/polaris.md).

## How to "become" a persona

Sign in with the persona's **Client ID + Secret** wherever the stack asks *who you are*:

- **Polaris Console** — open <http://localhost:8189> (k8s: `http://polaris-console.de.lan`), enter the
  **Client ID** and **Client Secret** (e.g. `analyst` / `analyst`), and sign in. The catalog tree you
  see is scoped to that persona's grants.
- **An engine (Trino / Spark)** — point it at the governed catalog with the same client ID/secret;
  it reads/writes only what that persona is allowed.

No identity server, no browser redirect, no hosts entry — the principal authenticates to Polaris
directly.

## These are *not* personas — they're platform/ops accounts

The other logins around the stack are **service accounts** for running the platform, not learner
roles. Don't confuse them with the personas above:

| Account | Where | What it is |
|---|---|---|
| `root` / `s3cr3t` | Polaris (Console or API) | Catalog **admin** — creates catalogs, users, roles & grants |
| `admin` / `admin` | Superset | BI tool admin (Superset has its own users) |
| `airflow` / `airflow` | Airflow | Orchestrator admin |
| token `123456` | Jupyter | Notebook access |
| `minioadmin` / `minioadmin` | MinIO | Object-store root |

The personas (`analyst`/`engineer`/`lead`) are the ones that carry a **data-access role**; the table
above is just how you open each tool.

## Where the personas are defined (for the curious)

Both identity *and* permissions come from one operator seed script,
`common/polaris/seed-polaris.sh` (compose: `make polaris-seed`; k8s: run inside the polaris pod). It
creates the three principals, pins their logins (client ID = secret = name), and applies the graded
grants. Change the personas or their access there — it's idempotent and safe to re-run.

!!! note "On the cloud, this is users + groups + an IdP"
    On Databricks/Snowflake you'd create *people*, attach them to **groups** (`analysts`,
    `engineers`) that hold the grants, and log in via an identity provider (SSO/MFA). Here we skip the
    IdP and give each role a direct principal login — simpler for training, and the mental model
    (identity → role → grants → least privilege) is identical.

## You can now…
- Name the three personas, their logins, and what each is allowed to read/write
- Sign in as a persona in the **Polaris Console** (or an engine) with its client ID/secret
- Tell a **data-access persona** apart from a **platform/ops service account**
