#!/usr/bin/env bash
GIT_BRANCH=`git rev-parse --abbrev-ref HEAD`
GIT_SHA=`git rev-parse --short HEAD`
REPO="harbor.uio.no"
PROJECT="it-usit-int-drift"
APP_NAME="evalg-backend"
CONTAINER="${REPO}/${PROJECT}/${APP_NAME}"
IMAGE_TAG="${CONTAINER}:${GIT_BRANCH}-${GIT_SHA}-${RANDOM}"

echo "Building $IMAGE_TAG"
docker build -f Dockerfile --pull --no-cache -t $IMAGE_TAG .

echo "Pushing $IMAGE_TAG"
docker push $IMAGE_TAG

echo "Tagging $IMAGE_TAG $CONTAINER:staging"
docker tag $IMAGE_TAG $CONTAINER:staging
docker push $CONTAINER:staging

if [[ $GIT_BRANCH = "main" ]]
then
  echo "On main-branch, setting $IMAGE_TAG as $CONTAINER:latest"
  docker tag $IMAGE_TAG $CONTAINER:latest
  docker push $CONTAINER:latest
fi
