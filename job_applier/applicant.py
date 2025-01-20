from job_applier.settings import SETTINGS


class Applicant:
    def __init__(self,
                 first_name: str = None,
                 last_name: str = None,
                 email: str = None,
                 phone: str = None,
                 address: str = None,
                 resume: str = None,
                 cover_letter_file_path: str = None
                 ):
        self.first_name = first_name if first_name else SETTINGS['applicant']['first_name']
        self.last_name = last_name if last_name else SETTINGS['applicant']['last_name']
        self.email = email if email else SETTINGS['applicant']['contacts']['email']
        self.phone = phone if phone else SETTINGS['applicant']['contacts']['phone']
        self.address = address if address else SETTINGS['applicant']['contacts']['address']
        self.resume = resume if resume else SETTINGS['applicant']['resume']['file']
        self.cover_letter_file_path = cover_letter_file_path if cover_letter_file_path else \
            SETTINGS['applicant']['cover_letter']['file']

    def __str__(self):
        return f"Applicant {self.first_name} {self.last_name} (email: {self.email}, phone: {self.phone}, address: {self.address})"
