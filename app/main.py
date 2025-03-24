from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil
from pathlib import Path
import os

# Création du microservices
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# dossier où seront uploadés les pdf
DATA_BRUTE_DIR = Path("/app/data-brute")


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    """route pour  servir le fichier html avec formulaire d'upload """
    files = os.listdir(DATA_BRUTE_DIR)
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "files": files
    })


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """route pour permettre l'ajout de fichiers à indexer"""
    destination = DATA_BRUTE_DIR / file.filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return RedirectResponse(url="/admin", status_code=303)
