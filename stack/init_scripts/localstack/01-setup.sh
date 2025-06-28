#!/bin/bash
set -e

# Create bucket and upload sample CSV
awslocal s3 mb s3://demo-bucket
awslocal s3 cp /code/shared/testdata  s3://demo-bucket/northwind/ --recursive
awslocal s3api put-object --bucket demo-bucket --key hive/default/