from dataclasses import dataclass
from typing import Optional, Any

import sqlalchemy
from sqlalchemy.orm import mapped_column, Mapped

from job_applier.models.base import Base
from job_applier.settings import SETTINGS


@dataclass
class Applicant(Base):
    __tablename__ = "applicants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    first_name: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    resume_file_path: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    cover_letter_file_path: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)

    def __init__(
            self,
            first_name: str = None,
            last_name: str = None,
            email: str = None,
            phone: str = None,
            address: str = None,
            resume_file_path: str = None,
            cover_letter_file_path: str = None,
            **kw: Any
    ):
        super().__init__(**kw)
        self.first_name = first_name or SETTINGS['applicant']['first_name']
        self.last_name = last_name or SETTINGS['applicant']['last_name']
        self.email = email or SETTINGS['applicant']['contacts']['email']
        self.phone = phone or SETTINGS['applicant']['contacts']['phone']
        self.address = address or SETTINGS['applicant']['contacts']['address']
        self.resume_file_path = resume_file_path or SETTINGS['applicant']['resume']['file']
        self.cover_letter_file_path = cover_letter_file_path or SETTINGS['applicant']['cover_letter']['file']
