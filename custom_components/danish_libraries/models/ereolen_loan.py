import json
import logging
from datetime import datetime


class EreolenLoan:
    def __init__(
        self,
        loan_data: dict[str, any],
        look_up_data: dict[str, any],
        image_url: str,
    ):
        try:
            self.title = look_up_data["title"]
            self.image_url = image_url
            self.author = ", ".join(
                [
                    f'{x["firstName"]} {x["lastName"]}'
                    for x in look_up_data["contributors"]
                    if x["type"] == "A01"
                ]
            )
            self.narrator = ", ".join(
                [
                    f'{x["firstName"]} {x["lastName"]}'
                    for x in look_up_data["contributors"]
                    if x["type"] == "E07"
                ]
            )
            self.format = (
                "Ebook" if not look_up_data["durationInSeconds"] else "Audiobook"
            )
            self.due_date = datetime.fromisoformat(
                loan_data["loanExpireDateUtc"]
            ).date()
            self.description = look_up_data["description"]
        except Exception as e:
            logger = logging.getLogger(__package__)
            logger.warning(
                "Could not parse data for Ereolen Loan, input: %s",
                json.dumps(loan_data),
            )
            logger.warning(e, exc_info=True)

    def to_json(self):
        return {
            "author": self.author,
            "title": self.title,
            "narrator": self.narrator,
            "image_url": self.image_url,
            "description": self.description,
            "due_date": self.due_date,
            "format": self.format,
        }
