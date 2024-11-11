import json
import logging
from datetime import datetime


class EreolenReservation:
    def __init__(
        self,
        reservation_data: dict[str, any],
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
            self.expected_availble_date = (
                datetime.fromisoformat(reservation_data["expectedRedeemDateUtc"]).date()
                if reservation_data["expectedRedeemDateUtc"] is not None
                else None
            )
            self.description = look_up_data["description"]
            self.pickup_deadline = (
                datetime.fromisoformat(reservation_data["pickupDeadline"]).date
                if reservation_data["expireDateUtc"] is not None
                else None
            )
        except Exception as e:
            logger = logging.getLogger(__package__)
            logger.warning(
                "Could not parse data for Ereolen Reservation, input: %s",
                json.dumps(reservation_data),
            )
            logger.warning(e, exc_info=True)

    def to_json(self):
        return {
            "title": self.title,
            "author": self.author,
            "image_url": self.image_url,
            "description": self.description,
            "narrator": self.narrator,
            "format": self.format,
            "expected_availble_date": self.expected_availble_date,
        }
