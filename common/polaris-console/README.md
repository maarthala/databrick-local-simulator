# Polaris Console — web UI build

Apache Polaris ships **no official Console image** yet, so we build it from
`apache/polaris-tools`. One tweak: the Console is a browser app, so its API URL is
baked at **build time** to the **browser-reachable** Polaris port (`localhost:8185`),
not the internal `polaris:8181`.

## Build the image

```bash
git clone --depth 1 https://github.com/apache/polaris-tools.git
cd polaris-tools/console

# point the console at the host-published Polaris port (browser-reachable)
sed -i 's#http://polaris:8181#http://localhost:8185#g' docker/Dockerfile

# self-contained multi-stage node/Vite build → nginx
docker build -f docker/Dockerfile -t apache/polaris-console:latest .
```

The build-time env baked in (from `docker/Dockerfile`):
```
VITE_POLARIS_API_URL=http://localhost:8185
VITE_POLARIS_REALM=POLARIS
VITE_POLARIS_PRINCIPAL_SCOPE=PRINCIPAL_ROLE:ALL
VITE_OAUTH_TOKEN_URL=http://localhost:8185/api/catalog/v1/oauth/tokens
VITE_POLARIS_REALM_HEADER_NAME=Polaris-Realm
```

## Run it (compose)

Wired in `local/polaris.yaml` as the `polaris-console` service (host **:8188** →
container :8080), depends on `polaris`. Browse **http://localhost:8188** and sign
in with the Polaris client credentials (`root` / `s3cr3t`, realm `POLARIS`).

## k8s

Build + `docker save | ssh … | microk8s ctr images import -` to the node (the
kubelet pull corrupts this node's containerd), then add a Deployment/Service +
ingress mirroring `local/polaris.yaml`.
