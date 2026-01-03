pipeline {
    agent any

    // parameters 없음

    stages {
        stage('Initialize') {
            steps {
                echo ">>> Initializing Pipeline..."
                checkout scm
            }
        }

        stage('Build & Package') {
            steps {
                script {
                    echo "Executing Python build script on Windows..."
                    bat 'python scripts/build_interface.py'
                }
            }
        }
    }

    post {
        success {
            echo ">>> Build Succeeded. Archiving artifacts..."
            archiveArtifacts artifacts: 'dist/*.zip', fingerprint: true
        }
        failure {
            echo ">>> Build Failed."
        }
    }
}