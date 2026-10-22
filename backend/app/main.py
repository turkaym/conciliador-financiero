from fastapi import FastAPI

from app.access.router import router as access_router
from app.errors import ApiError, api_error_handler
from app.import_catalogs.router import router as catalog_router
from app.imports.router import router as imports_router

app = FastAPI(title="Conciliador API", version="0.1.0")
app.add_exception_handler(ApiError, api_error_handler)
app.include_router(access_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(imports_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
