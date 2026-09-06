#!/usr/bin/env bash
# Push the stack's custom images to your registry, then point the chart at it:
#   helm upgrade ... --set global.imageRegistry=$REGISTRY
#
# Usage:
#   REGISTRY=ghcr.io/<your-gh-namespace>/de-stack   bash helm/de-stack/push-images.sh
#   REGISTRY=docker.io/<your-dockerhub-user>/de-stack bash helm/de-stack/push-images.sh
#
# You must be `docker login`'d to that registry first.
# The k8s node must be able to pull these — for a private repo, create an image
# pull secret (see README) or make the packages public.
set -euo pipefail

REGISTRY="${REGISTRY:?Set REGISTRY, e.g. ghcr.io/<you>/de-stack or docker.io/<you>/de-stack}"

# chart-repo-name -> locally-built compose image
build_pairs="
hive=stack-hive-metastore:latest
spark=stack-spark-master:latest
kafka-connect=stack-kafka-connect:latest
airflow-slim=ghcr.io/maarthala/de-stack/airflow-slim:latest
jupyter=stack-jupyter:latest
hue=stack-db-ui:latest
superset=stack-superset:latest
app=stack-app-generators:latest
"

rm -f /tmp/de-stack-push-failed
echo "$build_pairs" | while IFS='=' read -r name src; do
  [ -z "$name" ] && continue
  dst="$REGISTRY/$name:latest"
  docker tag "$src" "$dst"
  ok=""
  for attempt in 1 2 3; do
    echo ">> pushing $dst (attempt $attempt)"
    if docker push "$dst"; then ok=1; break; fi
    echo "   push failed, retrying in 5s..."; sleep 5
  done
  [ -z "$ok" ] && echo "!! GAVE UP on $dst" && echo "$name" >> /tmp/de-stack-push-failed
done

echo
if [ -s /tmp/de-stack-push-failed ]; then
  echo "Some images failed (re-run the script to retry): $(tr '\n' ' ' < /tmp/de-stack-push-failed)"
  rm -f /tmp/de-stack-push-failed
else
  echo "All custom images pushed to $REGISTRY"
fi
echo "Now: helm upgrade --install de-stack helm/de-stack -n de-stack --set global.imageRegistry=$REGISTRY"
