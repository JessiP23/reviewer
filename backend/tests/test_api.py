from fastapi.testclient import TestClient

from reviewer.main import app


def test_upload_to_graphql_end_to_end() -> None:
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200

        accepted = client.post(
            "/v1/reviews",
            files={"file": ("financials.csv", b"Revenue,100000\nNet income,12000\n", "text/csv")},
        )
        assert accepted.status_code == 202
        review_id = accepted.json()["id"]

        result = client.post(
            "/graphql",
            json={
                "query": """
                    query Review($id: ID!) {
                      review(id: $id) { id filename status metrics { key value } }
                    }
                """,
                "variables": {"id": review_id},
            },
        )
        assert result.status_code == 200
        review = result.json()["data"]["review"]
        assert review["filename"] == "financials.csv"
        assert review["status"] == "completed"
        assert {metric["key"] for metric in review["metrics"]} >= {
            "revenue",
            "net_income",
            "net_margin",
        }


def test_rejects_unsupported_and_empty_files() -> None:
    with TestClient(app) as client:
        unsupported = client.post(
            "/v1/reviews",
            files={"file": ("data.zip", b"bytes", "application/zip")},
        )
        empty = client.post(
            "/v1/reviews",
            files={"file": ("data.csv", b"", "text/csv")},
        )
        assert unsupported.status_code == 415
        assert empty.status_code == 400


def test_chat_and_document_endpoints() -> None:
    content = b"Revenue,100000\nNet income,12000\n"
    with TestClient(app) as client:
        accepted = client.post(
            "/v1/reviews",
            files={"file": ("financials.csv", content, "text/csv")},
        )
        assert accepted.status_code == 202
        review_id = accepted.json()["id"]

        chat = client.post(
            f"/v1/reviews/{review_id}/chat",
            json={"message": "What is revenue?"},
        )
        assert chat.status_code == 200
        reply = chat.json()["reply"]
        assert "100,000" in reply

        doc = client.get(f"/v1/reviews/{review_id}/document")
        assert doc.status_code == 200
        assert doc.content == content
        assert "financials.csv" in doc.headers["content-disposition"]


def test_chat_and_document_not_found() -> None:
    with TestClient(app) as client:
        chat = client.post(
            "/v1/reviews/does-not-exist/chat",
            json={"message": "What is revenue?"},
        )
        assert chat.status_code == 404
        doc = client.get("/v1/reviews/does-not-exist/document")
        assert doc.status_code == 404

