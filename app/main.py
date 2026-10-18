from fastapi import Depends, FastAPI

from app.api import auth, folders, items
from app.api.deps import require_api_key

app = FastAPI(title="Note API", version="0.1.0")


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}


protected = [Depends(require_api_key)]
app.include_router(auth.router, dependencies=protected)
app.include_router(folders.router, dependencies=protected)
app.include_router(items.router, dependencies=protected)
