#!/usr/bin/env groovy

pipeline {
    agent any
    options {
        copyArtifactPermission('*');
    }
    stages {
        stage('Build, test and deploy python package') {
            agent { label 'python3' }
            stages {
                stage('Run unit tests') {
                    steps {
                        sh 'tox --recreate'
                    }
                }
                // TODO add linting etc
                stage('Build source distribution') {
                    steps {
                        sh 'poetry build -f wheel'
                        archiveArtifacts artifacts: 'dist/evalg-*.tar.gz'
                    }
                }
            }
            post {
                always {
                    junit '**/junit*.xml'
                    publishCoverage adapters: [coberturaAdapter(path: '**/coverage*.xml')]
                }
                cleanup {
                    sh('rm -vf junit-*.xml')
                    sh('rm -vf coverage-*.xml')
                    sh('rm -vrf build dist')
                }
            }
        }
        stage('Build and deploy docker image') {
            agent { label 'docker' }
            when { branch 'master' }
            environment {
                VERSION = sh(
                    returnStdout: true,
                    script: 'git describe --dirty=+ --tags'
                ).trim()
                REPO = 'harbor.uio.no'
                PROJECT = 'it-usit-int-drift'
                APP_NAME = 'valg-backend'
                CONTAINER = "${REPO}/${PROJECT}/${APP_NAME}"
                IMAGE_TAG = "${CONTAINER}:${BRANCH_NAME}-${VERSION}"
            }
            stages {
                stage('Build docker image') {
                    steps {
                        script {
                            docker_image = docker.build("${IMAGE_TAG}", '--pull --no-cache -f ./Dockerfile-old-env .')
                        }
                    }
                }
                stage('Deploy') {
                    parallel {
                        stage('Push image to harbor') {
                            steps {
                                script {
                                    docker_image.push()
                                }
                            }
                        }
                        stage('Tag image as latest/utv') {
                            steps {
                                script {
                                    docker_image.push('latest')
                                    docker_image.push('utv')
                                }
                            }
                        }
                    }
                }
            }
            post {
                cleanup {
                    sh("docker rmi -f \$(docker images --filter 'reference=${IMAGE_TAG}' -q)")
                }
            }
        }
    }
}
