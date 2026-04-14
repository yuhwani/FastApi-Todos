import os
import requests
import pytest

BASE_URL = os.getenv("BASE_URL", "http://163.239.77.65:8003")

def is_server_available():
    try:
        requests.get(BASE_URL, timeout=3)
        return True
    except Exception:
        return False

skip_if_unavailable = pytest.mark.skipif(
    not is_server_available(),
    reason="배포 서버에 연결할 수 없어 테스트를 건너뜁니다."
)

@skip_if_unavailable
def test_root():
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200

@skip_if_unavailable
def test_get_todos():
    response = requests.get(f"{BASE_URL}/todos")
    assert response.status_code == 200
