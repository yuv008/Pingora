"""
Security module for authentication and authorization
Handles JWT tokens, password hashing, and session management
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityManager:
    """Centralized security management"""

    def __init__(self):
        self.algorithm = settings.JWT_ALGORITHM
        self.secret_key = settings.JWT_SECRET_KEY
        self.access_token_expire = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        self.refresh_token_expire = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    # Password Management
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a hashed password

        Args:
            plain_password: The plain text password to verify
            hashed_password: The hashed password to compare against

        Returns:
            True if passwords match, False otherwise
        """
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

    def get_password_hash(self, password: str) -> str:
        """
        Hash a password using bcrypt

        Args:
            password: The plain text password to hash

        Returns:
            The hashed password
        """
        return pwd_context.hash(password)

    def validate_password_strength(self, password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password strength

        Args:
            password: The password to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"

        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"

        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"

        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"

        # Check for special characters
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"

        return True, None

    # Token Management
    def create_access_token(
        self,
        user_id: str,
        session_id: str,
        workspace_id: Optional[str] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a JWT access token

        Args:
            user_id: The user's ID
            session_id: The session ID
            workspace_id: Optional workspace ID
            additional_claims: Any additional claims to include

        Returns:
            Encoded JWT token
        """
        expire = datetime.utcnow() + self.access_token_expire

        to_encode = {
            "sub": user_id,
            "session_id": session_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }

        if workspace_id:
            to_encode["workspace_id"] = workspace_id

        if additional_claims:
            to_encode.update(additional_claims)

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(
        self,
        user_id: str,
        session_id: str
    ) -> str:
        """
        Create a JWT refresh token

        Args:
            user_id: The user's ID
            session_id: The session ID

        Returns:
            Encoded JWT refresh token
        """
        expire = datetime.utcnow() + self.refresh_token_expire

        to_encode = {
            "sub": user_id,
            "session_id": session_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify and decode a JWT token

        Args:
            token: The JWT token to verify
            token_type: Expected token type (access or refresh)

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            # Verify token type
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected {token_type}"
                )

            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )

            return payload

        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not validate credentials: {str(e)}"
            )

    # Session Token Generation
    def generate_session_token(self) -> str:
        """Generate a secure random session token"""
        return secrets.token_urlsafe(32)

    def generate_verification_token(self) -> str:
        """Generate a secure random verification token"""
        return secrets.token_urlsafe(32)

    # Email Verification
    def create_email_verification_token(self, email: str) -> str:
        """
        Create a token for email verification

        Args:
            email: The email address to verify

        Returns:
            Encoded JWT token
        """
        expire = datetime.utcnow() + timedelta(hours=24)

        to_encode = {
            "sub": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "email_verification"
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_email_verification_token(self, token: str) -> str:
        """
        Verify an email verification token

        Args:
            token: The verification token

        Returns:
            The email address from the token

        Raises:
            HTTPException: If token is invalid
        """
        payload = self.verify_token(token, token_type="email_verification")
        email = payload.get("sub")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )

        return email

    # Password Reset
    def create_password_reset_token(self, user_id: str) -> str:
        """
        Create a token for password reset

        Args:
            user_id: The user's ID

        Returns:
            Encoded JWT token
        """
        expire = datetime.utcnow() + timedelta(hours=1)

        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "password_reset"
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_password_reset_token(self, token: str) -> str:
        """
        Verify a password reset token

        Args:
            token: The reset token

        Returns:
            The user ID from the token

        Raises:
            HTTPException: If token is invalid
        """
        payload = self.verify_token(token, token_type="password_reset")
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )

        return user_id


# Global security manager instance
security = SecurityManager()


# Convenience functions for backward compatibility
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password - convenience wrapper"""
    return security.verify_password(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password - convenience wrapper"""
    return security.get_password_hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create access token - convenience wrapper"""
    user_id = data.get("sub")
    session_id = data.get("session_id")
    workspace_id = data.get("workspace_id")

    return security.create_access_token(
        user_id=user_id,
        session_id=session_id,
        workspace_id=workspace_id
    )
