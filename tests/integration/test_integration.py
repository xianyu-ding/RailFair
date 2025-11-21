"""
Day 12: Integration Tests
Test the integrated prediction engine and fare comparison with FastAPI
"""

import pytest
from fastapi.testclient import TestClient
from datetime import date, time, datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integrated_main import app, rate_limiter, DB_PATH

# Create test client
client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns API info"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "RailFair API" in data["name"]
    assert "1.1.0" in data["version"]
    assert "endpoints" in data


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "database" in data


def test_predict_with_real_engine():
    """Test prediction with real prediction engine"""
    tomorrow = date.today() + timedelta(days=1)
    
    request_data = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": tomorrow.isoformat(),
        "departure_time": "09:30",
        "include_fares": False
    }
    
    response = client.post("/api/predict", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "request_id" in data
    assert "prediction" in data
    
    # Check prediction fields
    prediction = data["prediction"]
    assert "delay_minutes" in prediction
    assert "on_time_probability" in prediction
    assert "confidence_level" in prediction
    assert "sample_size" in prediction
    assert "is_degraded" in prediction
    
    # Check explanation
    assert "explanation" in data
    assert len(data["explanation"]) > 0
    
    # Check metadata
    assert "metadata" in data
    assert data["metadata"]["prediction_engine"] == "statistical_v1"


def test_predict_with_fares():
    """Test prediction with fare comparison"""
    tomorrow = date.today() + timedelta(days=1)
    
    request_data = {
        "origin": "KGX",
        "destination": "EDB",
        "departure_date": tomorrow.isoformat(),
        "departure_time": "14:00",
        "include_fares": True
    }
    
    response = client.post("/api/predict", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "fares" in data
    
    if data["fares"]:
        fares = data["fares"]
        assert "advance_price" in fares
        assert "off_peak_price" in fares
        assert "anytime_price" in fares
        assert "cheapest_type" in fares
        assert "data_source" in fares
        
        # Check metadata shows fare engine
        assert data["metadata"]["fare_engine"] == "simulated_v1"


def test_predict_with_recommendations():
    """Test that predictions include recommendations"""
    tomorrow = date.today() + timedelta(days=1)
    
    request_data = {
        "origin": "PAD",
        "destination": "BRI",
        "departure_date": tomorrow.isoformat(),
        "departure_time": "17:30",  # Peak time
        "include_fares": True
    }
    
    response = client.post("/api/predict", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)
    
    if data["recommendations"]:
        rec = data["recommendations"][0]
        assert "type" in rec
        assert "title" in rec
        assert "description" in rec
        assert "score" in rec
        assert rec["type"] in ["money", "time", "balanced"]


def test_degraded_prediction():
    """Test degraded prediction for unknown route"""
    tomorrow = date.today() + timedelta(days=1)
    
    request_data = {
        "origin": "XXX",  # Unknown station (but valid format)
        "destination": "YYY",
        "departure_date": tomorrow.isoformat(),
        "departure_time": "10:00",
        "include_fares": False
    }
    
    # This should still work but with degraded prediction
    response = client.post("/api/predict", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    prediction = data["prediction"]
    
    # Should be degraded
    assert prediction["is_degraded"] == True
    assert prediction["degradation_reason"] is not None
    assert "network average" in prediction["degradation_reason"].lower()
    
    # Should still have valid probabilities
    assert 0 <= prediction["on_time_probability"] <= 1
    assert prediction["delay_minutes"] >= 0


def test_time_adjustment_factors():
    """Test that different times produce different predictions"""
    tomorrow = date.today() + timedelta(days=1)
    
    # Morning peak prediction
    morning_request = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": tomorrow.isoformat(),
        "departure_time": "08:00",  # Morning peak
        "include_fares": False
    }
    
    morning_response = client.post("/api/predict", json=morning_request)
    morning_data = morning_response.json()
    
    # Midday prediction
    midday_request = morning_request.copy()
    midday_request["departure_time"] = "12:00"  # Midday
    
    midday_response = client.post("/api/predict", json=midday_request)
    midday_data = midday_response.json()
    
    # Evening peak prediction
    evening_request = morning_request.copy()
    evening_request["departure_time"] = "17:30"  # Evening peak
    
    evening_response = client.post("/api/predict", json=evening_request)
    evening_data = evening_response.json()
    
    # Peak times should have worse predictions (if not degraded)
    if not morning_data["prediction"]["is_degraded"]:
        # Morning peak should be worse than midday
        assert morning_data["prediction"]["on_time_probability"] <= midday_data["prediction"]["on_time_probability"]
        
        # Evening peak should be worst
        assert evening_data["prediction"]["on_time_probability"] <= morning_data["prediction"]["on_time_probability"]


def test_feedback_submission():
    """Test feedback endpoint"""
    feedback_data = {
        "request_id": "req_test123",
        "actual_delay_minutes": 15,
        "was_cancelled": False,
        "rating": 4,
        "comment": "Pretty accurate prediction"
    }
    
    response = client.post("/api/feedback", json=feedback_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "feedback_id" in data
    assert "message" in data
    assert "Thank you" in data["message"]
    assert "received_at" in data


def test_stats_endpoint():
    """Test statistics endpoint"""
    # Make a few requests first
    tomorrow = date.today() + timedelta(days=1)
    for _ in range(3):
        client.post("/api/predict", json={
            "origin": "EUS",
            "destination": "MAN",
            "departure_date": tomorrow.isoformat(),
            "departure_time": "09:00"
        })
    
    response = client.get("/api/stats")
    assert response.status_code == 200
    
    data = response.json()
    assert "total_requests" in data
    assert "unique_clients" in data
    assert "total_feedback" in data
    assert "average_rating" in data
    assert data["total_requests"] >= 3


def test_rate_limiting():
    """Test that rate limiting works"""
    # Clear rate limiter for test
    rate_limiter.requests.clear()
    
    tomorrow = date.today() + timedelta(days=1)
    request_data = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": tomorrow.isoformat(),
        "departure_time": "09:00"
    }
    
    # Make many requests quickly (simulate from same client)
    responses = []
    for i in range(105):  # Over the 100/min limit
        response = client.post("/api/predict", json=request_data)
        responses.append(response.status_code)
    
    # Should have some 429 responses
    assert 429 in responses
    
    # Count successful vs rate limited
    successful = responses.count(200)
    rate_limited = responses.count(429)
    
    # Should have at most 100 successful
    assert successful <= 100
    assert rate_limited > 0


def test_validation_errors():
    """Test input validation"""
    tomorrow = date.today() + timedelta(days=1)
    
    # Invalid CRS code (lowercase)
    response = client.post("/api/predict", json={
        "origin": "eus",  # Should be uppercase
        "destination": "MAN",
        "departure_date": tomorrow.isoformat(),
        "departure_time": "09:00"
    })
    assert response.status_code == 422
    
    # Invalid CRS code (wrong length)
    response = client.post("/api/predict", json={
        "origin": "EU",  # Too short
        "destination": "MAN",
        "departure_date": tomorrow.isoformat(),
        "departure_time": "09:00"
    })
    assert response.status_code == 422
    
    # Past date
    yesterday = date.today() - timedelta(days=1)
    response = client.post("/api/predict", json={
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": yesterday.isoformat(),
        "departure_time": "09:00"
    })
    assert response.status_code == 422
    
    # Date too far in future
    far_future = date.today() + timedelta(days=100)
    response = client.post("/api/predict", json={
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": far_future.isoformat(),
        "departure_time": "09:00"
    })
    assert response.status_code == 422


def test_response_headers():
    """Test that response includes expected headers"""
    tomorrow = date.today() + timedelta(days=1)
    
    response = client.post("/api/predict", json={
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": tomorrow.isoformat(),
        "departure_time": "09:00"
    })
    
    # Check for custom headers
    assert "X-Process-Time" in response.headers
    assert "X-Request-ID" in response.headers
    
    # Process time should be in correct format
    process_time = response.headers["X-Request-ID"]
    assert process_time.startswith("req_")


# Run tests if executed directly
if __name__ == "__main__":
    print("Running Day 12 Integration Tests...")
    pytest.main([__file__, "-v", "--tb=short"])
