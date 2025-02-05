import os
import tempfile
from dataclasses import dataclass
from typing import Optional

from docxtpl import DocxTemplate
from openai import OpenAI

from job_applier.log import log
from job_applier.models.file import FileModel
from job_applier.settings import SETTINGS
from job_applier.utils.convert_docx_to_pdf import libreoffice_available, convert_to_pdf_with_libreoffice


@dataclass
class CoverLetterModel(FileModel):

    def create_text(self) -> Optional[str]:

        if self.applicant.cover_letter_file_path:
            return None

        # Generate cover letter text
        developer_content = SETTINGS["openai"]["create_applicant_cover_letter"]["developer_content"]
        developer_content = developer_content.format(job=self.job, applicant=self.applicant)
        user_content = SETTINGS["openai"]["create_applicant_cover_letter"]["user_content"]
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

    def create_file(self) -> Optional[str]:

        if self.applicant.cover_letter_file_path:
            return self.applicant.cover_letter_file_path

        template_file_path = SETTINGS['cover_letter']['template']['file']
        template_file_name, template_file_ext = os.path.splitext(os.path.basename(template_file_path))

        # Define log dir for saving cover letters
        log_file = SETTINGS['log']['cover_letters']['file']
        if log_file:
            log_dir = os.path.dirname(log_file)
        else:
            log_dir = tempfile.gettempdir()
        log_file_name = f"{self.applicant.first_name.capitalize()}_{self.applicant.last_name.capitalize()}_Cover_Letter_{self.job.source_id}"

        result_files = (
            os.path.join(log_dir, f"{log_file_name}{template_file_ext}"),
            os.path.join(log_dir, f"{log_file_name}.pdf")
        )

        # Fill and save cover letter with template ext
        data = {
            'text': self.text,
            'job': self.job,
            'applicant': self.applicant
        }

        doc = DocxTemplate(template_file_path)
        doc.render(data)
        doc.save(result_files[0])

        # Save cover letter with PDF ext
        if libreoffice_available():
            convert_to_pdf_with_libreoffice(result_files[0], result_files[1])
            cover_letter_result_file = result_files[1]
        else:
            cover_letter_result_file = result_files[0]

        return cover_letter_result_file


def log_cover_letter(cover_letter: CoverLetterModel) -> None:
    data = {
        'job_applicant': f"{cover_letter.applicant.first_name} {cover_letter.applicant.last_name}",
        'job_applicant_email': cover_letter.applicant.email,
        'job_source': cover_letter.job.source,
        'job_source_id': cover_letter.job.source_id,
        'cover_letter_text': cover_letter.text,
        'cover_letter_file': cover_letter.file_path
    }
    log(SETTINGS['log']['cover_letters']['file'], [data])
