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
import httpx
from typing import Optional


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

TOKEN = "7777e84f3f9902abb6f2fd3d88427533810cf525489ed1b187a087395383c6891eb87abdedfbfaf3e2b31b4a5f80818d"


# @app.get("/get_data", response_class=HTMLResponse)
# async def get_data(request: Request, server_id: Optional[int] = None):
#     reglets_url = 'https://api.cloudvps.reg.ru/v1/reglets'
#     balance_data_url = 'https://api.cloudvps.reg.ru/v1/balance_data'
#
#     # Заголовки для запроса
#     headers = {
#         'Authorization': f'Bearer {TOKEN}',
#         'Content-Type': 'application/json'
#     }
#
#     async with httpx.AsyncClient() as client:
#         reglets_response = await client.get(reglets_url, headers=headers)
#         balance_response = await client.get(balance_data_url, headers=headers)
#
#     # Получение данных о балансе
#     balance_data = balance_response.json().get("balance_data", {})
#     total_balance = balance_data.get("balance", 0)
#     hourly_cost = balance_data.get("hourly_cost", 0)
#     monthly_cost = balance_data.get("monthly_cost", 0)
#
#     # Получение данных о реглетах
#     reglets_data = reglets_response.json().get("reglets", [])
#
#     # Определяем нужный реглет
#     if server_id is not None and server_id > 0:
#         selected_reglet = next((reglet for reglet in reglets_data if reglet['id'] == server_id), None)
#     else:
#         selected_reglet = reglets_data[0] if reglets_data else None
#
#
#
#     # Извлечение информации о реглете
#     name = selected_reglet.get("name")
#     ram = selected_reglet.get("memory")
#     disk = selected_reglet.get("disk")
#     status = selected_reglet.get("status")
#     region_slug = selected_reglet.get("region_slug")
#     operation_system = selected_reglet.get('image', {}).get('name')
#
#
#     # Возврат собранной информации
#     return templates.TemplateResponse("index.html", {
#         "request": request,
#         "operation_system": operation_system,
#         "ram": ram,
#         "disk": disk,
#         "status": status,
#         "region_slug": region_slug,
#         "name": name,
#         "hourly_cost": hourly_cost,
#         "monthly_cost": monthly_cost,
#         "total_balance": total_balance,
#     })



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
async def execute_command_page(request: Request, server_id: int, db: Session = Depends(get_db)):
    # Получаем информацию о сервере из базы
    server = db.query(Server).filter(Server.id == server_id).first()

    if not server:
        raise HTTPException(status_code=404, detail="Сервер не найден")

    reglets_url = 'https://api.cloudvps.reg.ru/v1/reglets'
    balance_data_url = 'https://api.cloudvps.reg.ru/v1/balance_data'

    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json'
    }

    async with httpx.AsyncClient() as client:
        reglets_response = await client.get(reglets_url, headers=headers)
        balance_response = await client.get(balance_data_url, headers=headers)

    if reglets_response.status_code != 200:
        raise HTTPException(status_code=reglets_response.status_code, detail="Ошибка при получении реглетов")

    if balance_response.status_code != 200:
        raise HTTPException(status_code=balance_response.status_code, detail="Ошибка при получении данных о балансе")

    balance_data = balance_response.json().get("balance_data", {})
    total_balance = balance_data.get("balance", 0)

    # Извлекаем детализацию
    detalization = balance_data.get("detalization", [])

    # Реглеты
    reglets_data = reglets_response.json().get("reglets", [])
    print("Все реглеты:", reglets_data)  # Отладочный вывод

    # Обрабатываем индекс для поиска реглета
    index = server_id - 1  # server_id передается в качестве индекса (начиная с 1)

    # Проверяем, существует ли реглет по индексу
    if 0 <= index < len(reglets_data):
        selected_reglet = reglets_data[index]
        name = selected_reglet.get("name")
        ram = selected_reglet.get("memory")
        disk = selected_reglet.get("disk")
        status = selected_reglet.get("status")
        region_slug = selected_reglet.get("region_slug")
        operation_system = selected_reglet.get('image', {}).get('name')

        # Ищем информацию о стоимости конкретного реглета
        for item in detalization:
            if item.get('name') == name:  # Или можно использовать другой уникальный идентификатор
                hourly_cost = float(item.get("price", 0))
                monthly_cost = float(item.get("price_month", 0))
                break
        else:
            hourly_cost = 0
            monthly_cost = 0
    else:
        name = ram = disk = status = region_slug = operation_system = "Не найдено"
        hourly_cost = monthly_cost = 0  # По умолчанию, если реглет не найден

    commands_results = db.query(CommandResult).filter(CommandResult.server_id == server_id).all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "commands_results": commands_results,
        "servers": db.query(Server).all(),
        "current_server": server,
        "operation_system": operation_system,
        "ram": ram,
        "disk": disk,
        "status": status,
        "region_slug": region_slug,
        "name": name,
        "hourly_cost": hourly_cost,
        "monthly_cost": monthly_cost,
        "total_balance": total_balance,
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
