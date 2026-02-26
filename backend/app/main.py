import uvicorn
from fastapi import FastAPI

from .api.endpoints import router

app = FastAPI(title="AI Support Backend")

# И эта строка тоже!
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", reload=True)
