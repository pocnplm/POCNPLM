pipeline {
    agent any

    parameters {
        string(name: 'BUILD_VERSION', defaultValue: '2.0.0-RC1', description: '배포할 버전 태그')
        choice(name: 'TARGET_ENV', choices: ['dev', 'stg', 'prod'], description: '배포 대상 환경')
    }

    stages {
        stage('Initialize') {
            steps {
                echo "🚀 파이프라인 초기화 중..."
                checkout scm
            }
        }

        stage('Build & Package') {
            steps {
                script {
                    // Python 스크립트에게 권한 위임
                    // Linux/Mac
                    sh 'python3 scripts/build_interface.py'
                    
                    // Windows라면 아래 주석 해제 후 위 sh 주석 처리
                    // bat 'python scripts/build_interface.py'
                }
            }
        }
    }

    post {
        success {
            echo "✅ 빌드가 성공했습니다. 결과물을 보관합니다."
            // Jenkins UI에 빌드 결과물(zip)을 다운로드 버튼으로 만들어줌
            archiveArtifacts artifacts: 'dist/*.zip', fingerprint: true
        }
        failure {
            echo "❌ 빌드 실패. 개발자에게 알림을 보냅니다."
        }
    }
}