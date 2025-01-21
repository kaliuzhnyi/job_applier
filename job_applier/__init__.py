import logging
import os
from typing import List

import openai
from dotenv import load_dotenv

from job_applier import databese
from job_applier.models.applicant import Applicant
from job_applier.application import Application, apply, log_cover_letter, create_cover_letter, create_cover_letter_file, \
    CoverLetter, log_application
from job_applier.canada.jobbank import find_jobs
from job_applier.models.job import log_jobs, save_jobs
from job_applier.settings import SETTINGS


def init() -> None:
    init_logging()
    init_envs()
    init_openai()
    init_db()
    logging.info("App successfully initialized!")


def init_logging() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def init_envs() -> None:
    if load_dotenv():
        logging.info("Envs successfully initialized.")


def init_openai() -> None:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        openai.api_key = openai_api_key
        logging.info("OpenAI API successfully initialized. API key set.")
    else:
        raise ValueError("OPENAI_API_KEY not found in .env file")


def init_db() -> None:
    databese.init_db()


def start() -> None:
    logging.info("App started...")
    start_job_founding()


def start_job_founding() -> None:
    current_applicant = Applicant()
    if current_applicant:
        logging.info(f"Applicant successfully initialized. Data - {current_applicant}")

    # Find jobs
    logging.info(
        f"Start searching for jobs, title: {SETTINGS['job']['title']}, location: {SETTINGS['job']['location']}")
    jobs = find_jobs(SETTINGS['job']['title'], SETTINGS['job']['location'])
    logging.info("Found %s jobs", len(jobs))

    # Log jobs
    logging.info(f"Log jobs, file: {SETTINGS['log']['jobs']['file']}")
    log_jobs(jobs)
    save_jobs(jobs)

    # Create applications
    logging.info("Start creation cover letters for jobs...")
    cover_letters: List[CoverLetter] = []
    applications: List[Application] = []
    for current_job in jobs:
        current_application = Application(
            applicant=current_applicant,
            job=current_job,
            email_to="kalyuzhny.ivan@gmail.com"
        )
        applications.append(current_application)
        cover_letters.append(current_application.cover_letter)

    # Log applications(cover letters)
    logging.info(f"Log cover letters, file: {SETTINGS['log']['cover_letters']['file']}")
    for value in cover_letters:
        log_cover_letter(job=value.job, text=value.text)

    # Apply for jobs
    logging.info("Start applying for jobs...")
    for value in applications:
        if not value.email_to:
            continue
        try:
            apply(value)
            value.applied = True
            logging.info(f"Successfully applied for job({value.job.title}, {value.job.source_id}, {value.job.email})")
        except Exception as e:
            value.applied = False
            logging.info(
                f"An error occurred during the application process for job({value.job.title}, {value.job.source_id}, {value.job.email})")
            logging.error(f"Error during : {e}")
        log_application(value)
