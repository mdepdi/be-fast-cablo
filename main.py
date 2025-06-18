"""
FastAPI Application Entry Point
This file allows running the app with: uvicorn main:app --reload
"""

from app.main import app

if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )