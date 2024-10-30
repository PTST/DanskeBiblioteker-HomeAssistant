import json
import logging
from datetime import date


class Reservation:
    def __init__(
        self,
        reservation_data: dict[str, any],
        look_up_data: dict[str, any],
        image_url: str,
    ):
        try:
            self.number_in_queue = reservation_data["numberInQueue"]
            self.pickup_deadline = (
                date.fromisoformat(reservation_data["pickupDeadline"])
                if reservation_data["pickupDeadline"] is not None
                else None
            )
            self.author = ", ".join([c["display"] for c in look_up_data["creators"]])
            self.title = " ".join(look_up_data["titles"]["full"])
            self.image_url = image_url
            self.description = " ".join(look_up_data["abstract"])
        except Exception as e:
            logger = logging.getLogger(__package__)
            logger.warning(
                "Could not parse data for Library Reservation, input: %s",
                json.dumps(reservation_data),
            )
            logger.warning(e, exc_info=True)

    @property
    def days_left_for_pickup(self):
        if self.pickup_deadline is None:
            return 10000 * self.number_in_queue
        return (self.pickup_deadline - date.today()).days

    def to_json(self):
        return {
            "title": self.title,
            "author": self.author,
            "image_url": self.image_url,
            "description": self.description,
            "pickup_deadline": self.pickup_deadline,
            "number_in_queue": self.number_in_queue,
            "days_left_for_pickup": self.days_left_for_pickup,
        }
