from alembic import context
from app.config import Settings
from app.db import Base,make_db
from app import models
config=context.config
if context.is_offline_mode():
    context.configure(url=Settings().database_url,target_metadata=Base.metadata,literal_binds=True)
    with context.begin_transaction():context.run_migrations()
else:
    engine,_=make_db(Settings().database_url)
    with engine.connect() as connection:
        context.configure(connection=connection,target_metadata=Base.metadata,compare_type=True)
        with context.begin_transaction():context.run_migrations()
