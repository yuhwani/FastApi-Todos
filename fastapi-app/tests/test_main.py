import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from main import app, save_todos, load_todos, TodoItem, CommentItem

client = TestClient(app)


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_state():
    """각 테스트 전후로 저장소를 초기화해 테스트 간 상태 격리."""
    save_todos([])
    yield
    save_todos([])


def make_todo(id=1, title="Test", description="Test description", completed=False, comments=None):
    """테스트용 TodoItem dict 생성 헬퍼."""
    return {
        "id": id,
        "title": title,
        "description": description,
        "completed": completed,
        "comments": comments if comments is not None else [],
    }


# ══════════════════════════════════════════════
# 1. 상태 관리 (State Management)
# ══════════════════════════════════════════════

class TestStateManagement:
    """저장소 상태가 테스트 간 격리되고 올바르게 유지되는지 검증."""

    def test_initial_state_is_empty(self):
        """초기 상태는 빈 목록이어야 한다."""
        assert load_todos() == []

    def test_save_and_load_roundtrip(self):
        """저장한 데이터를 그대로 불러올 수 있어야 한다."""
        todos = [make_todo(1), make_todo(2, title="Second")]
        save_todos(todos)
        loaded = load_todos()
        assert len(loaded) == 2
        assert loaded[0]["title"] == "Test"
        assert loaded[1]["title"] == "Second"

    def test_state_isolated_between_tests(self):
        """이전 테스트 데이터가 남아있지 않아야 한다."""
        response = client.get("/todos")
        assert response.json() == []

    def test_old_data_without_comments_gets_default(self):
        """comments 필드가 없는 기존 데이터를 불러오면 빈 리스트로 보정된다."""
        # comments 없이 직접 저장 (레거시 데이터 시뮬레이션)
        save_todos([{"id": 1, "title": "Old", "description": "Old desc", "completed": False}])
        loaded = load_todos()
        assert loaded[0]["comments"] == []

    def test_multiple_operations_maintain_consistency(self):
        """생성 → 수정 → 삭제 흐름에서 상태가 일관되게 유지된다."""
        client.post("/todos", json=make_todo(1))
        client.post("/todos", json=make_todo(2, title="B"))
        client.put("/todos/1", json=make_todo(1, title="A-updated"))
        client.delete("/todos/2")

        response = client.get("/todos")
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "A-updated"


# ══════════════════════════════════════════════
# 2. 데이터 모델링 (Data Modeling)
# ══════════════════════════════════════════════

class TestDataModeling:
    """TodoItem·CommentItem 모델의 구조와 기본값을 검증."""

    def test_todo_item_default_comments(self):
        """TodoItem 생성 시 comments 기본값은 빈 리스트다."""
        todo = TodoItem(id=1, title="T", description="D", completed=False)
        assert todo.comments == []

    def test_todo_item_with_comments(self):
        """TodoItem에 댓글을 포함해 생성할 수 있다."""
        comment = CommentItem(id=1, content="Hello")
        todo = TodoItem(id=1, title="T", description="D", completed=False, comments=[comment])
        assert len(todo.comments) == 1
        assert todo.comments[0].content == "Hello"

    def test_todo_item_fields_preserved(self):
        """API를 통해 생성된 항목의 모든 필드가 그대로 반환된다."""
        payload = make_todo(1, title="My Todo", description="Details", completed=True)
        response = client.post("/todos", json=payload)
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "My Todo"
        assert data["description"] == "Details"
        assert data["completed"] is True
        assert data["comments"] == []

    def test_comment_item_fields(self):
        """댓글 항목이 id와 content 필드를 올바르게 가진다."""
        client.post("/todos", json=make_todo(1))
        response = client.post("/todos/1/comments", json={"content": "First comment"})
        comment = response.json()["comments"][0]
        assert "id" in comment
        assert comment["content"] == "First comment"

    def test_comment_id_auto_increments(self):
        """댓글 ID는 자동으로 증가한다."""
        client.post("/todos", json=make_todo(1))
        client.post("/todos/1/comments", json={"content": "C1"})
        client.post("/todos/1/comments", json={"content": "C2"})
        response = client.get("/todos/1/comments")
        comments = response.json()
        assert comments[0]["id"] == 1
        assert comments[1]["id"] == 2


# ══════════════════════════════════════════════
# 3. CRUD API 테스트
# ══════════════════════════════════════════════

class TestGetTodos:
    """GET /todos"""

    def test_empty_list(self):
        response = client.get("/todos")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_all_items(self):
        save_todos([make_todo(1), make_todo(2, title="B")])
        response = client.get("/todos")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_response_includes_comments_field(self):
        save_todos([make_todo(1)])
        response = client.get("/todos")
        assert "comments" in response.json()[0]


class TestCreateTodo:
    """POST /todos"""

    def test_create_success(self):
        response = client.post("/todos", json=make_todo(1))
        assert response.status_code == 200
        assert response.json()["id"] == 1

    def test_create_multiple(self):
        client.post("/todos", json=make_todo(1))
        client.post("/todos", json=make_todo(2, title="B"))
        response = client.get("/todos")
        assert len(response.json()) == 2

    def test_create_duplicate_id_returns_400(self):
        client.post("/todos", json=make_todo(1))
        response = client.post("/todos", json=make_todo(1, title="Dup"))
        assert response.status_code == 400

    def test_create_preserves_completed_false(self):
        response = client.post("/todos", json=make_todo(1, completed=False))
        assert response.json()["completed"] is False

    def test_create_preserves_completed_true(self):
        response = client.post("/todos", json=make_todo(1, completed=True))
        assert response.json()["completed"] is True


