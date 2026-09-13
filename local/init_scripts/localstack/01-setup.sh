#!/bin/bash
set -e

# Create bucket and upload sample CSV
awslocal s3 mb s3://demo-bucket
awslocal s3api put-object --bucket demo-bucket --key hive/default/