import csv
import os
from typing import Any, List, Optional


def log(filename: Optional[str], data: List[Any]) -> None:
    if not filename or not data:
        return

    keys = extract_keys(data[0])

    with open(filename, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        if os.stat(filename).st_size == 0:
            writer.writeheader()
        for item in data:
            writer.writerow(item if hasattr(item, 'keys') else vars(item))


def extract_keys(item: Any) -> List[str]:
    return item.keys() if hasattr(item, 'keys') else vars(item)
