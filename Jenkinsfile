pipeline {
    agent any

    environment {
        // 빌드 번호를 포함한 압축 파일명 설정
        ARTIFACT_NAME = "Automotive_Sensor_Build_${BUILD_NUMBER}.zip"
    }

    stages {
        // 1단계: 테스트 (Polarion 연동을 위한 핵심 단계)
        stage('Test') {
            steps {
                echo 'Running Unit Tests...'
                // 파이썬 테스트 실행
                bat "python test_processor.py"
            }
            post {
                always {
                    // (선택) JUnit 플러그인이 있다면 결과를 시각화할 수 있습니다.
                    // 현재는 콘솔 출력으로 확인
                    echo "Test stage completed."
                }
            }
        }

        // 2단계: 빌드 (산출물을 zip으로 압축)
        stage('Build') {
            steps {
                echo 'Archiving artifacts into ZIP...'
                // PowerShell을 사용하여 필요한 파일들만 압축 (Windows 환경 전용)
                powershell """
                    Compress-Archive -Path main.py, models.py, sensor_processor.py -DestinationPath ${env.ARTIFACT_NAME} -Force
                """
                echo "Successfully created: ${env.ARTIFACT_NAME}"
            }
        }

        // 3단계: 배포 (Teamcenter REST API - 현재는 Placeholder)
        stage('Deploy') {
            steps {
                echo 'Connecting to Teamcenter REST Services...'
                echo "Target: http://your-teamcenter-server/tc/rest/..."
                echo "Status: Environment not ready. Skipping actual upload."
                
                // 나중에 환경이 준비되면 여기에 curl이나 powershell로 REST API 호출 코드를 넣습니다.
                script {
                    if (false) {
                        // 미래의 코드 예시
                        // bat "curl -u user:pass -X POST ... -F file=@${env.ARTIFACT_NAME}"
                    }
                }
            }
        }
    }

    // 빌드 후 처리 (젠킨스 UI에서 파일을 다운로드할 수 있게 보관)
    post {
        success {
            echo 'Build successful! Archiving the zip file in Jenkins...'
            archiveArtifacts artifacts: "*.zip", fingerprint: true
        }
    }
}