class TestUpdateTodo:
    """PUT /todos/{todo_id}"""

    def test_update_success(self):
        client.post("/todos", json=make_todo(1))
        response = client.put("/todos/1", json=make_todo(1, title="Updated", completed=True))
        assert response.status_code == 200
        assert response.json()["title"] == "Updated"
        assert response.json()["completed"] is True

    def test_update_not_found_returns_404(self):
        response = client.put("/todos/99", json=make_todo(99, title="X"))
        assert response.status_code == 404

    def test_update_preserves_existing_comments(self):
        """수정 시 기존 댓글이 사라지지 않아야 한다."""
        client.post("/todos", json=make_todo(1))
        client.post("/todos/1/comments", json={"content": "Keep me"})
        client.put("/todos/1", json=make_todo(1, title="Updated"))
        response = client.get("/todos/1/comments")
        assert len(response.json()) == 1
        assert response.json()[0]["content"] == "Keep me"


class TestDeleteTodo:
    """DELETE /todos/{todo_id}"""

    def test_delete_success(self):
        client.post("/todos", json=make_todo(1))
        response = client.delete("/todos/1")
        assert response.status_code == 200
        assert response.json()["message"] == "To-Do item deleted"

    def test_delete_removes_item(self):
        client.post("/todos", json=make_todo(1))
        client.delete("/todos/1")
        response = client.get("/todos")
        assert response.json() == []

    def test_delete_not_found_returns_404(self):
        response = client.delete("/todos/99")
        assert response.status_code == 404

    def test_delete_only_target_item(self):
        """지정한 항목만 삭제되고 나머지는 유지된다."""
        client.post("/todos", json=make_todo(1))
        client.post("/todos", json=make_todo(2, title="B"))
        client.delete("/todos/1")
        response = client.get("/todos")
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 2


class TestToggleTodo:
    """PATCH /todos/{todo_id}/toggle"""

    def test_toggle_false_to_true(self):
        client.post("/todos", json=make_todo(1, completed=False))
        response = client.patch("/todos/1/toggle")
        assert response.status_code == 200
        assert response.json()["completed"] is True

    def test_toggle_true_to_false(self):
        client.post("/todos", json=make_todo(1, completed=True))
        response = client.patch("/todos/1/toggle")
        assert response.json()["completed"] is False

    def test_toggle_twice_returns_original(self):
        client.post("/todos", json=make_todo(1, completed=False))
        client.patch("/todos/1/toggle")
        response = client.patch("/todos/1/toggle")
        assert response.json()["completed"] is False

    def test_toggle_not_found_returns_404(self):
        response = client.patch("/todos/99/toggle")
        assert response.status_code == 404


class TestComments:
    """POST /todos/{todo_id}/comments, GET /todos/{todo_id}/comments"""

    def test_add_comment_success(self):
        client.post("/todos", json=make_todo(1))
        response = client.post("/todos/1/comments", json={"content": "Hello"})
        assert response.status_code == 200
        assert response.json()["comments"][0]["content"] == "Hello"

    def test_add_comment_todo_not_found(self):
        response = client.post("/todos/99/comments", json={"content": "Hello"})
        assert response.status_code == 404

    def test_get_comments_success(self):
        client.post("/todos", json=make_todo(1))
        client.post("/todos/1/comments", json={"content": "C1"})
        client.post("/todos/1/comments", json={"content": "C2"})
        response = client.get("/todos/1/comments")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_get_comments_empty(self):
        client.post("/todos", json=make_todo(1))
        response = client.get("/todos/1/comments")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_comments_todo_not_found(self):
        response = client.get("/todos/99/comments")
        assert response.status_code == 404


# ══════════════════════════════════════════════
# 4. 유효성 검사 (Validation)
# ══════════════════════════════════════════════

class TestValidation:
    """필수 필드 누락·잘못된 타입 등 유효성 검사 실패를 검증."""

    def test_create_missing_description_returns_422(self):
        response = client.post("/todos", json={"id": 1, "title": "T", "completed": False})
        assert response.status_code == 422

    def test_create_missing_completed_returns_422(self):
        response = client.post("/todos", json={"id": 1, "title": "T", "description": "D"})
        assert response.status_code == 422

    def test_create_missing_title_returns_422(self):
        response = client.post("/todos", json={"id": 1, "description": "D", "completed": False})
        assert response.status_code == 422

    def test_create_missing_id_returns_422(self):
        response = client.post("/todos", json={"title": "T", "description": "D", "completed": False})
        assert response.status_code == 422

    def test_create_invalid_id_type_returns_422(self):
        response = client.post("/todos", json={"id": "not-a-number", "title": "T", "description": "D", "completed": False})
        assert response.status_code == 422

    def test_create_invalid_completed_type_returns_422(self):
        # Pydantic v2는 "yes"/"no" 문자열을 bool로 자동 변환하므로, 변환 불가한 리스트 타입으로 검증
        response = client.post("/todos", json={"id": 1, "title": "T", "description": "D", "completed": [1, 2, 3]})
        assert response.status_code == 422

    def test_update_missing_field_returns_422(self):
        client.post("/todos", json=make_todo(1))
        response = client.put("/todos/1", json={"id": 1, "title": "T"})
        assert response.status_code == 422

    def test_add_comment_missing_content_returns_422(self):
        client.post("/todos", json=make_todo(1))
        response = client.post("/todos/1/comments", json={})
        assert response.status_code == 422

    def test_create_empty_body_returns_422(self):
        response = client.post("/todos", json={})
        assert response.status_code == 422
