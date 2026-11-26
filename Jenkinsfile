// 차일드락 제어 SW CI 파이프라인
// 가정: Linux 에이전트에 python3.12가 설치되어 있다. Windows 에이전트면 sh를 bat으로 바꾼다.
pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }

    stages {
        stage('환경 준비') {
            steps {
                sh 'python3.12 -m venv .venv'
                sh '.venv/bin/python -m pip install --quiet --upgrade pip'
                sh '.venv/bin/python -m pip install --quiet -e ".[dev]"'
            }
        }
        stage('정적 분석 (Ruff)') {
            steps {
                sh '.venv/bin/python -m ruff check .'
                sh '.venv/bin/python -m ruff format --check .'
            }
        }
        stage('단위 테스트 (Branch 커버리지 100%)') {
            steps {
                sh '''
                    mkdir -p reports
                    .venv/bin/python -m pytest \
                        --junitxml=reports/junit.xml \
                        --cov --cov-branch --cov-fail-under=100 \
                        --cov-report=xml:reports/coverage.xml
                '''
            }
        }
        stage('주석률·함수 길이') {
            steps {
                sh '.venv/bin/python -m tools src tools'
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'reports/junit.xml'
            archiveArtifacts allowEmptyArchive: true, artifacts: 'reports/**'
        }
    }
}
