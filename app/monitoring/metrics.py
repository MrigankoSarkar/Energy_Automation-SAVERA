from __future__ import annotations


class Metrics:

    def __init__(self):
        self.counters = {}

    def increment(
        self,
        name: str,
        value: int = 1,
    ):

        self.counters[name] = (
            self.counters.get(
                name,
                0,
            )
            + value
        )

    def get(
        self,
        name: str,
    ):

        return self.counters.get(
            name,
            0,
        )

    def snapshot(self):

        return dict(
            self.counters
        )