from datetime import datetime


class EreolenReservation:
    def __init__(
        self,
        reservation_data: dict[str, any],
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
        self.expected_availble_date = datetime.fromisoformat(
            reservation_data["expectedRedeemDateUtc"]
        ).date
        self.description = look_up_data["description"]
