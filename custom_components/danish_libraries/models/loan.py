import json
import logging
from datetime import date


class Loan:
    def __init__(
        self,
        loan_data: dict[str, any],
        look_up_data: dict[str, any],
        image_url: str,
    ):
        try:
            self.author = ", ".join([c["display"] for c in look_up_data["creators"]])
            self.title = " ".join(look_up_data["titles"]["full"])
            self.image_url = image_url
            self.description = " ".join(look_up_data["abstract"])
            self.is_renewable = loan_data["isRenewable"]
            self.due_date = date.fromisoformat(loan_data["loanDetails"]["dueDate"])
        except Exception as e:
            logger = logging.getLogger(__package__)
            logger.warning(
                "Could not parse data for Library Loan, input: %s",
                json.dumps(loan_data),
            )
            logger.warning(e, exc_info=True)

    def to_json(self):
        return {
            "author": self.author,
            "title": self.title,
            "image_url": self.image_url,
            "description": self.description,
            "is_renewable": self.is_renewable,
            "due_date": self.due_date,
        }
