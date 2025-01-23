import logging
import os
from typing import List

import openai
from dotenv import load_dotenv

from job_applier import databese, log, finders
from job_applier.databese import DATABASE_USE
from job_applier.log import logger
from job_applier.models.applicant import Applicant, save_applicant, log_applicant
from job_applier.models.application import Application, apply, log_cover_letter, create_cover_letter, \
    create_cover_letter_file, \
    CoverLetter, log_application, save_application, check_application, save_applications, log_applications
from job_applier.models.job import find_jobs, log_jobs, save_jobs, Job, JOB_FINDERS
from job_applier.settings import SETTINGS


def init() -> None:
    init_logging()
    init_envs()
    init_openai()
    init_db()
    logging.info("App successfully initialized!")


def init_logging() -> None:
    log.init_logging()


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
    applicant = create_applicant()
    jobs = find_and_save_jobs()

    if jobs:
        applications = create_applications(applicant=applicant, jobs=jobs)
        if applications and SETTINGS["job"]["applying"]:
            process_applications(applications)


def create_applicant() -> Applicant:
    logger.info(f"Applicant initializing...")

    applicant = Applicant()
    logger.info(f"Applicant successfully initialized: {applicant}")

    log_file = SETTINGS['log']['applicants']['file']
    if log_file:
        log_applicant(applicant)
        logger.info(f"Applicant is logged in the file: {log_file}")

    if DATABASE_USE:
        save_applicant(applicant)
        logger.info(f"Applicant successfully saved/updated in database.")

    return applicant


def find_and_save_jobs() -> List[Job]:
    logger.info(f"Start finding jobs, title: {SETTINGS['job']['title']}, location: {SETTINGS['job']['location']}")

    JOB_FINDERS.append(finders.canada.jobbank.find_jobs)

    # Find jobs
    jobs = find_jobs()
    logger.info(f"Jobs found: {len(jobs)}")

    if jobs:

        # Log jobs
        log_file = SETTINGS['log']['jobs']['file']
        if log_file:
            log_jobs(jobs)
            logger.info(f"Jobs are logged in the file: {log_file}")

        # Save/update jobs
        if DATABASE_USE:
            save_jobs(jobs)
            logger.info("Jobs are saved in the database.")

    return jobs


def create_applications(applicant: Applicant, jobs: List[Job]) -> List[Application]:
    logger.info("Start creation cover letters for jobs...")

    # Create applications
    cover_letters: List[CoverLetter] = []
    applications: List[Application] = []
    for current_job in jobs:

        existing_application = check_application(job=current_job, applicant=applicant)
        if existing_application:
            logger.info(
                f"Applicant {applicant} already applied to job {current_job} at {existing_application.applied_at}")
            continue

        current_application = Application(
            applicant=applicant,
            job=current_job,
            email_to="kalyuzhny.ivan@gmail.com"
        )
        applications.append(current_application)
        cover_letters.append(current_application.cover_letter)

    # Log applications(cover letters)
    log_file = SETTINGS['log']['cover_letters']['file']
    if cover_letters and log_file:
        for cover_letter in cover_letters:
            log_cover_letter(job=cover_letter.job, text=cover_letter.text)
        logger.info(f"Cover letters are logged in the file: {log_file}")

    return applications


def process_applications(applications: List[Application]) -> None:
    logger.info("Start applying for jobs...")

    # Apply for jobs
    for application in applications:
        if not application.email_to:
            continue
        try:
            apply(application)
            application.applied = True
            logger.info(
                f"Successfully applied for job({application.job.title}, {application.job.source_id}, {application.job.email})")
        except Exception as e:
            application.applied = False
            logger.info(
                f"An error occurred during the application process for job({application.job.title}, {application.job.source_id}, {application.job.email})")
            logger.error(f"Error during : {e}")

    log_file = SETTINGS['log']['applications']['file']
    if log_file:
        log_applications(applications)
        logger.info(f"Applications are logged in the file: {log_file}")

    if DATABASE_USE:
        save_applications(applications)
        logger.info("Applications are saved in the database.")
