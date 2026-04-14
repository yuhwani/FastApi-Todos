"""
Playwright UI 테스트
실행 전 1회: playwright install chromium
실행:        pytest tests/test_ui.py -v
"""

import pytest
from playwright.sync_api import Page, expect


# ──────────────────────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────────────────────

def add_todo(page: Page, title: str, description: str = ""):
    """폼을 통해 Todo를 추가하는 헬퍼."""
    current_count = page.locator(".todo-card").count()
    page.fill("#title", title)
    if description:
        page.fill("#description", description)
    page.click(".btn-add")
    page.wait_for_function(
        f"document.querySelectorAll('.todo-card').length > {current_count}"
    )


# ══════════════════════════════════════════════════════════════
# 1. 페이지 로딩
# ══════════════════════════════════════════════════════════════

class TestPageLoad:

    def test_title_is_visible(self, page: Page, live_server: str):
        page.goto(live_server)
        expect(page.locator("h1")).to_have_text("✦ Task Board")

    def test_form_inputs_are_visible(self, page: Page, live_server: str):
        page.goto(live_server)
        expect(page.locator("#title")).to_be_visible()
        expect(page.locator("#description")).to_be_visible()
        expect(page.locator(".btn-add")).to_be_visible()

    def test_empty_state_message_shown(self, page: Page, live_server: str):
        page.goto(live_server)
        expect(page.locator(".empty")).to_be_visible()


# ══════════════════════════════════════════════════════════════
# 2. Todo 추가
# ══════════════════════════════════════════════════════════════

class TestAddTodo:

    def test_add_single_todo(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "첫 번째 할 일", "설명입니다")

        expect(page.locator(".todo-title").first).to_have_text("첫 번째 할 일")
        expect(page.locator(".todo-desc").first).to_have_text("설명입니다")

    def test_form_cleared_after_add(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "제목", "설명")

        expect(page.locator("#title")).to_have_value("")
        expect(page.locator("#description")).to_have_value("")

    def test_add_multiple_todos(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "할 일 1")
        add_todo(page, "할 일 2")
        add_todo(page, "할 일 3")

        expect(page.locator(".todo-card")).to_have_count(3)

    def test_empty_title_does_not_add(self, page: Page, live_server: str):
        page.goto(live_server)
        page.click(".btn-add")
        page.wait_for_timeout(500)

        expect(page.locator(".todo-card")).to_have_count(0)

    def test_add_with_enter_key(self, page: Page, live_server: str):
        page.goto(live_server)
        page.fill("#title", "Enter 키 테스트")
        page.keyboard.press("Enter")
        page.wait_for_function("document.querySelectorAll('.todo-card').length > 0")

        expect(page.locator(".todo-title").first).to_have_text("Enter 키 테스트")

    def test_add_with_dates(self, page: Page, live_server: str):
        page.goto(live_server)
        page.fill("#title", "날짜 있는 할 일")
        page.fill("#start_date", "2026-04-01")
        page.fill("#end_date", "2026-12-31")
        page.click(".btn-add")
        page.wait_for_function("document.querySelectorAll('.todo-card').length > 0")

        expect(page.locator(".date-badge")).to_be_visible()


# ══════════════════════════════════════════════════════════════
# 3. 완료 토글
# ══════════════════════════════════════════════════════════════

class TestToggle:

    def _do_toggle(self, page: Page):
        """토글 클릭 후 네트워크 완료까지 대기하는 헬퍼."""
        page.locator(".toggle").first.scroll_into_view_if_needed()
        page.locator(".toggle").first.click()
        page.wait_for_load_state("networkidle", timeout=15000)

    def test_toggle_marks_completed(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "토글 테스트")
        self._do_toggle(page)

        html = page.evaluate("() => document.getElementById('todo-list').innerHTML")
        assert "todo-card completed" in html, (
            f"Expected 'todo-card completed' in #todo-list. Actual HTML: {html[:500]}"
        )

    def test_toggle_shows_checkmark(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "체크 표시 테스트")
        self._do_toggle(page)

        html = page.evaluate("() => document.getElementById('todo-list').innerHTML")
        assert "toggle done" in html, (
            f"Expected 'toggle done' in #todo-list. Actual HTML: {html[:500]}"
        )

    def test_toggle_twice_uncompletes(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "두 번 토글")

        self._do_toggle(page)
        html1 = page.evaluate("() => document.getElementById('todo-list').innerHTML")
        assert "todo-card completed" in html1, (
            f"Expected completed after 1st toggle. HTML: {html1[:500]}"
        )

        self._do_toggle(page)
        html2 = page.evaluate("() => document.getElementById('todo-list').innerHTML")
        assert "todo-card completed" not in html2, (
            f"Expected NOT completed after 2nd toggle. HTML: {html2[:500]}"
        )

    def test_completed_todo_has_strikethrough_title(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "취소선 테스트")
        self._do_toggle(page)

        html = page.evaluate("() => document.getElementById('todo-list').innerHTML")
        assert "todo-card completed" in html, (
            f"Expected 'todo-card completed' in #todo-list. HTML: {html[:500]}"
        )

        title_el = page.locator(".todo-card.completed .todo-title").first
        text_decoration = title_el.evaluate("el => getComputedStyle(el).textDecoration")
        assert "line-through" in text_decoration


