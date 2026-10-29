from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.database import Base, engine
from app.models import Product
from app.routers.product import router as product_router


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Electronics Store Inventory Management System",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(product_router)


@app.get("/")
def root():
    return {
        "message": "Electronics Store Inventory Management System API"
    }