import json
import logging
import re
from datetime import date


class ProfileInfo:
    def __init__(self, data):
        logging.getLogger(__package__).debug(json.dumps(data))
        self.birth_date = date.fromisoformat(data["birthday"])
        self.email_address: str = data["emailAddress"]
        self.name: str = data["name"]
        self.patron_id: str = data["patronId"]

    @property
    def camel_cased_name(self):
        return re.sub(
            r"[^a-z_]", " ", self.name.lower().replace(" ", "_"), flags=re.IGNORECASE
        )
