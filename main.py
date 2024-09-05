from fastapi import FastAPI, Request, Form, Depends, Response, Cookie, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import paramiko
from starlette.middleware.cors import CORSMiddleware
import json
from models import SessionLocal, Server, User, CommandResult, engine
import models
from datetime import datetime
import logging


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)


templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def execute_command(ip: str, username: str, password: str, command: str):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username=username, password=password)

        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        client.close()

        return output if output else error
    except Exception as e:
        return str(e)

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if user and user.password == password:
        return user
    return None

@app.post("/login/")
async def login(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db)
):
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="username", value=username)
    return response

@app.get("/login_page", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    username = request.cookies.get("username")

    if not username:
        return RedirectResponse(url="/login_page")

    servers = db.query(Server).all()
    return templates.TemplateResponse("index.html",
                                      {"request": request, "servers": servers})

@app.post("/add_server/")
async def add_server(
        request: Request,
        name: str = Form(...),
        ip: str = Form(...),
        login: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db)
):
    new_server = Server(name=name, ip=ip, login=login, password=password)
    db.add(new_server)
    db.commit()
    return RedirectResponse(url="/", status_code=303)  # редирект на главную страницу

@app.post("/delete_server/")
async def delete_server(
        server_id: int = Form(...),
        db: Session = Depends(get_db)
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if server:
        db.delete(server)
        db.commit()
        return {"message": "Server deleted successfully!"}
    return {"error": "Server not found"}

@app.get("/execute/", response_class=HTMLResponse)
async def show_execute_command_page(request: Request, server_id: int, db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.id == server_id).first()

    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    commands_results = db.query(CommandResult).filter(CommandResult.server_id == server_id).all()
    return templates.TemplateResponse("index.html"  , {
        "request": request,
        "commands_results": commands_results,
        "servers": db.query(Server).all(),
        "current_server": server
    })


@app.post("/clear-history/")
async def clear_history(server_id: int, db: Session = Depends(get_db)):
    logging.info(f"Получен запрос на очистку истории для server_id: {server_id}")

    results = db.query(CommandResult).filter(CommandResult.server_id == server_id).all()

    if not results:
        logging.warning(f"Нет результатов команд для server_id: {server_id}")
        raise HTTPException(status_code=404, detail="Нет результатов команд для удаления.")

    deleted_count = db.query(CommandResult).filter(CommandResult.server_id == server_id).delete()
    db.commit()

    if deleted_count == 0:
        logging.error(f"Не удалось удалить записи для server_id: {server_id}")
        raise HTTPException(status_code=404, detail="Не удалось удалить записи.")

    logging.info(f"Успешно очищена история для server_id: {server_id}, удалено записей: {deleted_count}")
    return {"message": "История очищена!", "deleted_count": deleted_count}


@app.post("/execute/")
async def execute(request: Request, command: str = Form(...), server_id: int = Form(...), db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.id == server_id).first()

    if not server:
        return {"error": "Server not found"}

    result = execute_command(server.ip, server.login, server.password, command)

    # Сохранение результата в БД
    command_result = CommandResult(command=command, result=result, timestamp=datetime.utcnow(), server_id=server_id)
    db.add(command_result)
    db.commit()

    return RedirectResponse(url=f"/execute/?server_id={server.id}", status_code=303)

if __name__ == "__main__":
    import uvicorn
    models.Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        if not db.query(User).filter(User.username == "admin").first():
            db.add(User(username="admin", password="admin"))
            db.commit()

    uvicorn.run(app, host="127.0.0.1", port=8000)
