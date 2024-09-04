from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Создаем базу данных и определяем базовый класс для моделей
DATABASE_URL = "sqlite:///./servers.db"  # Замените путь, если необходимо

Base = declarative_base()
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    ip = Column(String, unique=True)
    login = Column(String)
    password = Column(String)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    lastname = Column(String, index=True)
    nickname = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)

def init_db():
    db = SessionLocal()
    user = db.query(User).filter(User.username == "admin").first()
    if not user:
        new_user = User(username="admin", password="admin")
        db.add(new_user)
        db.commit()
    db.close()

# Создаем таблицы в базе данных
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
