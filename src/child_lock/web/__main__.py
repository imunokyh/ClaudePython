"""@brief `python -m child_lock.web`: 로컬 시뮬레이터 서버 실행."""

import uvicorn

from child_lock.web.app import create_app

uvicorn.run(create_app(), host="127.0.0.1", port=8000)
