# 6.3 Discovery & search

## Concept
You've built the pipeline ([Unit 4](../unit4/spark-sql-gold.md)), scheduled it
([Unit 5](../unit5/basics.md)), and defined an access policy ([6.2](rbac.md)). The last job of a
catalog is **discovery**: letting people *find* trustworthy data themselves instead of pinging the
data team on Slack. A governed catalog turns *"where is the orders data and can I trust it?"* into
a two-minute self-service browse.

Good discovery answers four questions for every dataset:

```mermaid
flowchart LR
  U([Analyst]) --> Q{What do I need?}
  Q --> W["🔎 What exists?<br/>catalogs / schemas / tables"]
  Q --> C["🧬 What's in it?<br/>columns, types, comments"]
  Q --> O["👤 Who owns it?<br/>owner + metadata"]
  Q --> T["🔒 Can I read it?<br/>my grants (6.2)"]
```

Discovery and governance are two sides of one coin: the catalog is the single place that records
*what exists* **and** *who may see it*.

!!! info "Why discovery matters in a real org"
    In a small project you know every table by heart. In a company with hundreds of teams, **nobody
    knows every table** — data lives in dozens of catalogs and schemas that other people built. When
    you need "the orders data," you shouldn't have to guess a name or ping a stranger on Slack. A
    governed **catalog** is the searchable index of the whole data estate: it lets you *find* a
    dataset, read its description, and see **who owns it** so you know whether to trust it. That's
    what **discovery** (also called **data discovery** or **search**) means — self-service finding
    of trustworthy data.

!!! note "Two ways to explore: the Web UI vs the `uc` CLI"
    You'll do the exact same exploration two ways in this lab:

    - **The Unity Catalog Web UI** — a point-and-click browser. Best for humans exploring: click a
      catalog, see its schemas, click a table, read its columns and owner in a panel.
    - **The `uc` CLI** — the same catalog queried from the command line (`uc catalog list`,
      `uc schema list`, `uc table get`, …). Best for **scripting** — e.g. generating a data
      inventory, or checking metadata inside a pipeline. No browser, no container shell needed.

    Same catalog underneath, two front doors. Pick whichever fits the moment.

## Lab

### Browse in the Web UI
Open the Unity Catalog Web UI at <http://localhost:3000> and sign in as **`analyst` / `analyst`**
(Keycloak SSO; the browser redirect needs `127.0.0.1 keycloak` in `/etc/hosts`).

1. Click **`shopflow`** → the schemas `bronze`, `silver`, `gold`.
2. Open **`gold`** → its marts.
3. Click a table → inspect the **columns**, **owner**, and **metadata**.

**Read it step by step:**

- **Step 1 — pick a catalog.** `shopflow` is a **catalog**: the top-level container. Opening it
  reveals its **schemas** — the folders `bronze`, `silver`, `gold` that group related tables (the
  medallion layers from [Unit 1](../unit1/medallion.md)).
- **Step 2 — pick a schema.** `gold` holds the analyst-facing **marts** (the business tables built
  in [Unit 4](../unit4/spark-sql-gold.md)). Opening a schema lists the tables inside it.
- **Step 3 — inspect a table.** Clicking a table shows its **metadata**: the **columns** and their
  types (the table's *shape*), any **comments** describing what a field means, and the **owner** —
  the person or team accountable for it. Metadata is "data about the data": it tells you what's in
  the table and whether you can trust it *without* querying a single row.

!!! tip "What to look for — and what it tells you"
    The **owner** answers "who do I ask if this looks wrong?" The **columns + comments** answer
    "does this table actually have what I need?" On cloud Unity Catalog you'd also see **lineage**
    here — a diagram of *where this table's data came from* (which upstream tables and jobs
    produced it), the same idea introduced back in [Unit 1.1](../unit1/what-is-de.md). Lineage is
    a cloud-only feature in this OSS edition, but the browse-and-inspect habit is identical.

### Discover from the CLI (container-free)
The same discovery works headless — handy for scripting a data inventory. Use the token from
[6.1](catalogs.md) (`login.sh`, no container shell):

```bash
export UC=http://localhost:8081 UC_URL=http://localhost:8081
export KC_URL=http://keycloak:8080/realms/de-stack/protocol/openid-connect/token
T=$(common/uc-cli/login.sh analyst)

# What catalogs exist? Then drill in.
uc --server $UC --auth_token "$T" catalog list
uc --server $UC --auth_token "$T" schema  list --catalog shopflow
uc --server $UC --auth_token "$T" schema  get  --full_name shopflow.gold
```

**Read it step by step:**

- **`export UC=… UC_URL=…`** — set shell variables pointing at the Unity Catalog server so you
  don't retype the URL on every command. `$UC` is reused below as `--server $UC`.
- **`export KC_URL=…`** — the Keycloak token endpoint. `login.sh` calls it to get a login token.
- **`T=$(common/uc-cli/login.sh analyst)`** — log in as the **`analyst`** persona and capture the
  returned access **token** into the variable `T`. Every `uc` call passes it as `--auth_token "$T"`
  so the server knows *who is asking* — which, on cloud UC, decides what you're allowed to see.
