pipeline {
    agent any



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
                    // [수정됨] Windows 환경에 맞춰 bat 명령어 사용
                    echo "Windows 환경에서 Python 스크립트를 실행합니다..."
                    bat 'python scripts/build_interface.py'
                }
            }
        }
    }

    post {
        success {
            echo "✅ 빌드가 성공했습니다. 결과물을 보관합니다."
            // Windows에서는 경로 구분자가 다르지만 Jenkins가 어느 정도 처리해줍니다.
            // 혹시 실패하면 'dist\\*.zip' 으로 변경 고려
            archiveArtifacts artifacts: 'dist/*.zip', fingerprint: true
        }
        failure {
            echo "❌ 빌드 실패. 개발자에게 알림을 보냅니다."
        }
    }
}