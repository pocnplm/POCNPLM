pipeline {
    agent any

    // 스크린샷에 있는 값들을 '기본값'으로 설정하여 입력창 유지
    parameters {
        // 1. POLARION_TOKEN (사진에 있는 긴 토큰 값)
        string(name: 'POLARION_TOKEN', 
               defaultValue: 'eyJraWQiOiIyMDljOGNlNS0wYTAwODNkZS0yMzhlZjBjYy04NDNhMDM5NCIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJhZG1pbiIsImlkIjoiODIwZmFiYjAtMGEwMDgzZGUtNjUyYTFlYjQtNzMxMzgyMTgiLCJleHAiOjE3NzUxODk2MjMsImlhdCI6MTc2NzQxMzYyM30.YfpqhCjcV3gQUXU6Cstb6YXAvB-SNmjeKT6jXtX2ZFezuLCVxIhrdGySopS9gfOilbEKV0-q7udBy2nu24GjwSxlEj5ewnNfj9_zzEuZ46r_u97yxKlKdQNTaNChZcifFCseiuODK6gwbB5Ynxv_ljgOd924rAlUH3m9W8Ye1pQjCisKAZ6kzqd66AQfWr9iCjbafmeJOBMPe9_pggx6z49b7WlRZXJgLDGB_p3U1XsKJB9sl3gj032IQimKRn6k9zpYt06vAiPj4bIZTfxBg-tN9xyZ7QrHO3-th78CrD9uhBf504IqOpzN_qXcXY1oglZ7x6higZch7tgin6Zf-Q', 
               description: 'Polarion Access Token', 
               trim: true)
        
        // 2. projectid  (사진에 빈칸으로 되어 있음 -> 빈칸 유지)
        string(name: 'projectid', defaultValue: '', description: 'Project ID (e.g., elibrary)', trim: true)
        
        // 3. testRunId (사진에 빈칸으로 되어 있음 -> 빈칸 유지)
        string(name: 'testRunId', defaultValue: '', description: 'Target Test Run ID', trim: true)
        
        // 4. BASE_URL (사진에 있는 URL)
        string(name: 'BASE_URL', 
               defaultValue: 'https://nplm.krlcspilot.com/polarion/rest/v1', 
               description: 'Polarion REST API URL', 
               trim: true)
        
        // 5. PDF_PATH (사진에 있는 경로)
        string(name: 'PDF_PATH', 
               defaultValue: 'C:\\Siemens\\Polarion\\Static Analysis.pdf', 
               description: 'Absolute path to PDF file', 
               trim: true)
    }

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
                    echo ">>> [Stage 1] Executing Build Script..."
                    // 빌드 스크립트 실행
                    bat 'python scripts/build_interface.py'
                }
            }
        }

        stage('Upload to Polarion') {
            steps {
                script {
                    echo ">>> [Stage 2] Uploading Result to Polarion..."
                    // 업로드 스크립트 실행 
                    // (위 파라미터들이 Python의 os.getenv로 자동 전달됨)
                    bat 'python scripts/upload_polarion.py'
                }
            }
        }
    }

    post {
        success {
            echo ">>> Pipeline Succeeded. Artifacts archived."
            archiveArtifacts artifacts: 'dist/*.zip', fingerprint: true
        }
        failure {
            echo ">>> Pipeline Failed."
        }
    }
}