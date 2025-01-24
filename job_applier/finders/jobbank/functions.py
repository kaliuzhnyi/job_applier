import random
import re
import urllib.parse
from datetime import datetime
from enum import Enum
from time import sleep

import requests
from bs4 import BeautifulSoup

from job_applier.models.job import Job, SalaryType, Workspace


class ApiPaths(Enum):
    DOMAIN = "https://www.jobbank.gc.ca"
    JOBSEARCH = "/jobsearch/jobsearch"
    JOBSEARCH_MORE = "/jobsearch/job_search_loader.xhtml"


def find_jobs(job_title: str, location: str, sort: str = "M") -> list[Job]:
    """
    This function will scrape the job bank website for jobs based on the job title and location provided.
    :param job_title: The job title to search for
    :param location: The location to search for
    :param sort: The sorting option for the search results (M = Most relevant, D = Most recent)
    :return: A list of Job objects
    """

    result = []

    with requests.Session() as session:

        # Load main result
        response = session.get(
            f"{ApiPaths.DOMAIN.value}{ApiPaths.JOBSEARCH.value}",
            params={"searchstring": job_title, "locationstring": location, "sort": sort},
        )

        soup = BeautifulSoup(response.content, "html.parser")
        result_element = soup.find(id="ajaxupdateform:result_block")
        if not result_element:
            return result

        articles = result_element.find_all("article")

        # Load more results
        while True:
            response = session.get(f"{ApiPaths.DOMAIN.value}{ApiPaths.JOBSEARCH_MORE.value}")
            soup = BeautifulSoup(response.content, "html.parser")
            extra_articles = soup.find_all("article")
            if not extra_articles:
                break
            for article in extra_articles:
                articles.append(article)
            sleep(random.uniform(0, 1))

        for job_element in articles:
            sleep(random.uniform(0, 1))

            job = Job()

            link_element = job_element.find("a", class_="resultJobItem")
            if link_element:
                href = link_element.get("href")
                url_parts = urllib.parse.urlparse(href)
                job.link = urllib.parse.urljoin(ApiPaths.DOMAIN.value, url_parts.path)

            job.source_id = job_element.get("id").replace("article-", "")
            job.source = "jobbank"

            job.posted_on_jb = job_element.find("span", class_="postedonJB") is not None

            title_element = job_element.find("span", class_="noctitle")
            if title_element:
                job.title = str(title_element.get_text(strip=True)).capitalize()

            date_element = job_element.find("li", class_="date")
            if date_element:
                date_text = date_element.get_text(strip=True)
                try:
                    job.date = datetime.strptime(date_text, "%B %d, %Y")
                except:
                    pass

            business_element = job_element.find("li", class_="business")
            if business_element:
                job.business = business_element.get_text(strip=True)

            location_element = job_element.find("li", class_="location")
            if location_element:
                for child in location_element.find_all("span"):
                    child.extract()
                job.location = location_element.get_text(strip=True)

            salary_element = job_element.find("li", class_="salary")
            if salary_element:
                for child in salary_element.find_all("span"):
                    child.extract()
                salary_text = salary_element.get_text(strip=True)
                salary_text = salary_text.lower()

                if "hourly" in salary_text:
                    job.salary_type = SalaryType.HOURLY
                elif "annually" in salary_text:
                    job.salary_type = SalaryType.ANNUALLY

                match = re.search(r"\d+\.\d+", salary_text)
                if match:
                    job.salary = float(match.group())

            workspace_element = job_element.find("span", class_="telework")
            if workspace_element:
                workspace_text = workspace_element.get_text(strip=True)
                if "on site" in workspace_text:
                    job.workspace = Workspace.ONSITE
                elif "hybrid" in workspace_text:
                    job.workspace = Workspace.HYBRID

            fill_job_details(job)

            result.append(job)

    return result


def fill_job_details(job: Job) -> Job:
    """
    This function will scrape the job details from the provided job object.
    :param job: The job object to scrape the details from
    :return: A string containing the job details
    """

    if not job.link:
        return job

    with requests.Session() as session:

        # link = f"{ApiPaths.DOMAIN.value}{job.link}"
        link = job.link

        # Get page with job description
        response = session.get(link)
        soup = BeautifulSoup(response.content, "html.parser")
        job_posting_element = soup.find("div", attrs={"typeof": "JobPosting"})
        if job_posting_element:
            job_description_element = job_posting_element.find(
                "span", class_="hidden", attrs={"property": "description"}
            )
            if job_description_element:
                job_description = job_description_element.get_text(strip=True)
                job_description = job_description.replace("\t", "")
                job_description = job_description.replace("\n", "")
                job_description = re.sub(r"\s{2,}", " ", job_description)
                job.description = job_description

        # Get information "How to apply"
        responce = session.post(
            link,
            data={
                "seekeractivity:jobid": job.source_id,
                "seekeractivity_SUBMIT": "1",
                "jakarta.faces.ViewState": "stateless",
                "jakarta.faces.behavior.event": "action",
                "action": "applynowbutton",
                "jakarta.faces.partial.event": "click",
                "jakarta.faces.source": "seekeractivity",
                "jakarta.faces.partial.ajax": "true",
                "jakarta.faces.partial.execute": "jobid",
                "jakarta.faces.partial.render": "applynow markappliedgroup",
                "seekeractivity": "seekeractivity",
            },
        )
        soup = BeautifulSoup(responce.content, "xml")
        cdata_element = soup.find("update", id="applynow")
        if cdata_element:
            soup = BeautifulSoup(cdata_element.get_text(), "html.parser")
            email_element = soup.find("a", href=re.compile(r"mailto:"))
            if email_element:
                job.email = email_element.text

        return job
