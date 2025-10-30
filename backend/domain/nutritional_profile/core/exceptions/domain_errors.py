"""Domain exceptions for nutritional profile."""


class ProfileDomainError(Exception):
    """Base exception for nutritional profile domain errors."""
    
    pass


class InvalidUserDataError(ProfileDomainError):
    """Raised when user data validation fails."""
    
    pass


class ProfileNotFoundError(ProfileDomainError):
    """Raised when profile cannot be found."""
    
    def __init__(self, profile_id: str):
        super().__init__(f"Profile not found: {profile_id}")
        self.profile_id = profile_id


class ProfileAlreadyExistsError(ProfileDomainError):
    """Raised when trying to create profile for existing user."""
    
    def __init__(self, user_id: str):
        super().__init__(f"Profile already exists for user: {user_id}")
        self.user_id = user_id


class InvalidGoalError(ProfileDomainError):
    """Raised when goal is invalid."""
    
    pass


class NoProgressDataError(ProfileDomainError):
    """Raised when no progress data available for calculation."""
    
    def __init__(self, profile_id: str, start_date: str, end_date: str):
        super().__init__(
            f"No progress data for profile {profile_id} "
            f"between {start_date} and {end_date}"
        )
        self.profile_id = profile_id
        self.start_date = start_date
        self.end_date = end_date
