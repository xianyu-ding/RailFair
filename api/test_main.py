"""
RailFair API Integration Tests
================================

Comprehensive test suite for the FastAPI backend.

Test Coverage:
- Health check endpoint
- Prediction endpoint
- Feedback endpoint
- Rate limiting
- Error handling
- Request validation
- Response schemas
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import time
import json

from .main import app, rate_limiter, app_state


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter between tests"""
    rate_limiter.requests.clear()
    yield
    rate_limiter.requests.clear()


@pytest.fixture(autouse=True)
def reset_app_state():
    """Reset app state between tests"""
    app_state.request_count = 0
    app_state.error_count = 0
    yield


# ============================================================================
# Test: Root Endpoint
# ============================================================================

def test_root_endpoint(client):
    """Test root endpoint returns welcome message"""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data
    assert "health" in data
    assert "version" in data


# ============================================================================
# Test: Health Check
# ============================================================================

def test_health_check_success(client):
    """Test health check returns correct status"""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "status" in data
    assert "timestamp" in data
    assert "version" in data
    assert "uptime_seconds" in data
    assert "services" in data
    
    # Check status is valid
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    # Check version
    assert data["version"] == "1.0.0"
    
    # Check uptime is reasonable
    assert data["uptime_seconds"] >= 0
    
    # Check services
    assert isinstance(data["services"], dict)


def test_health_check_timing(client):
    """Test health check is fast"""
    start = time.time()
    response = client.get("/health")
    duration = time.time() - start
    
    assert response.status_code == 200
    assert duration < 0.1  # Should respond in <100ms


# ============================================================================
# Test: Prediction Endpoint - Success Cases
# ============================================================================

def test_predict_valid_request(client):
    """Test prediction with valid request"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    payload = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": tomorrow,
        "departure_time": "09:30",
        "include_fares": True
    }
    
    response = client.post("/api/predict", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "request_id" in data
    assert "origin" in data
    assert "destination" in data
    assert "departure_datetime" in data
    assert "prediction" in data
    assert "metadata" in data
    
    # Check prediction structure
    prediction = data["prediction"]
    assert "predicted_delay_minutes" in prediction
    assert "confidence" in prediction
    assert "delay_category" in prediction
    assert "on_time_probability" in prediction
    assert "historical_data_points" in prediction
    
    # Check confidence is in valid range
    assert 0.0 <= prediction["confidence"] <= 1.0
    assert 0.0 <= prediction["on_time_probability"] <= 1.0


def test_predict_with_fares(client):
    """Test prediction includes fare comparison when requested"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    payload = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": tomorrow,
        "departure_time": "14:30",
        "include_fares": True
    }
    
    response = client.post("/api/predict", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check fares are included
    assert "fares" in data
    assert data["fares"] is not None
    
    fares = data["fares"]
    assert "advance" in fares or "off_peak" in fares or "anytime" in fares
    assert "cheapest_type" in fares
    assert "cheapest_price" in fares
    assert "data_source" in fares


def test_predict_without_fares(client):
    """Test prediction without fare comparison"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    payload = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": tomorrow,
        "departure_time": "14:30",
        "include_fares": False
    }
    
    response = client.post("/api/predict", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Fares should be None or not included
    assert data.get("fares") is None


def test_predict_recommendations(client):
    """Test prediction includes recommendations"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    payload = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": tomorrow,
        "departure_time": "09:30",
        "include_fares": True
    }
    
    response = client.post("/api/predict", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check recommendations
    assert "recommendations" in data
    recommendations = data["recommendations"]
    assert isinstance(recommendations, list)
    
    if len(recommendations) > 0:
        rec = recommendations[0]
        assert "option" in rec
        assert "title" in rec
        assert "description" in rec
        assert "score" in rec
        assert 0 <= rec["score"] <= 100


def test_predict_metadata(client):
    """Test prediction includes metadata"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    payload = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": tomorrow,
        "departure_time": "09:30",
        "include_fares": True
    }
    
    response = client.post("/api/predict", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check metadata
    metadata = data["metadata"]
    assert "processing_time_ms" in metadata
    assert "cache_hit" in metadata
    assert "client_fingerprint" in metadata
    
    # Processing time should be reasonable
    assert metadata["processing_time_ms"] > 0
    assert metadata["processing_time_ms"] < 5000  # <5 seconds


# ============================================================================
# Test: Prediction Endpoint - Validation Errors
# ============================================================================

def test_predict_invalid_crs_code_lowercase(client):
    """Test prediction rejects lowercase CRS codes"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    payload = {
        "origin": "eus",  # Should be uppercase
        "destination": "MAN",
        "departure_date": tomorrow,
        "departure_time": "09:30"
    }
    
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422  # Validation error


