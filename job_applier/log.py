import csv
import logging
import os
from typing import Any, List, Optional

logger = logging.getLogger("jobapplier")


def init_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def log(filename: Optional[str], data: List[Any]) -> None:
    if not filename or not data:
        return

    keys = extract_keys(data[0])

    with open(filename, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        if os.stat(filename).st_size == 0:
            writer.writeheader()
        for item in data:
            row = {key: value for key, value in vars(item).items() if key in keys} if not hasattr(item, "keys") else item
            writer.writerow(row)
            # writer.writerow(item if hasattr(item, 'keys') else vars(item))


def extract_keys(item: Any) -> List[str]:
    if hasattr(item, "keys"):
        return list(item.keys())
    elif hasattr(type(item), "__annotations__"):
        return list(type(item).__annotations__.keys())
    else:
        return []