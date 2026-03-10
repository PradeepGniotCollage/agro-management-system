from app.main import app as fastapi_app

# Vercel Python runtime looks for an ASGI variable named `app`
app = fastapi_app
