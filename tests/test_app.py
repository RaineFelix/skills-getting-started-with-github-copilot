"""Tests for Mergington High School Activities API"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to a known state before each test"""
    # Store original state
    original_activities = {k: v.copy() for k, v in activities.items()}
    
    yield
    
    # Restore original state after test
    for activity_name in list(activities.keys()):
        if activity_name not in original_activities:
            del activities[activity_name]
        else:
            activities[activity_name]["participants"] = original_activities[activity_name]["participants"].copy()


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_success(self, client, reset_activities):
        """Test successfully retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert data["Chess Club"]["description"] == "Learn strategies and compete in chess tournaments"
        assert data["Chess Club"]["max_participants"] == 12
        assert len(data["Chess Club"]["participants"]) > 0
    
    def test_get_activities_has_required_fields(self, client, reset_activities):
        """Test that activities have all required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successfully signing up for an activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify participant was added
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_activity_not_found(self, client, reset_activities):
        """Test signing up for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_signup_duplicate_email(self, client, reset_activities):
        """Test that duplicate signups are rejected"""
        # Try to sign up with an email that's already registered
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]
    
    def test_signup_multiple_activities(self, client, reset_activities):
        """Test that same student can sign up for multiple activities"""
        email = "multistudent@mergington.edu"
        
        # Sign up for Chess Club
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Sign up for Programming Class
        response2 = client.post(
            "/activities/Programming Class/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        assert email in activities["Chess Club"]["participants"]
        assert email in activities["Programming Class"]["participants"]


class TestUnregisterFromActivity:
    """Tests for POST /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successfully unregistering from an activity"""
        email = "michael@mergington.edu"
        assert email in activities["Chess Club"]["participants"]
        
        response = client.post(
            "/activities/Chess Club/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        
        # Verify participant was removed
        assert email not in activities["Chess Club"]["participants"]
    
    def test_unregister_activity_not_found(self, client, reset_activities):
        """Test unregistering from non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/unregister",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_unregister_not_registered(self, client, reset_activities):
        """Test unregistering when student is not registered"""
        response = client.post(
            "/activities/Chess Club/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"]
    
    def test_unregister_and_rejoin(self, client, reset_activities):
        """Test that student can re-join after unregistering"""
        email = "rejoin@mergington.edu"
        
        # Sign up
        client.post("/activities/Chess Club/signup", params={"email": email})
        assert email in activities["Chess Club"]["participants"]
        
        # Unregister
        response = client.post("/activities/Chess Club/unregister", params={"email": email})
        assert response.status_code == 200
        assert email not in activities["Chess Club"]["participants"]
        
        # Re-join
        response = client.post("/activities/Chess Club/signup", params={"email": email})
        assert response.status_code == 200
        assert email in activities["Chess Club"]["participants"]


class TestEdgeCases:
    """Tests for edge cases and capacity limits"""
    
    def test_capacity_not_enforced_on_signup(self, client, reset_activities):
        """Test that capacity limits don't prevent signup (current behavior)"""
        # Note: Current implementation doesn't enforce max_participants
        # This test documents the current behavior
        activity = activities["Tennis Club"]
        initial_count = len(activity["participants"])
        
        # Add students beyond capacity
        for i in range(10):
            email = f"student{i}@mergington.edu"
            response = client.post(
                "/activities/Tennis Club/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all were added (no capacity enforcement)
        assert len(activity["participants"]) == initial_count + 10
    
    def test_signup_with_special_characters_in_email(self, client, reset_activities):
        """Test that emails with special characters are handled"""
        email = "student+tag@mergington.edu"
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        assert email in activities["Chess Club"]["participants"]
