import os
from dataclasses import dataclass, field

from typing import Optional, TYPE_CHECKING

import yagmail
from openai import OpenAI

if TYPE_CHECKING:
    from job_applier import Applicant, Job


@dataclass
class EmailModel:
    job: "Job"
    applicant: "Applicant"
    to: Optional[str] = None
    subject: Optional[str] = None
    text: Optional[str] = None
    attachments: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.to:
            self.to = self.job.email
        if not self.subject:
            self.subject = self.create_subject()
        if not self.text:
            self.text = self.create_text()

    def create_subject(self) -> Optional[str]:
        if not self.job or not self.job.title:
            return "Application for position"
        return f"Application for {self.job.title.capitalize()} position"

    def create_text(self) -> Optional[str]:

        from job_applier import SETTINGS

        developer_content = SETTINGS["openai"]["create_applicant_email"]["developer_content"]
        developer_content = developer_content.format(job=self.job, applicant=self.applicant)
        user_content = SETTINGS["openai"]["create_applicant_email"]["user_content"]
        user_content = user_content.format(job=self.job, applicant=self.applicant)

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

        if (not chat.choices
                or not hasattr(chat.choices[0], "message")
                or not hasattr(chat.choices[0].message, "content")):
            return None

        return chat.choices[0].message.content

    def send(self) -> bool:
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
            to=self.to,
            subject=self.subject,
            contents=self.text,
            attachments=self.attachments
        )
