import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column, relationship

from job_applier.databese import Session
from job_applier.log import log
from job_applier.models.applicant import Applicant
from job_applier.models.base import Base
from job_applier.models.cover_letter import CoverLetterModel
from job_applier.models.email import EmailModel
from job_applier.models.job import Job
from job_applier.models.resume import ResumeModel
from job_applier.settings import SETTINGS


@dataclass
class Application(Base):
    __tablename__ = "applications"

    job: Mapped[Job] = relationship()
    applicant: Mapped[Applicant] = relationship()

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(sqlalchemy.ForeignKey("jobs.id"), nullable=False)
    applicant_id: Mapped[int] = mapped_column(sqlalchemy.ForeignKey("applicants.id"), nullable=False)
    _applied: Mapped[bool] = mapped_column("applied", sqlalchemy.Boolean, default=False)
    applied_at: Mapped[Optional[datetime]] = mapped_column(sqlalchemy.DateTime)

    email: Optional[EmailModel] = None
    resume: Optional[ResumeModel] = None
    cover_letter: Optional[CoverLetterModel] = None

    def __post_init__(self) -> None:

        if not self.cover_letter:
            self.cover_letter = CoverLetterModel(job=self.job, applicant=self.applicant)
            if self.email and self.cover_letter.file_path not in self.email.attachments:
                self.email.attachments.append(self.cover_letter.file_path)

        if not self.resume:
            self.resume = ResumeModel(job=self.job, applicant=self.applicant)
            if self.email and self.resume.file_path not in self.email.attachments:
                self.email.attachments.append(self.resume.file_path)

        if not self.email:
            self.email = EmailModel(self.job, self.applicant)
            self.email.attachments.append(self.cover_letter.file_path)
            self.email.attachments.append(self.resume.file_path)

        if not self.applied_at and self.applied:
            self.applied_at = datetime.now()

    @property
    def applied(self) -> bool:
        return self._applied

    @applied.setter
    def applied(self, value: bool) -> None:
        self._applied = value
        self.applied_at = datetime.now() if self._applied else None

    def apply(self) -> bool:
        self.applied = self.email.send()
        return self.applied


def log_applications(applications: List[Application]) -> None:
    for application in applications:
        log_application(application)


def log_application(application: Application) -> None:
    data = {
        'job_applicant': f"{application.applicant.first_name} {application.applicant.last_name}",
        'job_applicant_email': application.applicant.email,
        'job_source': application.job.source,
        'job_source_id': application.job.source_id,
        'email_to': application.email.to,
        'applied': application.applied,
        'applied_at': application.applied_at
    }
    log(SETTINGS['log']['applications']['file'], [data])


def save_applications(applications: List[Application]) -> None:
    for application in applications:
        save_application(application)


def save_application(application: Application) -> Optional[Application]:
    with Session() as session:

        application.job = session.merge(application.job)
        application.applicant = session.merge(application.applicant)

        try:
            existing_application = session.query(Application).filter_by(
                job_id=application.job_id,
                applicant_id=application.applicant_id
            ).first()
            if existing_application:
                fields_to_update = ["applied", "applied_at"]
                for key in fields_to_update:
                    setattr(existing_application, key, getattr(application, key))
                session.commit()
                session.refresh(existing_application)
                for key, value in vars(existing_application).items():
                    if key != "_sa_instance_state":
                        setattr(application, key, value)
            else:
                session.add(application)
                session.commit()
                session.refresh(application)
            return application
        except SQLAlchemyError as e:
            session.rollback()
            logging.error(f"Database error while saving or updating application: {e}")
        except Exception as e:
            logging.error(f"Unexpected error while saving or updating application: {e}")


def check_application(application: Application = None, job: Job = None, applicant: Applicant = None) -> Optional[
    Application]:
    job = job or application.job
    applicant = applicant or application.applicant

    with Session() as session:
        try:
            existing_application = session.query(Application).filter(
                Application.job_id == job.id,
                Application.applicant_id == applicant.id,
                Application._applied == True,
                Application.applied_at.isnot(None)
            ).first()
            return existing_application
        except SQLAlchemyError as e:
            logging.error(f"Database error while checking application: {e}")
        except Exception as e:
            logging.error(f"Unexpected error while checking application: {e}")

    return None
