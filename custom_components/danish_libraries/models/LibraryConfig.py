from typing import Self

class LibraryConfig(object):
    def __init__(self, jsonData: dict[str, any]):
        self.name = jsonData["name"]
        self.branch_id = jsonData["branchId"]
        self.url = jsonData["url"]

    @staticmethod
    def from_json(data: dict[str, dict[str, any]]) -> dict[str, Self]:
        return {k: LibraryConfig(v) for k, v in data.items()}