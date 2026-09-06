# Unity Catalog server — static credential vending patch

Stock Unity Catalog OSS can only **vend** S3 credentials two ways, and both are
incompatible with **MinIO**:

- **STS `AssumeRole`** — requires an `awsRoleArn`, and the SDK calls AWS STS.
  MinIO's STS doesn't honor arbitrary role ARNs (needs OIDC/LDAP-configured
  roles), and MinIO's root user can't call STS at all.
- **Static session credentials** — only used when an `s3.sessionToken` is set,
  and that token is handed back to clients (MinIO rejects a bogus session token).

There is no "vend plain permanent keys" mode. `static-cred-vending.patch` adds one.

## What the patch changes (`static-cred-vending.patch`, base commit `58d5c7b`)

| File | Change |
|---|---|
| `server/.../utils/ServerProperties.java` | Register an `s3.bucketPath.N` config when it has `bucketPath + region + accessKey + secretKey` (previously required `awsRoleArn` **or** `sessionToken`). |
| `server/.../credential/aws/AwsCredentialVendor.java` | When a bucket config has **no** `awsRoleArn` but has access/secret keys, vend those **permanent** keys directly (`StaticAwsCredentialGenerator`, no STS, no session token). |

With the patch, UC's `server.properties` just needs:

```properties
s3.bucketPath.0=s3://demo-bucket
s3.region.0=us-east-1
s3.accessKey.0=minioadmin
s3.secretKey.0=minioadmin
```

UC then vends `minioadmin/minioadmin` (permanent) to Spark/Trino, which use them
directly against MinIO — no STS, no session tokens.

## Rebuild the image

```bash
git clone https://github.com/unitycatalog/unitycatalog /tmp/uc-src
cd /tmp/uc-src && git checkout 58d5c7b
git apply /path/to/common/uc-server/static-cred-vending.patch

# full sbt build via the repo Dockerfile (amd64 for the node)
docker build --platform linux/amd64 -t unitycatalog/unitycatalog:vend .

# flatten to a single layer (node overlayfs is fragile with multi-layer images)
docker create --name ucv unitycatalog/unitycatalog:vend
docker export ucv | docker import \
  --change 'ENV PATH=/usr/lib/jvm/default-jvm/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' \
  --change 'ENV HOME=/home/unitycatalog' --change 'ENV JAVA_HOME=/usr/lib/jvm/default-jvm' \
  --change 'WORKDIR /home/unitycatalog' --change 'USER unitycatalog' \
  --change 'CMD ["./bin/start-uc-server"]' - unitycatalog/unitycatalog:vendflat
docker rm ucv

# load onto the node (bypass the kubelet pull that corrupts this node's containerd)
docker save unitycatalog/unitycatalog:vendflat | gzip | ssh sysadmin@192.168.1.201 'cat > /tmp/uc-vendflat.tar.gz'
ssh -t sysadmin@192.168.1.201 'sudo bash -c "gunzip -c /tmp/uc-vendflat.tar.gz | microk8s ctr images import -"'

helm template de-stack k8s/helm/de-stack -s templates/unity-catalog.yaml | kubectl -n de-stack apply -f -
```

## Why this is needed

It's what makes the **Trino ⇄ Unity Catalog** bridge work: Spark writes a Delta
UniForm table into `lakehouse.sales` (data in MinIO, metadata in UC), and Trino
reads it through UC's Iceberg REST catalog — both engines getting working MinIO
credentials from UC's vending.
