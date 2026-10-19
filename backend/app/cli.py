import argparse,getpass,os,secrets
from datetime import timedelta
from pathlib import Path
from sqlalchemy import select,delete
from .main import create_app
from .auth import seed_admin
from .models import MediaAsset,now,AuthSession

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['admin','cleanup']);p.add_argument('--username',default='admin');args=p.parse_args();app=create_app()
    if args.command=='admin':
        password=os.environ.get('LUMA_INITIAL_ADMIN_PASSWORD') or getpass.getpass('Initial administrator password: ')
        if len(password)<12:raise SystemExit('Use at least 12 characters')
        seed_admin(app.state.db,args.username,password);print('Administrator initialized (existing account is never overwritten).')
    else:
        with app.state.db() as db:
            assets=db.scalars(select(MediaAsset).where(MediaAsset.kind=='recording',MediaAsset.created_at<now()-timedelta(days=app.state.settings.retention_days)))
            count=0
            for a in assets:
                path=Path(app.state.settings.media_dir)/a.path
                if path.exists():path.unlink();count+=1
            db.execute(delete(AuthSession).where(AuthSession.expires_at<now()));db.commit();print(f'Expired recordings removed: {count}')
if __name__=='__main__':main()
