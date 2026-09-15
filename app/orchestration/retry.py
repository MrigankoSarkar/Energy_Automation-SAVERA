from __future__ import annotations

import time
from typing import Callable, Any


class RetryService:

    def __init__(
        self,
        attempts: int = 3,
        delay_seconds: int = 5,
    ):
        self.attempts = max(
            1,
            int(attempts),
        )

        self.delay_seconds = max(
            0,
            int(delay_seconds),
        )

    def execute(
        self,
        function: Callable,
        *args,
        **kwargs,
    ) -> Any:

        last_error = None

        for attempt in range(
            self.attempts
        ):
            try:
                return function(
                    *args,
                    **kwargs
                )

            except Exception as exc:
                last_error = exc

                if (
                    attempt
                    < self.attempts - 1
                ):
                    time.sleep(
                        self.delay_seconds
                    )

        raise last_error