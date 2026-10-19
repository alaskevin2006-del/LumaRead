import threading
from collections import defaultdict,deque
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse
from .config import Settings
from .db import Base,make_db
from . import models,auth

def create_app(settings=None):
    settings=settings or Settings()
    Path(settings.media_dir).mkdir(parents=True,exist_ok=True)
    if settings.database_url.startswith('sqlite:///'):Path(settings.database_url.removeprefix('sqlite:///')).parent.mkdir(parents=True,exist_ok=True)
    engine,factory=make_db(settings.database_url)
    if settings.testing:Base.metadata.create_all(engine)
    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()
    app=FastAPI(title='LumaRead',lifespan=lifespan,docs_url='/api/docs' if settings.testing else None,redoc_url=None)
    app.state.settings=settings;app.state.db=factory;app.state.engine=engine
    app.state.seed_admin=lambda u,p:auth.seed_admin(factory,u,p)
    app.state.login_lock=threading.Lock();app.state.login_attempts=defaultdict(deque)
    app.state.dummy_hash=auth.hasher.hash('not-a-real-password')
    @app.middleware('http')
    async def security(request:Request,call_next):
        if request.method in ['POST','PATCH','PUT','DELETE']:
            origin=request.headers.get('origin')
            if request.headers.get('x-lumaread')!='1' or (origin and origin!=settings.public_origin and not settings.testing):
                return JSONResponse({'detail':'请求来源校验失败，请刷新页面'},status_code=403)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Cache-Control']='no-store'
        return response
    app.include_router(auth.router)
    @app.get('/api/health')
    def health():
        from sqlalchemy import text
        with factory() as db:db.execute(text('SELECT 1'))
        return {'status':'ok','service':'lumaread','speech_provider':settings.speech_provider}
    @app.get('/api/books')
    def books(user:auth.Current):return []
    return app
