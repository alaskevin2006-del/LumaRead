from sqlalchemy import create_engine,event
from sqlalchemy.orm import DeclarativeBase,sessionmaker

class Base(DeclarativeBase):pass

def make_db(url):
    engine=create_engine(url,connect_args={'check_same_thread':False,'timeout':30} if url.startswith('sqlite') else {},pool_pre_ping=True)
    if url.startswith('sqlite'):
        @event.listens_for(engine,'connect')
        def configure(conn,record):
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('PRAGMA journal_mode=WAL')
    return engine,sessionmaker(engine,expire_on_commit=False)

def get_db(request):
    with request.app.state.db() as db:yield db
