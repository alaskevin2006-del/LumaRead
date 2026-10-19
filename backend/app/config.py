from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config=SettingsConfigDict(env_prefix='LUMA_',env_file='.env',extra='ignore')
    database_url:str='sqlite:///./data/lumaread.db'
    media_dir:str='./data/media'
    secure_cookies:bool=True
    testing:bool=False
    public_origin:str='https://124.221.230.69:8443'
    speech_provider:str='disabled'
    speech_url:str='http://evaluator:8000'
    reference_url:str='http://scorer:8000'
    azure_key:str=''
    azure_region:str=''
    green_threshold:int=80
    orange_threshold:int=60
    retention_days:int=30
