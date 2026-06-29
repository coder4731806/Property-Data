"""
Local prediction API for Alethia. Runs on your Mac; the Cloudflare Worker calls
it server-to-server when a customer fills in their property details.

Start it:
    pip install -r requirements.txt
    uvicorn predict_service:app --host 127.0.0.1 --port 8008
    # or:  python predict_service.py

Endpoints:
    GET  /health
    POST /estimate            -> recommended price + band + confidence + comparables + all models
    POST /predict?model=ebm   -> single-model point + band

Example:
    curl -s localhost:8008/estimate -H 'content-type: application/json' -d '{
        "suburb":"PADDINGTON","postcode":"4064","property_type":"house",
        "bedrooms":3,"bathrooms":2,"car_spaces":1,"land_size_m2":405}'
"""
from typing import Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel

from predict import PricePredictor, MODEL_FILES

app = FastAPI(title="Alethia Price Model", version="1.0")
_predictor: Optional[PricePredictor] = None


def predictor() -> PricePredictor:
    global _predictor
    if _predictor is None:
        _predictor = PricePredictor()
    return _predictor


class Property(BaseModel):
    suburb: str
    postcode: Optional[str] = None
    property_type: str = "house"
    bedrooms: Optional[float] = None
    bathrooms: Optional[float] = None
    car_spaces: Optional[float] = None
    land_size_m2: Optional[float] = None
    building_size_m2: Optional[float] = None
    address: Optional[str] = None


@app.on_event("startup")
def _warm():
    predictor()  # load artifacts once at boot


@app.get("/health")
def health():
    p = predictor()
    return {"status": "ok", "models": list(p.models), "trained_at": p.meta.get("trained_at")}


@app.post("/estimate")
def estimate(prop: Property):
    return predictor().estimate(prop.model_dump(exclude_none=True))


@app.post("/predict")
def predict(prop: Property, model: str = Query("lightgbm", enum=list(MODEL_FILES))):
    return predictor().predict_model(prop.model_dump(exclude_none=True), model)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8008)
