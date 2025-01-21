from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from job_applier.models.base import Base
from job_applier.settings import SETTINGS

DATABASE_URL = SETTINGS["database"]["sqlite"]["path"]
engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(engine)


def init_db():
    Base.metadata.create_all(bind=engine)
