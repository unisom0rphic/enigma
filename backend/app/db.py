from sqlalchemy import create_engine

from .config import URL_DB

engine = create_engine(URL_DB)
