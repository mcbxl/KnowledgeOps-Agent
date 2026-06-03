from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import get_settings
from app.core.middleware import APIKeyMiddleware, RequestContextMiddleware


app = FastAPI(
    title="KnowledgeOps Agent API",
    version="0.1.0",
    description="Personal knowledge-base operations and citation-grounded RAG API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(APIKeyMiddleware)
app.add_middleware(RequestContextMiddleware)

app.include_router(router)
