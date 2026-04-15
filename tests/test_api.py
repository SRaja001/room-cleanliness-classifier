from fastapi.testclient import TestClient

from app.api import create_app


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app_name": "room-cleanliness-classifier",
    }


def test_classify_endpoint_returns_contract_shape() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/classify",
        json={
            "image_base64": "cGxhY2Vob2xkZXI=",
            "image_role": "after",
            "room_type": "bedroom",
            "source": "test-suite",
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["classification"] == "borderline"
    assert body["prediction_id"]
    assert body["needs_review"] is True
    assert "visible_reasons" in body
    assert body["image_quality"]["is_acceptable"] is True
    assert body["model_usage"]["input_tokens"] == 0
    assert body["model_usage"]["estimated_cost_usd"] == 0.0


def test_classify_endpoint_requires_an_image_reference() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/classify",
        json={
            "image_role": "after",
            "room_type": "bedroom",
            "source": "test-suite",
        },
    )

    assert response.status_code == 422


def test_admin_review_endpoint_accepts_review_for_existing_prediction() -> None:
    client = TestClient(create_app())
    classify_response = client.post(
        "/classify",
        json={
            "image_base64": "cGxhY2Vob2xkZXI=",
            "image_role": "after",
            "room_type": "bedroom",
            "source": "test-suite",
        },
    )
    prediction_id = classify_response.json()["prediction_id"]

    review_response = client.post(
        f"/predictions/{prediction_id}/review",
        json={
            "final_classification": "dirty",
            "admin_comment": "Visible trash by the bed.",
            "reviewer": "admin-user",
        },
    )

    assert review_response.status_code == 200
    assert review_response.json() == {
        "prediction_id": prediction_id,
        "final_classification": "dirty",
        "admin_comment": "Visible trash by the bed.",
        "reviewer": "admin-user",
    }


def test_admin_review_endpoint_returns_not_found_for_unknown_prediction() -> None:
    client = TestClient(create_app())

    review_response = client.post(
        "/predictions/unknown/review",
        json={
            "final_classification": "dirty",
            "admin_comment": "Visible trash by the bed.",
            "reviewer": "admin-user",
        },
    )

    assert review_response.status_code == 404


def test_prediction_read_endpoints_return_saved_prediction_and_summary() -> None:
    client = TestClient(create_app())
    classify_response = client.post(
        "/classify",
        json={
            "image_base64": "cGxhY2Vob2xkZXI=",
            "image_role": "after",
            "room_type": "bedroom",
            "source": "test-suite",
        },
    )
    prediction_id = classify_response.json()["prediction_id"]

    prediction_response = client.get(f"/predictions/{prediction_id}")
    list_response = client.get("/predictions")
    summary_response = client.get("/reports/summary")

    assert prediction_response.status_code == 200
    assert prediction_response.json()["prediction_id"] == prediction_id
    assert list_response.status_code == 200
    assert len(list_response.json()["predictions"]) == 1
    assert summary_response.status_code == 200
    assert summary_response.json()["total_predictions"] == 1
    assert summary_response.json()["pending_review"] == 1


def test_prediction_list_endpoint_can_filter_pending_reviews() -> None:
    client = TestClient(create_app())
    first = client.post(
        "/classify",
        json={
            "image_base64": "cGxhY2Vob2xkZXI=",
            "image_role": "after",
            "room_type": "bedroom",
            "source": "test-suite",
        },
    ).json()
    second = client.post(
        "/classify",
        json={
            "image_base64": "cGxhY2Vob2xkZXI=",
            "image_role": "after",
            "room_type": "bedroom",
            "source": "test-suite",
        },
    ).json()
    client.post(
        f"/predictions/{first['prediction_id']}/review",
        json={
            "final_classification": "dirty",
            "admin_comment": "Reviewed.",
            "reviewer": "admin-user",
        },
    )

    response = client.get("/predictions", params={"pending_only": "true"})

    assert response.status_code == 200
    predictions = response.json()["predictions"]
    assert len(predictions) == 1
    assert predictions[0]["prediction_id"] == second["prediction_id"]
