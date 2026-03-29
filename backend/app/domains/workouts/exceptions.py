class WorkoutException(Exception):
    """Base exception for workout-related errors."""
    pass

class ExerciseNotFoundError(WorkoutException):
    """Raised when an exercise is not found in the database."""
    pass

class IncompleteRulesError(WorkoutException):
    """Raised when exercise rules are incomplete."""
    pass

class PostureAnalysisError(WorkoutException):
    """Raised when there's an error in posture analysis (e.g., no person detected)."""
    pass
