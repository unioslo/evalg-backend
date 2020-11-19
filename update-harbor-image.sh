#!/usr/bin/env bash
GIT_BRANCH=`git rev-parse --abbrev-ref HEAD`
GIT_SHA=`git rev-parse --short HEAD`
REPO="harbor.uio.no"
PROJECT="it-usit-int-drift"
APP_NAME="valg-backend"
CONTAINER="${REPO}/${PROJECT}/${APP_NAME}"
IMAGE_TAG="${CONTAINER}:${GIT_BRANCH}-${GIT_SHA}"

if [[ $1 == "openshift" ]]; then
    APP_NAME="valg-backend-test"
    CONTAINER="${REPO}/${PROJECT}/${APP_NAME}"
    IMAGE_TAG="${CONTAINER}:${GIT_BRANCH}-${GIT_SHA}-${RANDOM}"
    IMAGE_TAG_WORKER="${CONTAINER}:${GIT_BRANCH}-${GIT_SHA}-WORKER-${RANDOM}"

    echo "Building $IMAGE_TAG"
    docker build -f Dockerfile-k8s -t $IMAGE_TAG .

    echo "Building $IMAGE_TAG"
    docker build -f Dockerfile-k8s-worker -t $IMAGE_TAG_WORKER .

    echo "Pushing $IMAGE_TAG"
    docker push $IMAGE_TAG

    echo "Pushing $IMAGE_TAG"
    docker push $IMAGE_TAG_WORKER

    echo "Tagging $IMAGE_TAG $CONTAINER:openshift"
    docker tag $IMAGE_TAG $CONTAINER:openshift

    echo "Tagging $IMAGE_TAG $CONTAINER:openshift"
    docker tag $IMAGE_TAG_WORKER $CONTAINER:worker

    echo "Tagging $IMAGE_TAG $CONTAINER:latest"
    docker tag $IMAGE_TAG $CONTAINER:latest

    echo "Pushing $CONTAINER:openshift"
    docker push $CONTAINER:openshift

    echo "Pushing $CONTAINER:openshift"
    docker push $CONTAINER:worker

    echo "Pushing $CONTAINER:latest"
    docker push $CONTAINER:latest

    exit 1
fi


echo "Building $IMAGE_TAG"
docker build -f Dockerfile-staging -t $IMAGE_TAG .

echo "Pushing $IMAGE_TAG"
docker push $IMAGE_TAG

if [[ $GIT_BRANCH = "master" ]]
then
  echo "On master-branch, setting $IMAGE_TAG as $CONTAINER:latest and $CONTAINER:utv"
  docker tag $IMAGE_TAG $CONTAINER:latest
  docker tag $IMAGE_TAG $CONTAINER:utv
  docker push $CONTAINER:latest
  docker push $CONTAINER:utv
fi
