#!/bin/bash

$CMD_MC alias set outception http://$MINIO_HOST:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD;

# Setup user & acccess policy
$CMD_MC admin user add outception $ACCESS_KEY $SECRET_ACCESS_KEY
$CMD_MC admin policy create outception outception-development $POLICY_FILE
$CMD_MC admin policy attach outception outception-development --user $ACCESS_KEY

# Create buckets
$CMD_MC mb outception/$BUCKET_NAME --with-versioning --ignore-existing

$CMD_MC mb outception/$PUBLIC_BUCKET_NAME --with-versioning --ignore-existing
$CMD_MC anonymous set download outception/$PUBLIC_BUCKET_NAME

$CMD_MC mb outception/$BUCKET_TESTING_NAME --with-versioning --ignore-existing
