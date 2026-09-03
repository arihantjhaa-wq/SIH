"""FastAPI Application — Stage 9 API Layer.

This module creates the FastAPI application and configures the API
endpoints for the AgriDirect pricing engine.

The API exposes the existing Stage 6-8 pricing pipeline through
a clean HTTP interface without duplicating any business logic.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes.pricing import router as pricing_router
from app.pricing.integration import PricingIntegrationError
from app.logistics.validate import LogisticsValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("AgriDirect Pricing Engine API starting up")
    yield
    logger.info("AgriDirect Pricing Engine API shutting down")


# Create FastAPI application
app = FastAPI(
    title="AgriDirect Pricing Engine API",
    description="""
## AgriDirect Pricing Engine API

This API provides pricing estimates for agricultural commodities in India.

### Features
- **Price Discovery**: Fair price calculation using market data and forecasts
- **Logistics Costing**: Distance-based transport cost estimation
- **Farmer Protection**: Minimum price floor to protect farmers
- **Buyer Transparency**: Full price breakdown including platform fees

### Pipeline
The API executes the full pricing pipeline:
1. **Stage 6**: Price discovery, fair price, reliability scoring
2. **Stage 7**: Logistics calculation (distance, transport, handling)
3. **Stage 8**: End-to-end integration (buyer price, explanations)
    """,
    version="0.9.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ---------------------------------------------------------------------------
# Exception Handlers
# ---------------------------------------------------------------------------

@app.exception_handler(PricingIntegrationError)
async def pricing_integration_error_handler(request: Request, exc: PricingIntegrationError):
    """Handle pricing integration errors."""
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "field": exc.field,
            }
        },
    )


@app.exception_handler(LogisticsValidationError)
async def logistics_validation_error_handler(request: Request, exc: LogisticsValidationError):
    """Handle logistics validation errors."""
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "field": exc.field,
            }
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle value errors from pricing calculations."""
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc),
                "field": None,
            }
        },
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    tags=["Health"],
    summary="Health check endpoint",
    description="Returns the health status of the API. This endpoint does not require any external service connectivity.",
)
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Health status with 'status': 'ok'
    """
    return {"status": "ok"}


# Include pricing routes
app.include_router(
    pricing_router,
    prefix="/api/v1/pricing",
    tags=["Pricing"],
)


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------

@app.get(
    "/",
    tags=["Root"],
    summary="API root endpoint",
    description="Returns basic API information.",
)
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AgriDirect Pricing Engine API",
        "version": "0.9.0",
        "docs": "/docs",
        "health": "/health",
        "pricing": "/api/v1/pricing/estimate",
    }
