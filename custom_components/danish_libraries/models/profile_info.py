from datetime import date


class ProfileInfo:
    def __init__(self, data):
        self.birth_date = date.fromisoformat(data["birthday"])
        self.email_address = data["emailAddress"]
        self.name = data["name"]
