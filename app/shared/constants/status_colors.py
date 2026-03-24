"""Status color semantic constants for UniFlow.

These color values define the semantic meaning of different status states.
Must be kept in sync with TypeScript StatusColors in uniflow-edge and uniflow-cloud-portal.
"""

STATUS_COLORS = {
    "BLUE": "#2563EB",  # active/in-progress
    "GREEN": "#16A34A",  # complete/success
    "AMBER": "#D97706",  # waiting/dependency
    "PURPLE": "#9333EA",  # user-paused
    "RED": "#DC2626",  # failed/error
    "GRAY": "#6B7280",  # offline/inactive
}
