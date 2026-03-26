"""Tests for JobStateMachine - Pure unit tests, no DB."""

import pytest

from app.exceptions.job_exceptions import InvalidTransitionError
from app.services.state_machine import JobStateMachine
from app.shared.enums.job_status import JobStatus


class TestValidTransitions:
    """Test all 13 valid transitions from the transition map."""

    def test_pre_registering_to_waiting_for_agent(self):
        """PRE_REGISTERING + complete_registration -> WAITING_FOR_AGENT"""
        assert JobStateMachine.can_transition(
            JobStatus.PRE_REGISTERING, "complete_registration"
        )
        next_state = JobStateMachine.get_next_state(
            JobStatus.PRE_REGISTERING, "complete_registration"
        )
        assert next_state == JobStatus.WAITING_FOR_AGENT

    def test_pre_registering_to_failed(self):
        """PRE_REGISTERING + fail -> FAILED"""
        assert JobStateMachine.can_transition(JobStatus.PRE_REGISTERING, "fail")
        next_state = JobStateMachine.get_next_state(JobStatus.PRE_REGISTERING, "fail")
        assert next_state == JobStatus.FAILED

    def test_waiting_for_agent_to_in_progress(self):
        """WAITING_FOR_AGENT + consent -> IN_PROGRESS"""
        assert JobStateMachine.can_transition(JobStatus.WAITING_FOR_AGENT, "consent")
        next_state = JobStateMachine.get_next_state(
            JobStatus.WAITING_FOR_AGENT, "consent"
        )
        assert next_state == JobStatus.IN_PROGRESS

    def test_waiting_for_agent_to_denied(self):
        """WAITING_FOR_AGENT + deny -> DENIED"""
        assert JobStateMachine.can_transition(JobStatus.WAITING_FOR_AGENT, "deny")
        next_state = JobStateMachine.get_next_state(JobStatus.WAITING_FOR_AGENT, "deny")
        assert next_state == JobStatus.DENIED

    def test_waiting_for_agent_to_cancelled(self):
        """WAITING_FOR_AGENT + cancel -> CANCELLED"""
        assert JobStateMachine.can_transition(JobStatus.WAITING_FOR_AGENT, "cancel")
        next_state = JobStateMachine.get_next_state(
            JobStatus.WAITING_FOR_AGENT, "cancel"
        )
        assert next_state == JobStatus.CANCELLED

    def test_waiting_for_agent_to_timeout(self):
        """WAITING_FOR_AGENT + timeout -> TIMEOUT"""
        assert JobStateMachine.can_transition(JobStatus.WAITING_FOR_AGENT, "timeout")
        next_state = JobStateMachine.get_next_state(
            JobStatus.WAITING_FOR_AGENT, "timeout"
        )
        assert next_state == JobStatus.TIMEOUT

    def test_in_progress_to_paused_user(self):
        """IN_PROGRESS + pause -> PAUSED_USER"""
        assert JobStateMachine.can_transition(JobStatus.IN_PROGRESS, "pause")
        next_state = JobStateMachine.get_next_state(JobStatus.IN_PROGRESS, "pause")
        assert next_state == JobStatus.PAUSED_USER

    def test_in_progress_to_cancelled(self):
        """IN_PROGRESS + cancel -> CANCELLED"""
        assert JobStateMachine.can_transition(JobStatus.IN_PROGRESS, "cancel")
        next_state = JobStateMachine.get_next_state(JobStatus.IN_PROGRESS, "cancel")
        assert next_state == JobStatus.CANCELLED

    def test_in_progress_to_completed(self):
        """IN_PROGRESS + complete -> COMPLETED"""
        assert JobStateMachine.can_transition(JobStatus.IN_PROGRESS, "complete")
        next_state = JobStateMachine.get_next_state(JobStatus.IN_PROGRESS, "complete")
        assert next_state == JobStatus.COMPLETED

    def test_in_progress_to_partially_failed(self):
        """IN_PROGRESS + partial_fail -> PARTIALLY_FAILED"""
        assert JobStateMachine.can_transition(JobStatus.IN_PROGRESS, "partial_fail")
        next_state = JobStateMachine.get_next_state(
            JobStatus.IN_PROGRESS, "partial_fail"
        )
        assert next_state == JobStatus.PARTIALLY_FAILED

    def test_in_progress_to_failed(self):
        """IN_PROGRESS + fail -> FAILED"""
        assert JobStateMachine.can_transition(JobStatus.IN_PROGRESS, "fail")
        next_state = JobStateMachine.get_next_state(JobStatus.IN_PROGRESS, "fail")
        assert next_state == JobStatus.FAILED

    def test_paused_user_to_in_progress(self):
        """PAUSED_USER + resume -> IN_PROGRESS"""
        assert JobStateMachine.can_transition(JobStatus.PAUSED_USER, "resume")
        next_state = JobStateMachine.get_next_state(JobStatus.PAUSED_USER, "resume")
        assert next_state == JobStatus.IN_PROGRESS

    def test_paused_user_to_cancelled(self):
        """PAUSED_USER + cancel -> CANCELLED"""
        assert JobStateMachine.can_transition(JobStatus.PAUSED_USER, "cancel")
        next_state = JobStateMachine.get_next_state(JobStatus.PAUSED_USER, "cancel")
        assert next_state == JobStatus.CANCELLED


