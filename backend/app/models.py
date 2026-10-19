import uuid
from datetime import datetime,timezone
from sqlalchemy import String,Boolean,DateTime,ForeignKey,Integer,Text,JSON,UniqueConstraint,Date,Float
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

class Book(Base):
    __tablename__='books'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    status:Mapped[str]=mapped_column(String(20),default='draft')
    published_version_id:Mapped[str|None]=mapped_column(String(36),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=now)

class BookVersion(Base):
    __tablename__='book_versions'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    book_id:Mapped[str]=mapped_column(ForeignKey('books.id'),index=True)
    number:Mapped[int]=mapped_column(Integer,default=1)
    published:Mapped[bool]=mapped_column(Boolean,default=False)
    title:Mapped[str]=mapped_column(String(120))
    level:Mapped[str]=mapped_column(String(1),default='A')
    description:Mapped[str]=mapped_column(Text,default='')
    cover_id:Mapped[str|None]=mapped_column(String(36),nullable=True)
    updated_at:Mapped[datetime]=mapped_column(DateTime,default=now,onupdate=now)
    __table_args__=(UniqueConstraint('book_id','number'),)

class Page(Base):
    __tablename__='pages'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    version_id:Mapped[str]=mapped_column(ForeignKey('book_versions.id'),index=True)
    position:Mapped[int]=mapped_column(Integer)
    kind:Mapped[str]=mapped_column(String(20),default='practice')
    text:Mapped[str]=mapped_column(Text,default='')
    image_id:Mapped[str|None]=mapped_column(String(36),nullable=True)
    audio_id:Mapped[str|None]=mapped_column(String(36),nullable=True)
    audio_start_ms:Mapped[int]=mapped_column(Integer,default=0)
    audio_end_ms:Mapped[int|None]=mapped_column(Integer,nullable=True)
    reviewed:Mapped[bool]=mapped_column(Boolean,default=False)
    __table_args__=(UniqueConstraint('version_id','position'),)

class MediaAsset(Base):
    __tablename__='media_assets'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    version_id:Mapped[str|None]=mapped_column(String(36),nullable=True,index=True)
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    kind:Mapped[str]=mapped_column(String(20))
    filename:Mapped[str]=mapped_column(String(160))
    path:Mapped[str]=mapped_column(String(160))
    mime:Mapped[str]=mapped_column(String(80))
    duration_ms:Mapped[int|None]=mapped_column(Integer,nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=now)

class Job(Base):
    __tablename__='jobs'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    kind:Mapped[str]=mapped_column(String(20))
    status:Mapped[str]=mapped_column(String(20),default='queued',index=True)
    payload:Mapped[dict]=mapped_column(JSON,default=dict)
    result:Mapped[dict]=mapped_column(JSON,default=dict)
    error:Mapped[str]=mapped_column(Text,default='')
    progress:Mapped[int]=mapped_column(Integer,default=0)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=now)
    started_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)

class ReadingSession(Base):
    __tablename__='reading_sessions'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    book_id:Mapped[str]=mapped_column(ForeignKey('books.id'))
    version_id:Mapped[str]=mapped_column(ForeignKey('book_versions.id'))
    current_page:Mapped[int]=mapped_column(Integer,default=1)
    active_key:Mapped[str|None]=mapped_column(String(80),unique=True,nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=now)
    completed_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)

class ReadingAttempt(Base):
    __tablename__='reading_attempts'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    session_id:Mapped[str]=mapped_column(ForeignKey('reading_sessions.id'),index=True)
    page_id:Mapped[str]=mapped_column(ForeignKey('pages.id'))
    media_id:Mapped[str]=mapped_column(String(36))
    job_id:Mapped[str]=mapped_column(String(36))
    idempotency_key:Mapped[str]=mapped_column(String(80))
    status:Mapped[str]=mapped_column(String(20),default='queued')
    result:Mapped[dict]=mapped_column(JSON,default=dict)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=now)
    __table_args__=(UniqueConstraint('user_id','idempotency_key'),)

class Checkin(Base):
    __tablename__='checkins'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    user_id:Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    date:Mapped[__import__('datetime').date]=mapped_column(Date)
    __table_args__=(UniqueConstraint('user_id','date'),)
