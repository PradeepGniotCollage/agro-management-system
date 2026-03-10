import re

def validate_password_strength(password: str) -> str:
    """
    Validates a password for:
    - minimum 8 characters
    - 1 uppercase letter
    - 1 number
    - 1 special character
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least 1 uppercase letter")
        
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least 1 number")
        
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValueError("Password must contain at least 1 special character")
        
    return password
