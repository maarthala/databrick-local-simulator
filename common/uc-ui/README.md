# Unity Catalog Web UI — Keycloak login patch

The upstream UC web UI (pinned commit `58d5c7b`) ships a **non-functional stub**
Keycloak button and only wires Google/Okta. `keycloak-login.patch` turns it into a
working per-user login that also works over plain **http**.

## What the patch changes (`keycloak-login.patch`, base `58d5c7b`)

| File | Change |
|---|---|
| `components/login/KeycloakAuthButton.tsx` | Implements the button: OIDC **implicit flow** (`response_type=id_token`, no secret/PKCE — `crypto.subtle` is unavailable on http), reads the id_token from the return fragment, calls `loginWithToken`. |
| `App.tsx` | `authEnabled` now also honors `REACT_APP_KEYCLOAK_AUTH_ENABLED` / Okta (was Google-only). |
| `context/client.ts` | Axios request interceptor attaches `Authorization: Bearer <uc_token>` from `localStorage`. UC's session cookie is `Secure`-only and the browser drops it on http, so the UI authenticates by header instead. |
| `hooks/user.ts` | Stores the UC token in the **`mutationFn`** and refreshes the user via a **`useMutation`-level `onSuccess`** (mutate-level callbacks are dropped when the caller unmounts mid-redirect — the actual bug that made login silently no-op). Logout clears it in `onSettled`. |
| `context/auth-context.tsx` | Minor: stores/clears the token on login/logout (belt-and-suspenders). |

## Runtime config (set as pod env — read by the CRA dev server at start)

```
REACT_APP_KEYCLOAK_AUTH_ENABLED=true
REACT_APP_KEYCLOAK_URL=http://auth.de.lan
REACT_APP_KEYCLOAK_REALM_ID=de-stack
REACT_APP_KEYCLOAK_CLIENT_ID=unity-catalog-ui
```

These are wired in `k8s/helm/de-stack/templates/unity-catalog-ui.yaml`. The realm's
public `unity-catalog-ui` client (implicit flow) and UC's `server.audiences`
(includes `unity-catalog-ui`) are in `files/keycloak/de-stack-realm.json` /
`templates/unity-catalog.yaml`.

## Rebuild the image

```bash
# 1. check out the pinned UC source and apply the patch
git clone https://github.com/unitycatalog/unitycatalog /tmp/uc-src
cd /tmp/uc-src && git checkout 58d5c7b
git apply /path/to/common/uc-ui/keycloak-login.patch

# 2. build (amd64 for the node) + flatten to a single layer (node overlayfs is fragile)
cd ui
docker build --platform linux/amd64 --build-arg PROXY_HOST=unity-catalog -t unitycatalog/unitycatalog-ui:kc .
docker create --name f unitycatalog/unitycatalog-ui:kc
docker export f | docker import \
  --change 'ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' \
  --change 'ENV NODE_VERSION=18.20.8' --change 'ENV YARN_VERSION=1.22.22' \
  --change 'WORKDIR /ui' --change 'ENTRYPOINT ["docker-entrypoint.sh"]' \
  --change 'CMD ["bun","run","start"]' - unitycatalog/unitycatalog-ui:kcflat
docker rm f

# 3. load onto the node (bypass the kubelet pull that corrupts this node's containerd)
docker save unitycatalog/unitycatalog-ui:kcflat | gzip | ssh sysadmin@192.168.1.201 'cat > /tmp/ucui-kcflat.tar.gz'
ssh -t sysadmin@192.168.1.201 'sudo bash -c "gunzip -c /tmp/ucui-kcflat.tar.gz | microk8s ctr images import -"'

# 4. deploy
helm template de-stack k8s/helm/de-stack -s templates/unity-catalog-ui.yaml | kubectl -n de-stack apply -f -
```

## Log in

Browse **http://uc-ui.de.lan** → **Continue with Keycloak** → sign in as
`analyst`, `engineer`, or `lead` (password = username). The catalog view is scoped to that user's
grants. (https also works via the Secure cookie, but shows a self-signed-cert
warning — http is the clean path.)
