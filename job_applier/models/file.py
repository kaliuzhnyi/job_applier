from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from job_applier import Applicant, Job


@dataclass
class FileModel(ABC):
    applicant: Applicant
    job: Job
    text: Optional[str] = None
    file_path: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.text:
            self.text = self.create_text()
        if not self.file_path:
            self.file_path = self.create_file()

    @abstractmethod
    def create_text(self) -> Optional[str]:
        pass

    @abstractmethod
    def create_file(self) -> Optional[str]:
        pass

