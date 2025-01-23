from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from job_applier.models.base import Base
from job_applier.settings import SETTINGS

DATABASE_URL = SETTINGS["database"]["sqlite"]["path"]
DATABASE_USE = bool(DATABASE_URL)

if DATABASE_USE:
    engine = create_engine(DATABASE_URL, echo=True)
    Session = sessionmaker(engine)


def init_db():
    if DATABASE_USE:
        Base.metadata.create_all(bind=engine)
