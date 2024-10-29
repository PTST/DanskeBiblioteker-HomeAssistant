from datetime import datetime


class EreolenLoan:
    def __init__(
        self,
        loan_data: dict[str, any],
        look_up_data: dict[str, any],
        image_url: str,
    ):
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
        self.format = "Ebook" if not look_up_data["durationInSeconds"] else "Audiobook"
        self.loan_expire_date = datetime.fromisoformat(
            loan_data["loanExpireDateUtc"]
        ).date
        self.description = look_up_data["description"]
