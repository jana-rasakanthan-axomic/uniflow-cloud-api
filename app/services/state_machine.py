"""Job State Machine - Pure logic, no DB dependencies.

Implements the job state transition map for UniFlow upload jobs.
Validates state transitions and tracks terminal states.
"""

from app.exceptions.job_exceptions import InvalidTransitionError
from app.shared.enums.job_status import JobStatus


class JobStateMachine:
    """Pure state machine for job state transitions.

    Defines valid transitions between job states and provides validation
    logic without any database dependencies.
    """

    # Terminal states - once reached, no further transitions allowed
    # Note: TIMEOUT is semi-terminal (allows resend transition)
    TERMINAL_STATES: set[str] = {
        JobStatus.DENIED,
        JobStatus.COMPLETED,
        JobStatus.PARTIALLY_FAILED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    }

    # Transition map: (current_state, action) -> next_state
    TRANSITION_MAP: dict[str, dict[str, str]] = {
        JobStatus.PRE_REGISTERING: {
            "complete_registration": JobStatus.WAITING_FOR_AGENT,
            "fail": JobStatus.FAILED,
        },
        JobStatus.WAITING_FOR_AGENT: {
            "consent": JobStatus.IN_PROGRESS,
            "deny": JobStatus.DENIED,
            "cancel": JobStatus.CANCELLED,
            "timeout": JobStatus.TIMEOUT,
        },
        JobStatus.IN_PROGRESS: {
            "pause": JobStatus.PAUSED_USER,
            "cancel": JobStatus.CANCELLED,
            "complete": JobStatus.COMPLETED,
            "partial_fail": JobStatus.PARTIALLY_FAILED,
            "fail": JobStatus.FAILED,
        },
        JobStatus.PAUSED_USER: {
            "resume": JobStatus.IN_PROGRESS,
            "cancel": JobStatus.CANCELLED,
        },
        JobStatus.TIMEOUT: {
            "resend": JobStatus.WAITING_FOR_AGENT,
        },
    }

    @classmethod
    def can_transition(cls, current_state: str, action: str) -> bool:
        """Check if a transition is allowed.

        Args:
            current_state: Current job status
            action: Action to perform

        Returns:
            True if transition is valid, False otherwise
        """
        # Terminal states reject all transitions
        if current_state in cls.TERMINAL_STATES:
            return False

        # Check if action is valid for current state
        return action in cls.TRANSITION_MAP.get(current_state, {})

    @classmethod
    def get_next_state(cls, current_state: str, action: str) -> str:
        """Get the next state for a given current state and action.

        Args:
            current_state: Current job status
            action: Action to perform

        Returns:
            Next job status

        Raises:
            InvalidTransitionError: If transition is not allowed
        """
        if not cls.can_transition(current_state, action):
            raise InvalidTransitionError(current_state, action)

        return cls.TRANSITION_MAP[current_state][action]

    @classmethod
    def is_terminal(cls, state: str) -> bool:
        """Check if a state is terminal.

        Args:
            state: Job status to check

        Returns:
            True if state is terminal, False otherwise
        """
        return state in cls.TERMINAL_STATES

    @classmethod
    def get_valid_actions(cls, current_state: str) -> list[str]:
        """Get all valid actions for a given state.

        Args:
            current_state: Current job status

        Returns:
            List of valid action names (empty for terminal states)
        """
        if current_state in cls.TERMINAL_STATES:
            return []

        return list(cls.TRANSITION_MAP.get(current_state, {}).keys())
