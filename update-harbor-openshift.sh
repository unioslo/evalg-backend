#!/usr/bin/env bash
GIT_BRANCH=`git rev-parse --abbrev-ref HEAD`
GIT_SHA=`git rev-parse --short HEAD`
REPO="harbor.uio.no"
PROJECT="it-usit-int-drift"

APP_NAME="evalg-backend-k8s"
WORKER_APP_NAME="evalg-worker-k8s"

CONTAINER="${REPO}/${PROJECT}/${APP_NAME}"
WORKER_CONTAINER="${REPO}/${PROJECT}/${WORKER_APP_NAME}"

IMAGE_TAG="${CONTAINER}:${GIT_BRANCH}-${GIT_SHA}-${RANDOM}"
IMAGE_TAG_WORKER="${WORKER_CONTAINER}:${GIT_BRANCH}-${GIT_SHA}-WORKER-${RANDOM}"

echo "Building $IMAGE_TAG"
docker build -f Dockerfile-k8s -t $IMAGE_TAG .

echo "Building $IMAGE_TAG"
docker build -f Dockerfile-k8s-worker -t $IMAGE_TAG_WORKER .

echo "Pushing $IMAGE_TAG"
docker push $IMAGE_TAG

echo "Pushing $IMAGE_TAG"
docker push $IMAGE_TAG_WORKER

echo "Tagging $IMAGE_TAG $CONTAINER:openshift"
docker tag $IMAGE_TAG_WORKER $WORKER_CONTAINER:latest

echo "Tagging $IMAGE_TAG $CONTAINER:latest"
docker tag $IMAGE_TAG $CONTAINER:latest

echo "Pushing $WORKER_CONTAINER:openshift"
docker push $WORKER_CONTAINER:latest

echo "Pushing $CONTAINER:latest"
docker push $CONTAINER:latest