def test_predict_invalid_crs_code_length(client):
    """Test prediction rejects invalid CRS code length"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    payload = {
        "origin": "EU",  # Too short
        "destination": "MAN",
        "departure_date": tomorrow,
        "departure_time": "09:30"
    }
    
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


def test_predict_invalid_date_format(client):
    """Test prediction rejects invalid date format"""
    payload = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": "25/12/2024",  # Wrong format
        "departure_time": "09:30"
    }
    
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


def test_predict_past_date(client):
    """Test prediction rejects past dates"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    payload = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": yesterday,
        "departure_time": "09:30"
    }
    
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


def test_predict_far_future_date(client):
    """Test prediction rejects dates too far in future"""
    far_future = (datetime.now() + timedelta(days=100)).strftime("%Y-%m-%d")
    
    payload = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": far_future,
        "departure_time": "09:30"
    }
    
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


def test_predict_invalid_time_format(client):
    """Test prediction rejects invalid time format"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    payload = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": tomorrow,
        "departure_time": "9:30 AM"  # Wrong format
    }
    
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


def test_predict_missing_required_field(client):
    """Test prediction rejects missing required fields"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    payload = {
        "origin": "EUS",
        # Missing destination
        "departure_date": tomorrow,
        "departure_time": "09:30"
    }
    
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


# ============================================================================
# Test: Feedback Endpoint
# ============================================================================

def test_feedback_submission_success(client):
    """Test successful feedback submission"""
    payload = {
        "request_id": "req_test123",
        "actual_delay_minutes": 15,
        "was_cancelled": False,
        "rating": 4,
        "comment": "Prediction was fairly accurate"
    }
    
    response = client.post("/api/feedback", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "feedback_id" in data
    assert "received_at" in data
    assert "message" in data
    
    # Check feedback ID format
    assert data["feedback_id"].startswith("fb_")


def test_feedback_minimal_data(client):
    """Test feedback with minimal required data"""
    payload = {
        "request_id": "req_test123",
        "was_cancelled": False
    }
    
    response = client.post("/api/feedback", json=payload)
    assert response.status_code == 200


def test_feedback_cancelled_train(client):
    """Test feedback for cancelled train"""
    payload = {
        "request_id": "req_test123",
        "was_cancelled": True,
        "rating": 1,
        "comment": "Train was cancelled"
    }
    
    response = client.post("/api/feedback", json=payload)
    assert response.status_code == 200


def test_feedback_invalid_rating(client):
    """Test feedback rejects invalid rating"""
    payload = {
        "request_id": "req_test123",
        "rating": 6,  # Must be 1-5
        "was_cancelled": False
    }
    
    response = client.post("/api/feedback", json=payload)
    assert response.status_code == 422


def test_feedback_comment_too_long(client):
    """Test feedback rejects overly long comments"""
    payload = {
        "request_id": "req_test123",
        "comment": "a" * 501,  # Max 500 characters
        "was_cancelled": False
    }
    
    response = client.post("/api/feedback", json=payload)
    assert response.status_code == 422


# ============================================================================
# Test: Rate Limiting
# ============================================================================

def test_rate_limit_minute_limit(client):
    """Test per-minute rate limit"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    payload = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": tomorrow,
        "departure_time": "09:30"
    }
    
    # Make requests up to limit
    for i in range(100):
        response = client.post("/api/predict", json=payload)
        assert response.status_code == 200, f"Request {i+1} failed"
    
    # Next request should be rate limited
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()


def test_rate_limit_different_clients(client):
    """Test rate limits are per-client"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    payload = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": tomorrow,
        "departure_time": "09:30"
    }
    
    # First client makes requests
    for _ in range(50):
        response = client.post("/api/predict", json=payload)
        assert response.status_code == 200
    
    # Second client with different user-agent should have separate limit
    client2 = TestClient(app)
    response = client2.post(
        "/api/predict",
        json=payload,
        headers={"User-Agent": "Different-Client"}
    )
    assert response.status_code == 200


