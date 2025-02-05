import json
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
class ResumeModel(FileModel):

    def create_text(self) -> Optional[str]:

        if self.applicant.resume_file_path:
            return None

        developer_content = SETTINGS["openai"]["create_applicant_resume"]["developer_content"]
        developer_content = developer_content.format(job=self.job, applicant=self.applicant)
        user_content = SETTINGS["openai"]["create_applicant_resume"]["user_content"]
        user_content = user_content.format(
            job=self.job,
            applicant=self.applicant,
            json=json.dumps({"applicant": SETTINGS["applicant"]})
        )

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

        if self.applicant.resume_file_path:
            return self.applicant.resume_file_path

        template_file_path = SETTINGS['resume']['template']['file']
        template_file_name, template_file_ext = os.path.splitext(os.path.basename(template_file_path))

        # Define log dir for saving resumes
        log_file = SETTINGS['log']['resumes']['file']
        if log_file:
            log_dir = os.path.dirname(log_file)
        else:
            log_dir = tempfile.gettempdir()
        log_file_name = f"{self.applicant.first_name.capitalize()}_{self.applicant.last_name.capitalize()}_Resume_{self.job.source_id}"

        result_files = (
            os.path.join(log_dir, f"{log_file_name}{template_file_ext}"),
            os.path.join(log_dir, f"{log_file_name}.pdf")
        )

        # Fill resume with template
        text = self.text.replace("```json", "").replace("```", "")
        data = json.loads(text)
        data.update({"job": self.job})

        doc = DocxTemplate(template_file_path)
        doc.render(data)
        doc.save(result_files[0])

        # Save resume with PDF ext
        if libreoffice_available():
            convert_to_pdf_with_libreoffice(result_files[0], result_files[1])
            resume_result_file = result_files[1]
        else:
            resume_result_file = result_files[0]

        return resume_result_file


def log_resume(resume: ResumeModel) -> None:
    data = {
        'job_applicant': f"{resume.applicant.first_name} {resume.applicant.last_name}",
        'job_applicant_email': resume.applicant.email,
        'job_source': resume.job.source,
        'job_source_id': resume.job.source_id,
        'resume_text': resume.text,
        'resume_file': resume.file_path
    }
    log(SETTINGS['log']['resumes']['file'], [data])
