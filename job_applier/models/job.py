import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column

from job_applier.databese import Session
from job_applier.log import log
from job_applier.models.base import Base
from job_applier.settings import SETTINGS

JOB_FINDERS: List = []


class SalaryType(Enum):
    HOURLY = "hourly"
    ANNUALLY = "annually"


class Workspace(Enum):
    ONSITE = "on site"
    HYBRID = "hybrid"


@dataclass
class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    link: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    source_id: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    posted_on_jb: Mapped[bool] = mapped_column(sqlalchemy.Boolean, default=False)
    title: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    date: Mapped[Optional[datetime]] = mapped_column(sqlalchemy.DateTime, nullable=True)
    business: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    salary: Mapped[float] = mapped_column(sqlalchemy.Float, default=0.0)
    salary_type: Mapped[Optional[SalaryType]] = mapped_column(sqlalchemy.Enum(SalaryType), nullable=True)
    workspace: Mapped[Optional[Workspace]] = mapped_column(sqlalchemy.Enum(Workspace), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(sqlalchemy.DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(sqlalchemy.DateTime, nullable=True)


def find_jobs() -> List[Job]:
    jobs = []

    for finder in JOB_FINDERS:
        jobs += finder(SETTINGS['job']['title'], SETTINGS['job']['location'])

    return jobs


def log_jobs(jobs: List[Job]) -> None:
    log(SETTINGS['log']['jobs']['file'], jobs)


def save_jobs(jobs: List[Job]) -> None:
    for job in jobs:
        save_job(job)


def save_job(job: Job) -> Job:
    job.updated_at = datetime.now()
    with Session() as session:
        try:
            existing_job = session.query(Job).filter_by(source=job.source, source_id=job.source_id).first()
            if existing_job:
                for key, value in vars(job).items():
                    if key != "_sa_instance_state" and key != "id" and key != "updated_at":
                        setattr(existing_job, key, value)
                session.commit()
                session.refresh(existing_job)
                for key, value in vars(existing_job).items():
                    if key != "_sa_instance_state":
                        setattr(job, key, value)
            else:
                session.add(job)
                session.commit()
                session.refresh(job)
            return job
        except SQLAlchemyError as e:
            session.rollback()
            logging.error(f"Database error while saving or updating job: {e}")
        except Exception as e:
            logging.error(f"Unexpected error while saving or updating job: {e}")
