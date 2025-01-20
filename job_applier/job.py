import csv
from datetime import datetime
from enum import Enum
from typing import List

from job_applier.settings import SETTINGS

JOB_FINDERS: List = []


class SalaryType(Enum):
    HOURLY = "hourly"
    ANNUALLY = "annually"


class Workspace(Enum):
    ONSITE = "on site"
    HYBRID = "hybrid"


class Job:
    def __init__(
            self,
            link: str = None,
            id: str = None,
            source: str = None,
            posted_on_jb: bool = False,
            title: str = None,
            description: str = None,
            date: datetime = None,
            business: str = None,
            location: str = None,
            salary: float = 0.0,
            salary_type: str = SalaryType,
            workspace: Workspace = None,
            email: str = None,
    ):
        self.link = link
        self.id = id
        self.source = source
        self.posted_on_jb = posted_on_jb
        self.title = title
        self.description = description
        self.business = business
        self.location = location
        self.salary = salary
        self.salary_type = salary_type
        self.workspace = workspace
        self.email = email
        self.date = date

    def __str__(self):
        return (
            f"Title: {self.title}\n"
            f"Description: {self.description}\n"
            f"Date: {self.date}\n"
            f"Business: {self.business}\n"
            f"Location: {self.location}\n"
            f"Salary: {self.salary:.2f} ({self.salary_type.value if self.salary_type else ''})\n"
            f"Workspace: {self.workspace}\n"
            f"Link: {self.link}\n"
            f"Posted on Job Bank: {'Yes' if self.posted_on_jb else 'No'}\n"
            f"Email: {self.email}"
        )


def find_jobs() -> List[Job]:
    jobs = []

    for finder in JOB_FINDERS:
        jobs += finder(SETTINGS['job']['title'], SETTINGS['job']['location'])

    return jobs


def log_jobs(jobs: List[Job]) -> None:
    log_file = SETTINGS['log']['jobs']['file']
    if not log_file:
        return

    with open(log_file, "w", newline='') as file:
        writer = csv.DictWriter(file, fieldnames=vars(jobs[0]).keys())
        writer.writeheader()
        for job in jobs:
            writer.writerow(vars(job))
