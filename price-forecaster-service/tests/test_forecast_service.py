import pytest
from services.forecast_service import ForecastService

class TestForecastService:
    def test_valid_request(self):
        service = ForecastService()
        result = service.predict({"location":"Kolkata","state":"West Bengal","commodity":"Tomato"})
        assert "forecast" in result
        assert len(result["forecast"]) == 7
        assert result["trend"]["direction"] in ("rising","falling","stable")

    def test_missing_commodity(self):
        service = ForecastService()
        with pytest.raises(ValueError):
            service.predict({"location":"Pune","state":"Maharashtra"})

    def test_deterministic_output(self):
        service = ForecastService()
        r1 = service.predict({"location":"Kolkata","state":"West Bengal","commodity":"Tomato"})
        r2 = service.predict({"location":"Kolkata","state":"West Bengal","commodity":"Tomato"})
        for a,b in zip(r1["forecast"], r2["forecast"]):
            assert a["predicted_price_inr_per_kg"] == b["predicted_price_inr_per_kg"]
