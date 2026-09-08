# 6.7 A day in the governed lakehouse

## Concept
Units 6.1–6.6 taught the *mechanics*. This lesson shows the **payoff**: three people at ShopFlow, one
Unity Catalog, and how the **same catalog gives each of them a different view** — automatically,
without anyone configuring three separate tools.

Meet the team (your personas — password = username):

| Person | Role | What they need |
|---|---|---|
| **Ava** (`analyst`) | BI / analytics | read the finished business marts |
| **Eddie** (`engineer`) | data engineering | build the pipeline, read raw-ish + finished |
| **Lena** (`lead`) | data lead / owner | everything, including raw data with PII |

And the policy Lena set once (the **medallion access policy**):

```
shopflow (catalog)
├── bronze   raw ingest (contains customer PII)   → lead only
├── silver   cleaned & joined                     → engineer + lead
└── gold     business marts (safe, aggregated)    → everyone
```

## The scenario

### 09:00 — Ava (analyst) builds a sales dashboard
She needs `daily_sales`. She logs in and looks at what she can see:

```bash
UC=http://localhost:8081
T=$(common/uc-cli/login.sh analyst)
uc --server $UC --auth_token "$T" schema list --catalog shopflow
```
✅ **She sees `gold` — and only `gold`.**

```
gold
```
`silver` and `bronze` aren't just locked — they're **invisible**. Ava never even learns the raw
customer table exists, so there's no PII she could accidentally query. She builds her dashboard on
`gold.daily_sales` and moves on. **No ticket, no Slack question, no risk.**

### 10:30 — Eddie (engineer) fixes the Silver join
A bug in the orders-to-customers join. Eddie needs to read and rebuild **silver**:

```bash
T=$(common/uc-cli/login.sh engineer)
uc --server $UC --auth_token "$T" schema list --catalog shopflow
```
✅ **He sees `silver` *and* `gold`:**

```
gold
silver
```
He has `CREATE TABLE` on silver (so he can rebuild it) and read on gold (to check downstream marts).
But **`bronze` — the raw data with untouched PII — is invisible to him too.** Engineers transform
data; they don't need the raw PII sitting in bronze. Least privilege, enforced.

### 14:00 — Lena (lead) investigates a data-quality issue
A customer complaint traces back to bad raw data. Lena needs the **raw** record — PII and all:

```bash
T=$(common/uc-cli/login.sh lead)
uc --server $UC --auth_token "$T" schema list --catalog shopflow
```
✅ **She sees everything:**

```
bronze
gold
silver
```
Only Lena can open `bronze`. She's also the one who *grants* access — a persona who tries to create a
catalog or hand out a grant gets **`403 PERMISSION_DENIED`** (that's [6.4](create-assign.md)). Governance
authority is itself governed.

## What just happened (the whole point)
One catalog. One policy, written once. **Three completely different, safe experiences** — and nobody
configured Ava's tool, Eddie's tool, and Lena's tool separately. That's the job Unity Catalog does:

| Without a catalog | With Unity Catalog |
|---|---|
| "which table is the real one?" in Slack | Ava searches, finds `gold.daily_sales` |
| PII lockdown configured per-tool, drifts | one grant, `bronze` invisible to non-leads |
| finance vs dashboard numbers disagree | everyone reads the same `gold` marts |
| "who saw PII last quarter?" — no answer | every access recorded |

## Where this is enforced (and the good news)
The visibility above is Unity Catalog enforcing grants. And on this stack it's not just *visibility* —
**Spark now enforces it at query time**: querying the governed `lakehouse` catalog through UC, Ava's
read of `silver`/`bronze` is refused **by the engine itself**, per her token (see
[6.8](governed-spark.md)). **Trino** still reads the open `iceberg` catalog directly (ungoverned) —
that's the SQL/BI path (Units 2 & 7).

On **Databricks / Snowflake / Fabric**, *every* engine goes through the catalog before returning a row;
here **Spark does and Trino doesn't (yet)** — but the **policy you wrote is identical**, so it transfers
100%.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **Medallion access policy** | bronze=lead, silver=engineer+lead, gold=everyone — least privilege per layer |
| **Invisible vs denied** | without `USE SCHEMA`, a schema doesn't even appear — you can't leak what you can't see |
| **Least privilege** | each role gets exactly what its job needs, nothing more |
| **Governed governance** | only admins/owners can grant — personas get `403` |

## You can now…
- Explain, with a concrete story, **what Unity Catalog is for**: one policy → many safe, role-scoped views
- Show the medallion access policy in action across `analyst` / `engineer` / `lead`
- Articulate what transfers to Databricks (the policy) and what the cloud adds (engine-level enforcement)
