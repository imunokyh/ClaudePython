// 차일드락 제어 SW CI 파이프라인
// 에이전트: Jenkins Built-In 노드 (Windows 11, 172.16.7.117)
// Python: Jenkins 전역 환경 변수 CHILD_LOCK_PYTHON이 있으면 그 경로를,
//         없으면 이 PC에 설치된 Python 3.12 경로를 쓴다.
pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    environment {
        PYTHON = "${env.CHILD_LOCK_PYTHON ?: 'C:\\Users\\user\\AppData\\Local\\Programs\\Python\\Python312\\python.exe'}"
        PYTHONUTF8 = '1'
        VENV_PY = '.venv\\Scripts\\python.exe'
    }

    stages {
        stage('환경 준비') {
            steps {
                bat '"%PYTHON%" --version'
                bat '"%PYTHON%" -m venv .venv'
                bat '%VENV_PY% -m pip install --quiet --upgrade pip'
                bat '%VENV_PY% -m pip install --quiet -e ".[dev]"'
            }
        }
        stage('정적 분석 (Ruff)') {
            steps {
                bat '%VENV_PY% -m ruff check .'
                bat '%VENV_PY% -m ruff format --check .'
            }
        }
        stage('타입 검사 (mypy strict)') {
            steps {
                bat '%VENV_PY% -m mypy'
            }
        }
        stage('단위 테스트 (Branch 커버리지 100%)') {
            steps {
                bat 'if not exist reports mkdir reports'
                bat '%VENV_PY% -m pytest --junitxml=reports/junit.xml --cov --cov-branch --cov-fail-under=100 --cov-report=xml:reports/coverage.xml'
            }
        }
        stage('주석률·함수 길이') {
            steps {
                bat '%VENV_PY% -m tools src tools'
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
