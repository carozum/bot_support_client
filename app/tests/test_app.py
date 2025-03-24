from fastapi.testclient import TestClient
from main import app
import os

client = TestClient(app)

def test_chat_post(monkeypatch):
    # Mock de l'appel à OpenAI pour éviter une requête réelle
    def mock_create(**kwargs):
        class MockResponse:
            class Choice:
                message = type("obj", (object,), {"content": "Réponse mockée"})

            choices = [Choice()]
        return MockResponse()

    monkeypatch.setattr("openai.chat.completions.create", mock_create)

    response = client.post("/chat", auth=('admin', 'password'), data={"question": "Quelle est la capitale de la France ?"})
    assert response.status_code == 200
    assert "Réponse mockée" in response.text




def test_upload_file(tmp_path):
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"%PDF-1.4 test content")

    with open(test_file, "rb") as f:
        response = client.post(
            "/upload",
            auth =("admin", "password"),
            files={"file": ("test.pdf", f, "application/pdf")})

    assert response.status_code == 200
    assert "test.pdf" in response.text
