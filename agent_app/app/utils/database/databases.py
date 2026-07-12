from functools import wraps
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


DATABASE_URL = "sqlite:////home/xentellion/mas/agent_app/data/database.sqlite3"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


# Take note that this guy ONLY works for class methods
def with_orm_session(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with SessionLocal() as session:
            result = method(self, session, *args, **kwargs)
        return result

    return wrapper
