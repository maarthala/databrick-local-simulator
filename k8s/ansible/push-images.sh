#!/usr/bin/env bash
# Push all custom + patched de-stack images to a container registry, for
# environments whose nodes can pull directly from a registry (i.e. they do NOT
# need the build-load.yml ctr-import path).
#
# Build the images first (they must exist locally), e.g.:
#   ansible-playbook build-load.yml --tags images        # builds, does not import
# then:
#   REGISTRY=ghcr.io/<you>/de-stack ./push-images.sh
#
# You must be `docker login`'d to the registry. For a private repo, the cluster
# needs an imagePullSecret (see the chart README).
set -euo pipefail
REGISTRY="${REGISTRY:?Set REGISTRY, e.g. ghcr.io/<you>/de-stack or docker.io/<you>}"

# local image ref  =  registry repo:tag to publish as
mappings=(
  "ghcr.io/maarthala/de-stack/spark:latest=spark:latest"
  "ghcr.io/maarthala/de-stack/jupyter:latest=jupyter:latest"
  "ghcr.io/maarthala/de-stack/superset:latest=superset:latest"
  "ghcr.io/maarthala/de-stack/airflow-slim:latest=airflow-slim:latest"
  "unitycatalog/unitycatalog:vendflat=unity-catalog:vendflat"
  "unitycatalog/unitycatalog-ui:kcflat=unity-catalog-ui:kcflat"
)

for m in "${mappings[@]}"; do
  src="${m%%=*}"; dst="$REGISTRY/${m##*=}"
  if ! docker image inspect "$src" >/dev/null 2>&1; then
    echo "!! missing local image: $src  (build it first, e.g. ansible-playbook build-load.yml --tags images)"
    exit 1
  fi
  echo ">> $src  ->  $dst"
  docker tag "$src" "$dst"
  for attempt in 1 2 3; do docker push "$dst" && break || { echo "   retry $attempt..."; sleep 5; }; done
done

cat <<EOF

All images pushed to $REGISTRY. Deploy on a registry-pulling cluster with:

  ansible-playbook deploy.yml \\
    -e global_image_registry=$REGISTRY \\
    -e uc_image=$REGISTRY/unity-catalog:vendflat \\
    -e uc_ui_image=$REGISTRY/unity-catalog-ui:kcflat

(imagePullPolicy is IfNotPresent, so the kubelet pulls these from the registry
when they aren't already present on the node.)
EOF
