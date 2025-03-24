from fastapi.testclient import TestClient
import os
from pathlib import Path
from main import openai_service
from main import app

client = TestClient(app)

# Point d'entrée de ton projet (ex: bot_support_client/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# pour isoler la logique liée à OpenAI et pouvoir changer de  modèle plus facilement
import os
import openai



def test_chat_post(monkeypatch):
    # Mock la fonction ask_openai directement
    def mock_ask_openai(question: str) -> str:
        return "Réponse mockée"

    monkeypatch.setattr(openai_service, "ask_openai", mock_ask_openai)

    response = client.post(
        "/chat",
        data={"question": "Qu'est-ce qu'une API ?"},
        auth=("admin", "password")
    )

    assert response.status_code == 200
    assert "Réponse mockée" in response.text




def test_upload_file(tmp_path):
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"%PDF-1.4 test content")

    # Crée le dossier data-brute à la racine si besoin
    upload_dir = PROJECT_ROOT / "data-brute"
    upload_dir.mkdir(parents=True, exist_ok=True)

    with open(test_file, "rb") as f:
        response = client.post(
            "/upload",
            auth =("admin", "password"),
            files={"file": ("test.pdf", f, "application/pdf")})

    assert response.status_code == 200
    assert "test.pdf" in response.text
