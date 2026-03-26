"""Job-related exceptions."""


class InvalidTransitionError(Exception):
    """Raised when attempting an invalid job state transition.

    Used to signal 409 Conflict responses when a state transition
    is not allowed by the state machine.
    """

    def __init__(self, current_state: str, action: str, detail: str | None = None):
        self.current_state = current_state
        self.action = action
        self.detail = detail or (
            f"Invalid transition: cannot perform '{action}' from state '{current_state}'"
        )
        super().__init__(self.detail)
