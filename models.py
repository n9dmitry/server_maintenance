# from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker, relationship
#
# DATABASE_URL = "sqlite:///./servers.db"
#
# Base = declarative_base()
# engine = create_engine(DATABASE_URL)
#
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#
# class Server(Base):
#     __tablename__ = "servers"
#
#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String, index=True)
#     ip = Column(String, unique=True)
#     login = Column(String)
#     password = Column(String)
#
#     commands_results = relationship("CommandResult", back_populates="server")
#
# class CommandResult(Base):
#     __tablename__ = "command_results"
#
#     id = Column(Integer, primary_key=True, index=True)
#     command = Column(String, index=True)
#     result = Column(String)
#     server_id = Column(Integer, ForeignKey('servers.id'))
#
#     server = relationship("Server", back_populates="commands_results")
#
# class User(Base):
#     __tablename__ = "users"
#
#     id = Column(Integer, primary_key=True, index=True)
#     username = Column(String, index=True)
#     lastname = Column(String, index=True)
#     nickname = Column(String, unique=True, index=True)
#     email = Column(String, unique=True, index=True)
#     password = Column(String)
#
# def init_db():
#     db = SessionLocal()
#     user = db.query(User).filter(User.username == "admin").first()
#     if not user:
#         new_user = User(username="admin", password="admin")
#         db.add(new_user)
#         db.commit()
#     db.close()
#
# if __name__ == "__main__":
#     Base.metadata.create_all(bind=engine)

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = "sqlite:///./servers.db"

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

    commands_results = relationship("CommandResult", back_populates="server")

class CommandResult(Base):
    __tablename__ = "command_results"

    id = Column(Integer, primary_key=True, index=True)
    command = Column(String, index=True)
    result = Column(String)
    timestamp = Column(DateTime)
    server_id = Column(Integer, ForeignKey('servers.id'))

    server = relationship("Server", back_populates="commands_results")



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

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