# ══════════════════════════════════════════════════════════════
# 4. Todo 수정
# ══════════════════════════════════════════════════════════════

class TestEditTodo:

    def test_modal_opens_on_edit(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "수정할 항목")

        page.locator(".btn-edit").first.click()
        expect(page.locator(".modal-overlay")).to_have_class("modal-overlay open")

    def test_modal_prefills_existing_values(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "원래 제목", "원래 설명")

        page.locator(".btn-edit").first.click()
        expect(page.locator("#m-title")).to_have_value("원래 제목")
        expect(page.locator("#m-desc")).to_have_value("원래 설명")

    def test_edit_saves_new_title(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "변경 전 제목")

        page.locator(".btn-edit").first.click()
        page.fill("#m-title", "변경 후 제목")
        page.click(".btn-save")
        page.wait_for_timeout(400)

        expect(page.locator(".todo-title").first).to_have_text("변경 후 제목")

    def test_cancel_closes_modal_without_saving(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "취소 테스트")

        page.locator(".btn-edit").first.click()
        page.fill("#m-title", "저장 안 될 제목")
        page.click(".btn-cancel")
        page.wait_for_timeout(300)

        expect(page.locator(".modal-overlay")).not_to_have_class("open")
        expect(page.locator(".todo-title").first).to_have_text("취소 테스트")

    def test_escape_key_closes_modal(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "ESC 테스트")

        page.locator(".btn-edit").first.click()
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)

        expect(page.locator(".modal-overlay")).not_to_have_class("open")


# ══════════════════════════════════════════════════════════════
# 5. Todo 삭제
# ══════════════════════════════════════════════════════════════

class TestDeleteTodo:

    def test_delete_removes_card(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "삭제할 항목")

        page.on("dialog", lambda d: d.accept())
        page.locator(".btn-del").first.click()
        page.wait_for_timeout(400)

        expect(page.locator(".todo-card")).to_have_count(0)

    def test_delete_shows_empty_state(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "유일한 항목")

        page.on("dialog", lambda d: d.accept())
        page.locator(".btn-del").first.click()
        page.wait_for_timeout(400)

        expect(page.locator(".empty")).to_be_visible()

    def test_cancel_delete_keeps_card(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "취소할 삭제")

        page.on("dialog", lambda d: d.dismiss())
        page.locator(".btn-del").first.click()
        page.wait_for_timeout(400)

        expect(page.locator(".todo-card")).to_have_count(1)

    def test_delete_only_target(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "남길 항목")
        add_todo(page, "삭제할 항목")

        page.on("dialog", lambda d: d.accept())
        page.locator(".btn-del").last.click()
        page.wait_for_timeout(400)

        expect(page.locator(".todo-card")).to_have_count(1)
        expect(page.locator(".todo-title").first).to_have_text("남길 항목")


# ══════════════════════════════════════════════════════════════
# 6. 댓글
# ══════════════════════════════════════════════════════════════

class TestComments:

    def test_add_comment(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "댓글 테스트")

        comment_input = page.locator(".comment-form input").first
        comment_input.fill("첫 댓글")
        page.locator(".btn-comment").first.click()
        page.wait_for_timeout(400)

        expect(page.locator(".comment-item").first).to_contain_text("첫 댓글")

    def test_comment_input_cleared_after_submit(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "댓글 입력 초기화")

        comment_input = page.locator(".comment-form input").first
        comment_input.fill("내용")
        page.locator(".btn-comment").first.click()
        page.wait_for_timeout(400)

        expect(comment_input).to_have_value("")

    def test_multiple_comments(self, page: Page, live_server: str):
        page.goto(live_server)
        add_todo(page, "여러 댓글")

        for text in ["댓글 1", "댓글 2", "댓글 3"]:
            page.locator(".comment-form input").first.fill(text)
            page.locator(".btn-comment").first.click()
            page.wait_for_timeout(300)

        expect(page.locator(".comment-item")).to_have_count(3)
