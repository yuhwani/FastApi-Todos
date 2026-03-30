from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import json
import os

app = FastAPI()

# 댓글 모델
class CommentItem(BaseModel):
    id: int
    content: str

# 댓글 생성용 모델
class CommentCreate(BaseModel):
    content: str

# To-Do 항목 모델
class TodoItem(BaseModel):
    id: int
    title: str
    description: str
    completed: bool
    comments: list[CommentItem] = Field(default_factory=list)

# JSON 파일 경로
TODO_FILE = "todo.json"

# JSON 파일에서 To-Do 항목 로드
def load_todos():
    if os.path.exists(TODO_FILE):
        with open(TODO_FILE, "r", encoding="utf-8") as file:
            todos = json.load(file)

            # 기존 데이터에 comments가 없을 수 있으니 보정
            for todo in todos:
                if "comments" not in todo:
                    todo["comments"] = []

            return todos
    return []

# JSON 파일에 To-Do 항목 저장
def save_todos(todos):
    with open(TODO_FILE, "w", encoding="utf-8") as file:
        json.dump(todos, file, indent=4, ensure_ascii=False)

# To-Do 목록 조회
@app.get("/todos", response_model=list[TodoItem])
def get_todos():
    return load_todos()

# 신규 To-Do 항목 추가
@app.post("/todos", response_model=TodoItem)
def create_todo(todo: TodoItem):
    todos = load_todos()

    # 중복 ID 방지
    for existing_todo in todos:
        if existing_todo["id"] == todo.id:
            raise HTTPException(status_code=400, detail="Todo ID already exists")

    todo_dict = todo.dict()

    if "comments" not in todo_dict:
        todo_dict["comments"] = []

    todos.append(todo_dict)
    save_todos(todos)
    return todo_dict

# To-Do 항목 수정
@app.put("/todos/{todo_id}", response_model=TodoItem)
def update_todo(todo_id: int, updated_todo: TodoItem):
    todos = load_todos()
    for index, todo in enumerate(todos):
        if todo["id"] == todo_id:
            updated_todo_dict = updated_todo.dict()

            # 기존 댓글 유지
            updated_todo_dict["comments"] = todo.get("comments", [])

            todos[index] = updated_todo_dict
            save_todos(todos)
            return updated_todo_dict

    raise HTTPException(status_code=404, detail="To-Do item not found")

# To-Do 항목 삭제
@app.delete("/todos/{todo_id}", response_model=dict)
def delete_todo(todo_id: int):
    todos = load_todos()
    new_todos = [todo for todo in todos if todo["id"] != todo_id]

    if len(new_todos) == len(todos):
        raise HTTPException(status_code=404, detail="To-Do item not found")

    save_todos(new_todos)
    return {"message": "To-Do item deleted"}

# 댓글 추가
@app.post("/todos/{todo_id}/comments", response_model=TodoItem)
def add_comment(todo_id: int, comment: CommentCreate):
    todos = load_todos()

    for todo in todos:
        if todo["id"] == todo_id:
            comments = todo.get("comments", [])
            new_comment_id = 1 if not comments else max(c["id"] for c in comments) + 1

            new_comment = {
                "id": new_comment_id,
                "content": comment.content
            }

            comments.append(new_comment)
            todo["comments"] = comments

            save_todos(todos)
            return todo

    raise HTTPException(status_code=404, detail="To-Do item not found")

# 특정 To-Do의 댓글 조회
@app.get("/todos/{todo_id}/comments", response_model=list[CommentItem])
def get_comments(todo_id: int):
    todos = load_todos()

    for todo in todos:
        if todo["id"] == todo_id:
            return todo.get("comments", [])

    raise HTTPException(status_code=404, detail="To-Do item not found")

# 완료 토글
@app.patch("/todos/{todo_id}/toggle", response_model=TodoItem)
def toggle_todo(todo_id: int):
    todos = load_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo["completed"] = not todo["completed"]
            save_todos(todos)
            return todo
    raise HTTPException(status_code=404, detail="To-Do item not found")

# HTML 파일 서빙
@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("templates/index.html", "r", encoding="utf-8") as file:
        content = file.read()
    return HTMLResponse(content=content)