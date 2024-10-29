from datetime import date


class Loan:
    def __init__(
        self,
        loan_data: dict[str, any],
        look_up_data: dict[str, any],
        image_url: str,
    ):
        self.author = ", ".join([c["display"] for c in look_up_data["creators"]])
        self.title = " ".join(look_up_data["titles"]["full"])
        self.image_url = image_url
        self.description = " ".join(look_up_data["abstract"])
        self.is_renewable = loan_data["isRenewable"]
        self.loan_expire_date = date.fromisoformat(loan_data["loanDetails"]["dueDate"])