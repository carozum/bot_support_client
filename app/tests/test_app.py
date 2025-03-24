from fastapi.testclient import TestClient
from main import app

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

    response = client.post("/chat", data={"question": "Quelle est la capitale de la France ?"})
    assert response.status_code == 200
    assert "Réponse mockée" in response.text
