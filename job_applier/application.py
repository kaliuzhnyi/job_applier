import csv
import datetime
import os.path

import yagmail
from docx import Document
from openai import OpenAI
from python_docx_replace import docx_replace

from job_applier.applicant import Applicant
from job_applier.job import Job
from job_applier.settings import SETTINGS
from job_applier.utils.convert_docx_to_pdf import convert_to_pdf_with_libreoffice, libreoffice_available


class CoverLetter:
    def __init__(self,
                 applicant: Applicant,
                 job: Job,
                 text: str = None,
                 file_path: str = None
                 ):
        self.applicant = applicant
        self.job = job
        self.text = text \
            if text \
            else "" \
            if file_path \
            else create_cover_letter(job=job, applicant=applicant)
        self.file_path = file_path if file_path else create_cover_letter_file(job=job,
                                                                              applicant=applicant,
                                                                              text=self.text)


class Application:
    def __init__(self,
                 applicant: Applicant,
                 job: Job,
                 email_to: str = None,
                 email_subject: str = None,
                 email_body: str = None,
                 resume: str = None,
                 cover_letter: CoverLetter = None,
                 applied: bool = False
                 ):
        self.applicant = applicant
        self.job = job
        self.email_to = email_to if email_to else self.job.email
        self.email_subject = email_subject if email_subject else create_email_subject(job)
        self.email_body = email_body if email_body else create_email_body(job, applicant)
        self.cover_letter = cover_letter \
            if cover_letter \
            else CoverLetter(job=job, applicant=applicant, file_path=self.applicant.cover_letter_file_path) \
            if self.applicant.cover_letter_file_path \
            else CoverLetter(job=job, applicant=applicant)
        self.resume = resume if resume else applicant.resume
        self.applied = applied


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
    template_file_dir = os.path.dirname(template_file_path)
    template_file_name, template_file_ext = os.path.splitext(os.path.basename(template_file_path))

    result_file_suffix = f".{job.id}"
    result_files = (
        os.path.join(template_file_dir, f"{template_file_name}{result_file_suffix}{template_file_ext}"),
        os.path.join(template_file_dir, f"{template_file_name}{result_file_suffix}.pdf")
    )

    doc = Document(template_file_path)
    docx_replace(doc, **replacements)
    doc.save(result_files[0])

    if libreoffice_available():
        convert_to_pdf_with_libreoffice(result_files[0], result_files[1])
        cover_letter_result_file = result_files[1]
    else:
        cover_letter_result_file = result_files[0]

    return cover_letter_result_file


def log_cover_letter(job: Job, text: str) -> None:
    log_file = SETTINGS['log']['cover_letters']['file']
    if not log_file:
        return

    file_exists = os.path.isfile(log_file)
    data = {
        'job_id': job.id,
        'cover_letter_text': text
    }
    with open(log_file, "a", newline='') as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        if not file_exists or os.stat(log_file).st_size == 0:
            writer.writeheader()
        writer.writerow(data)


def apply(application: Application) -> bool:
    return send_email(to=application.email_to,
                      subject=application.email_subject,
                      body=application.email_body,
                      attachments=[application.cover_letter.file_path, application.resume]
                      )


def send_email(to: str, subject: str, body: str = None, attachments: list[str] = None) -> bool:
    yag = yagmail.SMTP(os.getenv("EMAIL_USER"),
                       os.getenv("EMAIL_PASSWORD"),
                       os.getenv("EMAIL_HOST"),
                       os.getenv("EMAIL_PORT")
                       )
    return yag.send(to=to,
                    subject=subject,
                    contents=body,
                    attachments=attachments
                    )


def log_application(application: Application) -> None:
    log_file = SETTINGS['log']['applications']['file']
    if not log_file:
        return

    file_exists = os.path.isfile(log_file)
    data = {
        'datetime': datetime.datetime.now(),
        'job_id': application.job.id,
        'email_to': application.email_to,
        'applied': application.applied
    }
    with open(log_file, "a", newline='') as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        if not file_exists or os.stat(log_file).st_size == 0:
            writer.writeheader()
        writer.writerow(data)
