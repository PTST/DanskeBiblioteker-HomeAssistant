import re
from datetime import date


class ProfileInfo:
    def __init__(self, data):
        self.birth_date = date.fromisoformat(data["birthday"])
        self.email_address: str = data["emailAddress"]
        self.name: str = data["name"]

    @property
    def camel_cased_name(self):
        return re.sub(
            r"[^a-z_]", " ", self.name.lower().replace(" ", "_"), flags=re.IGNORECASE
        )
