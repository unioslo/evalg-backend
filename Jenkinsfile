#!/usr/bin/env groovy

pipeline {
    agent any
    options {
        copyArtifactPermission('*');
    }
    environment {
        POETRY = '/opt/python-3.9/bin/poetry'
        VERSION = sh(
            returnStdout: true,
            script: 'git describe --tags --abbrev=0'
        ).trim()
        no_proxy = "bitbucket.usit.uio.no"
    }
    stages {
        stage('Test and build python package') {
            agent { label 'python3' }
            stages {
                stage('Install dependencies') {
                    steps {
                        // Set version number from git tag
                        sh "${POETRY} version ${VERSION}"
                        sh "${POETRY} install"
                    }
                }
                stage('Test, lint and build') {
                    parallel {
                        stage('Run linting') {
                            steps {
                                script {
                                    // Allow linting to fail
                                    // TODO remove catchError after cleaning up codet describe --tags --dirty=+
                                    catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                                        sh "${POETRY} -q check"
                                        sh "${POETRY} run pylint evalg"
                                        sh "${POETRY} run black --check --diff evalg"
                                    }
                                }
                            }
                        }
                        stage('Run type checks') {
                            steps {
                                sh "${POETRY} run mypy -p evalg"
                            }
                        }
                        stage('Run tests') {
                            steps {
                                sh "${POETRY} run pytest --junitxml=junit.xml --cov=evalg --cov-report xml:coverage.xml --cov-report term"
                            }
                        }
                        stage('Build wheel') {
                            steps {
                                sh "${POETRY} build -f wheel"
                                archiveArtifacts artifacts: 'dist/evalg-*.whl'
                            }
                        }
                    }
                }
            }
            post {
                always {
                    junit '**/junit.xml'
                    publishCoverage adapters: [coberturaAdapter(path: '**/coverage.xml')]
                }
                cleanup {
                    sh('rm -vf junit.xml')
                    sh('rm -vf coverage.xml')
                    sh('rm -vrf build dist')
                }
            }
        }
        stage('Build and deploy docker image') {
            agent { label 'docker' }
            when { branch 'main' }
            environment {
                REPO = 'harbor.uio.no'
                PROJECT = 'it-usit-int-drift'
                APP_NAME = 'evalg-backend'
                CONTAINER = "${REPO}/${PROJECT}/${APP_NAME}"
                IMAGE_TAG = "${CONTAINER}:${VERSION}"
            }
            stages {
                stage('Build docker images') {
                    steps {
                        script {
                            docker_image = docker.build("${IMAGE_TAG}", '--pull --no-cache -f ./Dockerfile .')
                            docker_image.push()
                            docker_image.push('staging')
                            docker_image.push('latest')
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
