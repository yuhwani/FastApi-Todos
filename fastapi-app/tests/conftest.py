import sys
import os
import threading
import time
import pytest
import uvicorn

# fastapi-app/ 디렉토리를 기준으로 경로 설정
APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# main.py import 및 templates/ 상대경로가 올바르게 동작하도록 작업 디렉토리 변경
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

BASE_URL = "http://localhost:8001"


class UvicornTestServer(uvicorn.Server):
    """테스트용 uvicorn 서버 (별도 스레드에서 실행)."""

    def install_signal_handlers(self):
        pass  # 시그널 핸들러 비활성화 (스레드 내 실행 시 필요)


@pytest.fixture(scope="session")
def live_server(tmp_path_factory):
    """FastAPI 서버를 백그라운드 스레드에서 기동하고 base URL을 반환."""
    # 테스트 전용 임시 todo 파일 생성
    tmp_dir = tmp_path_factory.mktemp("data")
    test_todo_file = str(tmp_dir / "todo_test.json")

    # 환경변수로 TODO_FILE 경로를 오버라이드
    os.environ["TODO_FILE"] = test_todo_file

    import main as app_module
    app_module.TODO_FILE = test_todo_file

    config = uvicorn.Config(
        app=app_module.app,
        host="127.0.0.1",
        port=8001,
        log_level="error",
    )
    server = UvicornTestServer(config=config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # 서버가 뜰 때까지 대기
    for _ in range(30):
        if server.started:
            break
        time.sleep(0.1)

    yield BASE_URL

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(autouse=True)
def reset_todos(live_server):
    """각 테스트 전후로 todo 데이터를 초기화."""
    import main as app_module
    app_module.save_todos([])
    yield
    app_module.save_todos([])
