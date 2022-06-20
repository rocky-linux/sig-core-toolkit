#!/bin/bash

MANIFEST_NAME="peridotempanadas"
BUILD_PATH="."
REGISTRY="docker.io"
USER="neilresf"
IMAGE_TAG="v0.1.0"
IMAGE_NAME="peridotempanadas"

podman buildx build \
  --platform linux/amd64,linux/arm64,linux/s390x,linux/ppc64le \
  --tag "${REGISTRY}/${USER}/${IMAGE_NAME}:${IMAGE_TAG}" \
  $PWD

