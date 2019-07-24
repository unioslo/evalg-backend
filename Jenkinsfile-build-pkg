#!/usr/bin/env groovy

pipeline {
    agent { label 'python3' }
    stages {
        stage('Run unit tests') {
            steps {
                sh 'tox --recreate'
            }
        }
        stage('Build source distribution') {
            steps {
                sh 'python3.6 setup.py sdist'
                archiveArtifacts artifacts: 'dist/evalg-*.tar.gz'
            }
        }
    }
    post {
        always {
            junit '**/junit*.xml'
            cobertura coberturaReportFile: '**/coverage*.xml'
        }
        cleanup {
            sh 'rm -vf junit-*.xml'
            sh 'rm -vf coverage-*.xml'
            sh 'rm -vrf build dist'
        }
    }
}
