import os
import requests

BASE_URL = os.getenv("BASE_URL", "http://163.239.77.77:8011")

def test_root():
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200

def test_get_todos():
    response = requests.get(f"{BASE_URL}/todos")
    assert response.status_code == 200