from datetime import date


class Reservation:
    def __init__(
        self,
        reservation_data: dict[str, any],
        look_up_data: dict[str, any],
        image_url: str,
    ):
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
