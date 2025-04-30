from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI, UploadFile, File, Request, Form, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
import shutil
from pathlib import Path
import os
import openai
import requests
from starlette.status import HTTP_401_UNAUTHORIZED
from typing import Optional
import json

# ENV peut être "prod", "test", etc.
ENV = os.getenv("ENV", "prod")

if ENV == "test":
     from app.services import openai_service
else:
     from services import openai_service

# Création du microservices
app = FastAPI(
    title="APP API",
    description="API pour uploader des fichiers, visualiser la liste des fichiers uploadés et interroger le modèle",
    version="1.0.0"
)
Instrumentator().instrument(app).expose(app)

# Dossier courant du fichier main.py
BASE_DIR = Path(__file__).resolve().parent

# Répertoires utiles
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_BRUTE_DIR = BASE_DIR / "data-brute"

# Création des dossiers si absents (utile en CI ou premier lancement)
STATIC_DIR.mkdir(parents=True, exist_ok=True)
DATA_BRUTE_DIR.mkdir(parents=True, exist_ok=True)

# Configuration Jinja2 et statiques
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Authentification basique
# security = HTTPBasic()

# def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
#    correct_username = os.getenv("BASIC_AUTH_USER", "admin")
#    correct_password = os.getenv("BASIC_AUTH_PASS", "password")
#    if credentials.username != correct_username or credentials.password != correct_password:
#        raise HTTPException(
#            status_code=HTTP_401_UNAUTHORIZED,
#            detail="Identifiants invalides",
#            headers={"WWW-Authenticate": "Basic"},
#        )

# ################################## ADMIN ##################################################

# Page Admin avec upload et liste des fichiers
@app.get("/admin", response_class=HTMLResponse, summary="Page Admin", tags=["Admin"])
def admin_page(request: Request):
    """route pour  servir le fichier html avec formulaire d'upload """
    files = os.listdir(DATA_BRUTE_DIR)
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "files": files
    })


@app.post("/upload", summary="Uploader un fichier", tags=["Admin"])
async def upload_file(file: UploadFile = File(...)):
    """route pour permettre l'ajout de fichiers à indexer"""
    destination = DATA_BRUTE_DIR / file.filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/delete", summary="Supprimer un fichier", tags=["Admin"])
async def delete_file(filename: str = Form(...)):
    # Protection contre chemins relatifs malveillants
    safe_filename = os.path.basename(filename)
    file_path = DATA_BRUTE_DIR / safe_filename

    if file_path.exists():
        file_path.unlink()  # Ceci déclenchera le watchdog
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier non trouvé"
        )

    return RedirectResponse(url="/admin", status_code=303)


# ################################ AIDE EN LIGNE ##############################################

# Chat avec GPT-4o

@app.get("/chat", response_class=HTMLResponse, summary="Poser une question", tags=["Chat"])
def chat_form(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

# enrichir cette fonction avec un sélecteur de modèle

@app.post("/chat", response_class=HTMLResponse, summary="Obtenir une réponse", tags=["Chat"])
async def answer(request: Request, question: str = Form(...)):
    try:
        answer = openai_service.ask_openai(question)
    except Exception as e:
        answer = f"Erreur lors de l'appel à l'API : {e}"

    return templates.TemplateResponse("chat.html", {
        "request": request,
        "question": question,
        "answer": answer
    })


def ask_openai(question: str) -> str:
    openai.api_key = os.getenv("OPENAI_API_KEY", "fake-key-for-tests")

    # Utiliser json.dumps pour échapper correctement les caractères spéciaux
    escaped_question = json.dumps(question, ensure_ascii=False)

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Tu es un assistant qui aide à comprendre une documation en ligne"},
            {"role": "user", "content": escaped_question}
        ],
        temperature=0.3,
        top_p=0.5,
        stream=True
    )

    for chunk in response:
        print(chunk)
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content



HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")
HF_URL = "https://carozum-supportbot.hf.space/generate_stream"


def huggingface_stream(question: str):
    # Utiliser json.dumps pour échapper correctement les caractères spéciaux
    escaped_question = json.dumps(question, ensure_ascii=False)

    response = requests.post(
        HF_URL,
        headers={
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json"
        },
        json={"inputs": escaped_question},
        stream=True
    )
    for chunk in response.iter_content(chunk_size=None):
        yield chunk.decode("utf-8")


@app.post("/ask_stream", summary="stream la réponse", tags=["stream"])
async def ask_stream(request: Request):
    """Stream la réponse du modèle"""
    data = await request.json()
    print(data)
    question = data["question"]
    model_type = data.get("model", "hf")  # hf par défaut

    if model_type == "openai":
        return StreamingResponse(ask_openai(question), media_type="text/plain")
    else:
        return StreamingResponse(huggingface_stream(question), media_type="text/plain")


# ############################# VALIDATION DES Q/A ########################################




# ############################### EVALUATION DES MODELES ###################################


# MOCK - à remplacer par les vraies fonctions de génération au fur et à mesure

def call_mistral_classic(question):
    url = "https://carozum-supportbot.hf.space/generate"

    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {HF_TOKEN}",
                "Content-Type": "application/json"},
            json={"inputs": question},
            timeout=60
        )
        print(response.text)
        if response.status_code != 200:
            return f"Erreur HF ({response.status_code})"

        return response.json().get("response", "réponse vide")
    except Exception as e:
        return f"Exception HF : {e}"


def call_mistral_raft(question):
    return f"Réponse RAFT à : {question}"

def call_mistral_raft_rag(question):
    return f"Réponse RAFT + RAG à : {question}"

def call_mixtral(question):
    return f"Réponse Mixtral à : {question}"

def call_customerbot(question):
    return f"Réponse du modèle Mistral Customerbot à : {question}"

def call_gpt4o(question):
    openai.api_key = os.getenv("OPENAI_API_KEY", "fake-key-for-tests")
    escaped_question = json.dumps(question, ensure_ascii=False)
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Tu es un assistant qui aide à comprendre une documentation en ligne"},
            {"role": "user", "content": escaped_question}
        ],
        temperature=0.3,
        top_p=0.5
    )

    return response.choices[0].message.content


model_colors = {
    "Mistral 7B FT classique": "primary",
    "Mistral 7B FT RAFT": "secondary",
    "Mistral 7B RAFT + RAG": "info",
    "Mixtral 12B FT": "warning",
    "Mistral customerbot": "success",
    "GPT-4o": "danger",
}


@app.get("/evaluation", response_class=HTMLResponse)
async def evaluation_get(request: Request):
    return templates.TemplateResponse("evaluation.html", {
        "request": request,
        "question": None,
        "responses": {},
        "model_colors": model_colors
    })

@app.post("/evaluation", response_class=HTMLResponse)
async def evaluation_post(request: Request, question: str = Form(...)):
    responses = {
        "Mistral 7B FT classique": await run_in_threadpool(call_mistral_classic, question),
        "Mistral 7B FT RAFT": await run_in_threadpool(call_mistral_raft, question),
        "Mistral 7B RAFT + RAG": await run_in_threadpool(call_mistral_raft_rag, question),
        "Mixtral 12B FT": await run_in_threadpool(call_mixtral, question),
        "Mistral customerbot": await run_in_threadpool(call_customerbot, question),
        "GPT-4o": await run_in_threadpool(call_gpt4o, question),
    }

    return templates.TemplateResponse("evaluation.html", {
        "request": request,
        "question": question,
        "responses": responses,
        "model_colors": model_colors
    })
