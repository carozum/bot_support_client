from fastapi import FastAPI, UploadFile, File, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import shutil
from pathlib import Path
import os
import openai
from starlette.status import HTTP_401_UNAUTHORIZED
from typing import Optional
from app.services import openai_service 

# Création du microservices
app = FastAPI(
    title="APP API",
    description="API pour uploader des fichiers, visualiser la liste des fichiers uploadés et interroger le modèle",
    version="1.0.0"
)

# Crée les dossiers s'ils n'existent pas (utile en CI)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# RÉPERTOIRES FIXES
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_BRUTE_DIR = BASE_DIR / "data-brute"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Authentification basique
security = HTTPBasic()

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = os.getenv("BASIC_AUTH_USER", "admin")
    correct_password = os.getenv("BASIC_AUTH_PASS", "password")
    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
            headers={"WWW-Authenticate": "Basic"},
        )

# Page Admin avec upload et liste des fichiers
@app.get("/admin", response_class=HTMLResponse, summary="Page Admin", tags=["Admin"])
def admin_page(request: Request, credentials: HTTPBasicCredentials = Depends(authenticate)):
    """route pour  servir le fichier html avec formulaire d'upload """
    files = os.listdir(DATA_BRUTE_DIR)
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "files": files
    })


@app.post("/upload", summary="Uploader un fichier", tags=["Admin"])
async def upload_file(file: UploadFile = File(...), credentials: HTTPBasicCredentials = Depends(authenticate)):
    """route pour permettre l'ajout de fichiers à indexer"""
    destination = DATA_BRUTE_DIR / file.filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return RedirectResponse(url="/admin", status_code=303)



# Chat avec GPT-4o

@app.get("/chat", response_class=HTMLResponse, summary="Poser une question", tags=["Chat"])
def chat_form(request: Request, credentials: HTTPBasicCredentials = Depends(authenticate)):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.post("/chat", response_class=HTMLResponse, summary="Obtenir une réponse", tags=["Chat"])
async def answer(request: Request, question: str = Form(...), credentials: HTTPBasicCredentials = Depends(authenticate)):
    try:
        answer = openai-service.ask_openai(question)
    except Exception as e:
        answer = f"Erreur lors de l'appel à l'API : {e}"

    return templates.TemplateResponse("chat.html", {
        "request": request,
        "question": question,
        "answer": answer
    })


