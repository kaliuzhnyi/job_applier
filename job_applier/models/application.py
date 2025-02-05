import logging
import os.path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, List

import sqlalchemy
import yagmail
from openai import OpenAI
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column, relationship

from job_applier.databese import Session
from job_applier.log import log
from job_applier.models.applicant import Applicant
from job_applier.models.base import Base
from job_applier.models.cover_letter import CoverLetterModel
from job_applier.models.job import Job
from job_applier.models.resume import ResumeModel
from job_applier.settings import SETTINGS


@dataclass
class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(sqlalchemy.ForeignKey("jobs.id"), nullable=False)
    applicant_id: Mapped[int] = mapped_column(sqlalchemy.ForeignKey("applicants.id"), nullable=False)
    _applied: Mapped[bool] = mapped_column("applied", sqlalchemy.Boolean, default=False)
    applied_at: Mapped[Optional[datetime]] = mapped_column(sqlalchemy.DateTime)

    job: Mapped[Job] = relationship()
    applicant: Mapped[Applicant] = relationship()

    email_to: Optional[str] = field(default=None, init=False)
    email_subject: Optional[str] = field(default=None, init=False)
    email_body: Optional[str] = field(default=None, init=False)
    resume: Optional[ResumeModel] = field(default=None, init=False)
    cover_letter: Optional[CoverLetterModel] = field(default=None, init=False)

    def __init__(
            self,
            applicant: Applicant,
            job: Job,
            email_to: Optional[str] = None,
            email_subject: Optional[str] = None,
            email_body: Optional[str] = None,
            resume: Optional[ResumeModel] = None,
            cover_letter: Optional[CoverLetterModel] = None,
            applied: bool = False,
            applied_at: datetime = None,
            **kw: Any
    ):
        super().__init__(**kw)
        self.applicant = applicant
        self.job = job
        self.email_to = email_to or job.email
        self.email_subject = email_subject or create_email_subject(job)
        self.email_body = email_body or create_email_body(job, applicant)
        self.cover_letter = cover_letter or CoverLetterModel(job=job, applicant=applicant)
        self.resume = resume or ResumeModel(job=job, applicant=applicant)
        self.applied = applied
        self.applied_at = applied_at or (datetime.now() if applied else None)

    @property
    def applied(self) -> bool:
        return self._applied

    @applied.setter
    def applied(self, value: bool) -> None:
        self._applied = value
        self.applied_at = datetime.now() if self._applied else None


def create_email_subject(job: Job) -> str:
    if not job or not job.title:
        return "Application for position"
    return f"Application for {job.title.capitalize()} position"


def create_email_body(job: Job, applicant: Applicant) -> str | None:
    developer_content = SETTINGS["openai"]["create_applicant_email"]["developer_content"]
    developer_content = developer_content.format(job=job, applicant=applicant)
    user_content = SETTINGS["openai"]["create_applicant_email"]["user_content"]
    user_content = user_content.format(job=job, applicant=applicant)

    client = OpenAI()
    chat = client.chat.completions.create(
        model=SETTINGS["openai"]["version"],
        messages=[
            {"role": "developer", "content": developer_content},
            {"role": "user", "content": user_content},
        ],
        response_format={
            "type": "text"
        },
    )

    if not len(chat.choices):
        return None

    return chat.choices[0].message.content


def apply(application: Application) -> bool:
    return send_email(
        to=application.email_to,
        subject=application.email_subject,
        body=application.email_body,
        attachments=[application.cover_letter.file_path, application.resume.file_path]
    )


def send_email(to: str, subject: str, body: str = None, attachments: list[str] = None) -> bool:
    port = os.getenv("EMAIL_PORT")
    smtp_ssl = True if os.getenv("EMAIL_PORT") == "465" else False
    yag = yagmail.SMTP(
        user=os.getenv("EMAIL_USER"),
        password=os.getenv("EMAIL_PASSWORD"),
        host=os.getenv("EMAIL_HOST"),
        port=port,
        smtp_ssl=smtp_ssl
    )
    return yag.send(
        to=to,
        subject=subject,
        contents=body,
        attachments=attachments
    )


def log_applications(applications: List[Application]) -> None:
    for application in applications:
        log_application(application)


def log_application(application: Application) -> None:
    data = {
        'job_applicant': f"{application.applicant.first_name} {application.applicant.last_name}",
        'job_applicant_email': application.applicant.email,
        'job_source': application.job.source,
        'job_source_id': application.job.source_id,
        'email_to': application.email_to,
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
