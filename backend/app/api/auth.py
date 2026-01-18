from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
import httpx
from app.core.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.get("/github")
async def github_login():
    """Redirect to GitHub OAuth authorization page."""
    if not settings.github_client_id:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")

    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&scope=repo,read:user"
        f"&redirect_uri={settings.backend_url}/api/auth/github/callback"
    )
    return RedirectResponse(url=github_auth_url)


@router.get("/github/callback")
async def github_callback(code: str):
    """Handle GitHub OAuth callback."""
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get access token")

        token_data = token_response.json()

        if "error" in token_data:
            raise HTTPException(status_code=400, detail=token_data.get("error_description", "OAuth error"))

        access_token = token_data.get("access_token")

    # Redirect to frontend with token
    frontend_callback = f"{settings.frontend_url}/auth/callback?token={access_token}"
    return RedirectResponse(url=frontend_callback)


@router.get("/github/user")
async def get_github_user(token: str):
    """Get GitHub user info with access token."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )

        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_data = response.json()
        return {
            "login": user_data["login"],
            "avatar_url": user_data["avatar_url"],
            "name": user_data.get("name"),
        }