- **`uc … catalog list`** — the first discovery move: **list every catalog** you can see. The
  general shape is `uc <object> list` — ask "what exists?" one level at a time.
- **`uc … schema list --catalog shopflow`** — **drill in one level**: list the schemas inside the
  `shopflow` catalog (`bronze`, `silver`, `gold`). Same `list` verb, narrowed by `--catalog`.
- **`uc … schema get --full_name shopflow.gold`** — switch from `list` to **`get`**: instead of
  "what exists?", ask "**tell me everything about this one thing**." `get` returns a single object's
  full **metadata** — its comment, owner, and properties. You address it by **`--full_name`**, the
  fully-qualified `catalog.schema` name.

!!! note "`list` vs `get` — the two verbs of CLI discovery"
    Almost all headless discovery is these two commands: **`list`** enumerates what's inside a
    container (catalogs → schemas → tables), and **`get`** pulls the full metadata for one named
    object. To inspect a table's columns and owner from the shell — the CLI equivalent of clicking
    a table in the Web UI — you'd run `uc … table get --full_name shopflow.gold.<table>`.

!!! note "Discovery and grants — model vs OSS"
    On **Databricks Unity Catalog**, discovery is *filtered by your grants* — you only see what
    you're allowed to, so browsing is safe to open to the whole company. This OSS edition doesn't
    filter listings that way yet, so treat the grant policy from [6.2](rbac.md) as the source of
    truth for *who may read what*. The **principle** — discovery is trustworthy because governance
    travels with the metadata — is what transfers to the cloud.

## Challenge
An analyst asks: *"Which `shopflow` schema is for analysts, and how would I confirm it's the
governed layer?"* Answer it through discovery alone.

!!! tip "How to approach it"
    Discovery is a two-step drill: first **`list`** to find the candidate (which schema looks like
    the analyst layer?), then confirm it's really theirs by checking the **grants** on it — the
    access policy from [6.2](rbac.md). "Governed" doesn't mean "named gold"; it means the policy
    actually lets analysts read it.

??? note "Solution"
    ```bash
    # 1. list the schemas
    uc --server $UC --auth_token "$T" schema list --catalog shopflow
    #    -> bronze, silver, gold   (gold = the analyst marts)

    # 2. confirm the access policy on it (from 6.2)
    uc --server $UC --auth_token "$T" permission get --securable_type schema --name shopflow.gold
    #    -> analyst: USE SCHEMA, SELECT
    ```

    **Read it step by step:**

    - **`schema list --catalog shopflow`** — the discovery step. It returns `bronze`, `silver`,
      `gold`; `gold` is the analyst-facing marts layer by convention.
    - **`permission get --securable_type schema --name shopflow.gold`** — the *confirmation* step.
      A **securable** is any object grants can attach to (a catalog, schema, or table);
      `--securable_type schema` says "I'm asking about a schema," and `--name` picks which one. The
      output — `analyst: USE SCHEMA, SELECT` — proves analysts are actually **granted** to read it.
      That's what makes it the *governed* layer, not just its name.

    Same path in the UI: `shopflow` → `gold` → read the column/owner panel. No Slack message
    required — that's the payoff of a governed catalog.

!!! tip "🎯 The same discovery on Azure, Databricks, Snowflake & Fabric"
    **What you just did:** browsed the catalog (UI + CLI) and inspected schema/table metadata.

    - **Azure Databricks** — *identical*: the browse surface is **Catalog Explorer** over the same
      Unity Catalog metadata, plus first-class **search, tags, and data lineage**.
    - **Snowflake** — the **Snowsight** object explorer + `INFORMATION_SCHEMA`; **Horizon** for
      catalog-wide search/governance.
    - **Microsoft Fabric** — the **OneLake data hub** for finding data, **Microsoft Purview** for
      catalog search, classification, and lineage.
    - **Azure Data Factory** — no catalog/discovery of its own; that surface lives in UC / Purview.

    Everywhere the principle holds: discovery is only trustworthy because governance backs it.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **Data discovery** | Finding trustworthy data yourself via the catalog — no Slack message needed |
| **Search** | Looking up a dataset by name/keyword instead of knowing where it lives |
| **Catalog** | The top-level container and searchable index of the whole data estate |
| **Metadata** | "Data about the data" — columns, types, comments, owner recorded per object |
| **Ownership** | Who is accountable for a dataset — the "who do I ask?" of trust |
| **Lineage** | Where data came from — upstream tables/jobs that produced it (cloud UC/Purview) |
| **Securable** | Any object grants attach to — a catalog, schema, or table |
| **`uc … list`** | Enumerate what's inside a container (catalogs → schemas → tables) |
| **`uc … get`** | Pull the full metadata for one named object (`--full_name`) |
| **Self-service** | Browse without asking the data team |
| **Catalog Explorer** | Databricks' UC browse UI (this is its OSS cousin) |

## You can now…
- Browse catalogs → schemas → tables and inspect metadata (UI + CLI, container-free)
- Explain why a governed catalog enables safe, self-service discovery
- Tie discovery back to the access policy — the two halves of governance
