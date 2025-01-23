import logging
import os.path
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, List

import sqlalchemy
import yagmail
from docx import Document
from openai import OpenAI
from python_docx_replace import docx_replace
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column, relationship

from job_applier.databese import Session
from job_applier.log import log
from job_applier.models.applicant import Applicant
from job_applier.models.base import Base
from job_applier.models.job import Job
from job_applier.settings import SETTINGS
from job_applier.utils.convert_docx_to_pdf import convert_to_pdf_with_libreoffice, libreoffice_available


@dataclass
class Resume:
    applicant: Applicant
    job: Job
    file_path: Optional[str] = None

    def __init__(
            self,
            applicant: Applicant,
            job: Job,
            file_path: Optional[str] = None
    ):
        self.applicant = applicant
        self.job = job
        self.file_path = file_path or applicant.resume_file_path


@dataclass
class CoverLetter:
    applicant: Applicant
    job: Job
    text: Optional[str] = None
    file_path: Optional[str] = None

    def __init__(
            self,
            applicant: Applicant,
            job: Job,
            text: Optional[str] = None,
            file_path: Optional[str] = None
    ):
        self.applicant = applicant
        self.job = job
        self.text = text or create_cover_letter(job=job, applicant=applicant)
        self.file_path = file_path or create_cover_letter_file(job=job, applicant=applicant, text=self.text)


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
    resume: Optional[Resume] = field(default=None, init=False)
    cover_letter: Optional[CoverLetter] = field(default=None, init=False)

    def __init__(
            self,
            applicant: Applicant,
            job: Job,
            email_to: Optional[str] = None,
            email_subject: Optional[str] = None,
            email_body: Optional[str] = None,
            resume: Optional[Resume] = None,
            cover_letter: Optional[CoverLetter] = None,
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
        self.cover_letter = cover_letter or CoverLetter(job=job, applicant=applicant)
        self.resume = resume or Resume(job=job, applicant=applicant)
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


def create_cover_letter(job: Job, applicant: Applicant) -> str | None:
    # Generate cover letter text
    developer_content = SETTINGS["openai"]["create_applicant_cover_letter"]["developer_content"]
    developer_content = developer_content.format(job=job, applicant=applicant)
    user_content = SETTINGS["openai"]["create_applicant_cover_letter"]["user_content"]
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


def create_cover_letter_file(job: Job, applicant: Applicant, text: str) -> str | None:
    replacements = {'text': text}
    for k, v in vars(job).items():
        replacements[f"job.{k}"] = v
    for k, v in vars(applicant).items():
        replacements[f"applicant.{k}"] = v

    template_file_path = SETTINGS['cover_letter']['template']['file']
    template_file_name, template_file_ext = os.path.splitext(os.path.basename(template_file_path))

    # Define log dir for saving cover letters
    log_file = SETTINGS['log']['cover_letters']['file']
    if log_file:
        log_dir = os.path.dirname(log_file)
    else:
        log_dir = tempfile.gettempdir()
    log_file_name = f"{applicant.first_name.capitalize()}_{applicant.last_name.capitalize()}_{job.source_id}"

    result_files = (
        os.path.join(log_dir, f"{log_file_name}{template_file_ext}"),
        os.path.join(log_dir, f"{log_file_name}.pdf")
    )

    # Fill and save cover letter with template ext
    doc = Document(template_file_path)
    docx_replace(doc, **replacements)
    doc.save(result_files[0])

    # Save cover letter with PDF ext
    if libreoffice_available():
        convert_to_pdf_with_libreoffice(result_files[0], result_files[1])
        cover_letter_result_file = result_files[1]
    else:
        cover_letter_result_file = result_files[0]

    return cover_letter_result_file


def log_cover_letter(job: Job, text: str) -> None:
    data = {
        'job_id': job.source_id,
        'cover_letter_text': text
    }
    log(SETTINGS['log']['cover_letters']['file'], [data])


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
        'job_id': application.job.source_id,
        'email_to': application.email_to,
        'applied': application.applied,
        'applied_at': application.applied_at
    }
    log(SETTINGS['log']['applications']['file'], [data])


def save_applications(applications: List[Application]) -> None:
    for application in applications:
        save_application(application)


def save_application(application: Application) -> Application:
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
