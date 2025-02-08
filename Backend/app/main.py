from fastapi import FastAPI
from routes.user_routes import router as user_router
from routes.product_routes import router as product_router
from routes.invoice_routes import router as invoice_router
from routes.predictions_routes import router as prediction_router
from db.database import database

app = FastAPI()

app.include_router(user_router, prefix="/api", tags=["Users"])
app.include_router(product_router, prefix="/api", tags=["Products"])
app.include_router(invoice_router, prefix="/api", tags=["Invoices"])
app.include_router(prediction_router, prefix="/api", tags=["Predictions"])

# Health Check Route for MongoDB Connection
@app.get("/")
async def root():
    try:
        await database.command("ping")
        return {"message": "MongoDB Atlas is connected successfully! 🎉"}
    except Exception as e:
        return {"error": "Failed to connect to MongoDB Atlas", "details": str(e)}