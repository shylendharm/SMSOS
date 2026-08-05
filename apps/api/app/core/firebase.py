"""
Firebase Admin SDK integration for verifying Google Sign-In tokens.
"""
import os
import structlog
from typing import Optional, Dict, Any

logger = structlog.get_logger()

_firebase_app = None


def _get_firebase_app():
    """Lazy-initialize the Firebase Admin SDK."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials

        # Look for the service account JSON relative to the api directory
        api_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sa_path = os.path.join(api_dir, "firebase-service-account.json")

        if not os.path.exists(sa_path):
            logger.error("Firebase service account file not found", path=sa_path)
            return None

        cred = credentials.Certificate(sa_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully")
        return _firebase_app
    except Exception as e:
        logger.error("Failed to initialize Firebase Admin SDK", error=str(e))
        return None


async def verify_firebase_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Firebase ID token and return the decoded claims.

    Returns a dict with keys like:
        - uid: Firebase user ID
        - email: User's email address
        - name: User's display name
        - picture: User's profile photo URL
        - email_verified: Whether email is verified

    Returns None if verification fails.
    """
    app = _get_firebase_app()
    if app is None:
        logger.error("Firebase app not initialized, cannot verify token")
        return None

    try:
        from firebase_admin import auth

        decoded_token = auth.verify_id_token(id_token)
        logger.info(
            "Firebase token verified successfully",
            uid=decoded_token.get("uid"),
            email=decoded_token.get("email"),
        )
        return {
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name", ""),
            "picture": decoded_token.get("picture", ""),
            "email_verified": decoded_token.get("email_verified", False),
        }
    except Exception as e:
        logger.error("Firebase token verification failed", error=str(e))
        return None
