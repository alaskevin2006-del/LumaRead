import uuid
from datetime import datetime,timezone
from sqlalchemy import String,Boolean,DateTime,ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base

def uid():return str(uuid.uuid4())
def now():return datetime.now(timezone.utc).replace(tzinfo=None)

class User(Base):
    __tablename__='users'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    username:Mapped[str]=mapped_column(String(32),unique=True)
    name:Mapped[str]=mapped_column(String(30))
    password_hash:Mapped[str]=mapped_column(String(256))
    role:Mapped[str]=mapped_column(String(10),default='student')
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    must_change_password:Mapped[bool]=mapped_column(Boolean,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=now)

class AuthSession(Base):
    __tablename__='auth_sessions'
    token_hash:Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    expires_at:Mapped[datetime]=mapped_column(DateTime)
