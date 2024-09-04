from fastapi import FastAPI, Request, Form, Depends, Response, Cookie, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import paramiko
from starlette.middleware.cors import CORSMiddleware
import json
from models import SessionLocal, Server, User, engine
import models

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        # If not authenticated, redirect to login
        return RedirectResponse(url="/login_page")

    servers = db.query(Server).all()
    commands_results = json.loads(request.cookies.get("session", "[]"))
    return templates.TemplateResponse("index.html",
                                      {"request": request, "commands_results": commands_results, "servers": servers})


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
    return {"message": "Server added successfully!"}


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

    commands_results = json.loads(request.cookies.get("session", "[]"))
    return templates.TemplateResponse("index.html", {
        "request": request,
        "commands_results": commands_results,
        "servers": db.query(Server).all(),
        "current_server": server  # Pass the current server to the template
    })


@app.post("/execute/")
async def execute(request: Request, command: str = Form(...), server_id: int = Form(...), session: str = Cookie(None),
                  db: Session = Depends(get_db)):
    server = db.query(Server).filter(Server.id == server_id).first()

    if not server:
        return {"error": "Server not found"}

    result = execute_command(server.ip, server.login, server.password, command)
    commands_results = json.loads(session) if session else []

    commands_results.append({"command": command, "result": result})

    response = templates.TemplateResponse("index.html", {"request": request, "commands_results": commands_results,
                                                         "servers": db.query(Server).all()})

    response.set_cookie(key="session", value=json.dumps(commands_results), httponly=True)

    return response


if __name__ == "__main__":
    import uvicorn


    models.Base.metadata.create_all(bind=engine)
    # Ensure there is at least one user for login
    with SessionLocal() as db:
        if not db.query(User).filter(User.username == "admin").first():
            db.add(User(username="admin", password="admin"))
            db.commit()

    uvicorn.run(app, host="127.0.0.1", port=8000)
