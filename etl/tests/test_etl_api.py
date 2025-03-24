import pytest
from fastapi.testclient import TestClient
from etl.etl_api import app

client = TestClient(app)


def test_get_fichiers():
    response = client.get("/fichiers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    if response.json():
        assert "id_source" in response.json()[0]
        assert "nom_fichier" in response.json()[0]


def test_get_dataset():
    response = client.get("/dataset")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    if response.json():
        assert "question" in response.json()[0]
        assert "response" in response.json()[0]


def test_get_chunks_with_qa_by_file_id():
    # Attention : 1 doit être un id_source existant en base. Peut être changé
    response = client.get("/fichier/1")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        assert isinstance(response.json(), list)
        if response.json():
            assert "contenu" in response.json()[0]
            assert "questions_reponses" in response.json()[0]


def test_get_chunks_by_file_id():
    # Attention : 1 doit être un id_source existant en base. Peut être changé
    response = client.get("/chunks/1")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        assert isinstance(response.json(), list)
        if response.json():
            assert "contenu" in response.json()[0]
            assert "id_chunk" in response.json()[0]


def test_get_qa_by_file_id():
    # Attention : 1 doit être un id_source existant en base. Peut être changé
    response = client.get("/qa/1")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        assert isinstance(response.json(), list)
        if response.json():
            assert "question" in response.json()[0]
            assert "réponse" in response.json()[0]