# ============================================================================
# Test: Statistics Endpoint
# ============================================================================

def test_statistics_endpoint(client):
    """Test statistics endpoint returns usage data"""
    # Make a few requests first
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    for _ in range(3):
        client.post("/api/predict", json={
            "origin": "EUS",
            "destination": "MAN",
            "departure_date": tomorrow,
            "departure_time": "09:30"
        })
    
    response = client.get("/api/stats")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "total_requests" in data
    assert "total_errors" in data
    assert "uptime_seconds" in data
    assert "uptime_hours" in data
    assert "error_rate" in data
    assert "version" in data
    
    # Check reasonable values
    assert data["total_requests"] >= 3  # At least our test requests
    assert data["uptime_seconds"] >= 0
    assert data["error_rate"] >= 0


# ============================================================================
# Test: CORS Headers
# ============================================================================

def test_cors_headers_present(client):
    """Test CORS headers are present in responses"""
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"}
    )
    
    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers


# ============================================================================
# Test: Error Handling
# ============================================================================

def test_404_on_invalid_endpoint(client):
    """Test 404 for non-existent endpoints"""
    response = client.get("/api/nonexistent")
    assert response.status_code == 404


def test_method_not_allowed(client):
    """Test 405 for wrong HTTP method"""
    response = client.get("/api/predict")  # Should be POST
    assert response.status_code == 405


# ============================================================================
# Test: Request ID Generation
# ============================================================================

def test_unique_request_ids(client):
    """Test that each request gets a unique ID"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    payload = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": tomorrow,
        "departure_time": "09:30"
    }
    
    request_ids = set()
    for _ in range(10):
        response = client.post("/api/predict", json=payload)
        data = response.json()
        request_ids.add(data["request_id"])
    
    # All IDs should be unique
    assert len(request_ids) == 10


# ============================================================================
# Test: Response Time Performance
# ============================================================================

def test_prediction_performance(client):
    """Test prediction endpoint responds quickly"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    payload = {
        "origin": "EUS",
        "destination": "MAN",
        "departure_date": tomorrow,
        "departure_time": "09:30"
    }
    
    times = []
    for _ in range(10):
        start = time.time()
        response = client.post("/api/predict", json=payload)
        duration = time.time() - start
        times.append(duration)
        assert response.status_code == 200
    
    avg_time = sum(times) / len(times)
    
    # Average should be under 200ms (target from plan)
    assert avg_time < 0.2, f"Average response time {avg_time:.3f}s exceeds 200ms target"


# ============================================================================
# Test: Swagger Documentation
# ============================================================================

def test_swagger_docs_available(client):
    """Test Swagger documentation is accessible"""
    response = client.get("/docs")
    assert response.status_code == 200


def test_redoc_available(client):
    """Test ReDoc documentation is accessible"""
    response = client.get("/redoc")
    assert response.status_code == 200


def test_openapi_schema_available(client):
    """Test OpenAPI schema is accessible"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    # Check schema structure
    schema = response.json()
    assert "info" in schema
    assert "paths" in schema
    assert "components" in schema


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