class TestInvalidTransitions:
    """Test invalid transitions raise InvalidTransitionError."""

    def test_completed_to_cancel_invalid(self):
        """COMPLETED + cancel -> InvalidTransitionError (terminal state)"""
        assert not JobStateMachine.can_transition(JobStatus.COMPLETED, "cancel")
        with pytest.raises(InvalidTransitionError) as exc_info:
            JobStateMachine.get_next_state(JobStatus.COMPLETED, "cancel")
        assert exc_info.value.current_state == JobStatus.COMPLETED
        assert exc_info.value.action == "cancel"

    def test_pre_registering_to_consent_invalid(self):
        """PRE_REGISTERING + consent -> InvalidTransitionError (wrong action)"""
        assert not JobStateMachine.can_transition(JobStatus.PRE_REGISTERING, "consent")
        with pytest.raises(InvalidTransitionError) as exc_info:
            JobStateMachine.get_next_state(JobStatus.PRE_REGISTERING, "consent")
        assert exc_info.value.current_state == JobStatus.PRE_REGISTERING
        assert exc_info.value.action == "consent"

    def test_in_progress_to_deny_invalid(self):
        """IN_PROGRESS + deny -> InvalidTransitionError (deny only valid for WAITING_FOR_AGENT)"""
        assert not JobStateMachine.can_transition(JobStatus.IN_PROGRESS, "deny")
        with pytest.raises(InvalidTransitionError):
            JobStateMachine.get_next_state(JobStatus.IN_PROGRESS, "deny")


class TestTerminalStateImmutability:
    """Test that all 6 terminal states reject all actions."""

    TERMINAL_STATES = [
        JobStatus.DENIED,
        JobStatus.TIMEOUT,
        JobStatus.COMPLETED,
        JobStatus.PARTIALLY_FAILED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    ]

    ACTIONS = [
        "complete_registration",
        "fail",
        "consent",
        "deny",
        "cancel",
        "timeout",
        "pause",
        "complete",
        "partial_fail",
        "resume",
    ]

    @pytest.mark.parametrize("terminal_state", TERMINAL_STATES)
    @pytest.mark.parametrize("action", ACTIONS)
    def test_terminal_state_rejects_all_actions(self, terminal_state, action):
        """All terminal states reject all actions."""
        assert not JobStateMachine.can_transition(terminal_state, action)
        with pytest.raises(InvalidTransitionError):
            JobStateMachine.get_next_state(terminal_state, action)


class TestGetValidActions:
    """Test get_valid_actions returns correct actions for each state."""

    def test_pre_registering_valid_actions(self):
        """PRE_REGISTERING has complete_registration and fail."""
        actions = JobStateMachine.get_valid_actions(JobStatus.PRE_REGISTERING)
        assert set(actions) == {"complete_registration", "fail"}

    def test_waiting_for_agent_valid_actions(self):
        """WAITING_FOR_AGENT has consent, deny, cancel, timeout."""
        actions = JobStateMachine.get_valid_actions(JobStatus.WAITING_FOR_AGENT)
        assert set(actions) == {"consent", "deny", "cancel", "timeout"}

    def test_in_progress_valid_actions(self):
        """IN_PROGRESS has pause, cancel, complete, partial_fail, fail."""
        actions = JobStateMachine.get_valid_actions(JobStatus.IN_PROGRESS)
        assert set(actions) == {"pause", "cancel", "complete", "partial_fail", "fail"}

    def test_paused_user_valid_actions(self):
        """PAUSED_USER has resume and cancel."""
        actions = JobStateMachine.get_valid_actions(JobStatus.PAUSED_USER)
        assert set(actions) == {"resume", "cancel"}

    def test_terminal_state_no_valid_actions(self):
        """Terminal states have no valid actions."""
        actions = JobStateMachine.get_valid_actions(JobStatus.COMPLETED)
        assert actions == []


class TestIsTerminal:
    """Test is_terminal returns True for terminal states, False for non-terminal."""

    def test_terminal_states_return_true(self):
        """All 5 terminal states return True."""
        terminal_states = [
            JobStatus.DENIED,
            JobStatus.COMPLETED,
            JobStatus.PARTIALLY_FAILED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        ]
        for state in terminal_states:
            assert JobStateMachine.is_terminal(state)

    def test_non_terminal_states_return_false(self):
        """Non-terminal states return False (TIMEOUT is semi-terminal, allows resend)."""
        non_terminal_states = [
            JobStatus.PRE_REGISTERING,
            JobStatus.WAITING_FOR_AGENT,
            JobStatus.IN_PROGRESS,
            JobStatus.PAUSED_USER,
            JobStatus.TIMEOUT,  # Semi-terminal: allows resend transition
        ]
        for state in non_terminal_states:
            assert not JobStateMachine.is_terminal(state)
