from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from vosk import Model, KaldiRecognizer
import wave
import json
import os
import subprocess
import uuid
from pathlib import Path


app = FastAPI()

# Autoriser les appels cross-domain depuis ton frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chargement du modèle
MODEL_PATH = "vosk-model/vosk-model-small-fr-0.22"
if not os.path.exists(MODEL_PATH):
    raise Exception("Modèle VOSK manquant dans le dossier 'vosk-model/'")

model = Model(MODEL_PATH)

# Dossier temporaire pour stocker les fichiers audio
TMP_DIR = Path("/tmp/stt")
TMP_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
def home():
    return {"message": "STT Service is running"}


@app.post("/stt")
async def transcribe(file: UploadFile = File(...)):
    try:
        # Sauvegarder le fichier reçu (webm, ogg, etc.)
        ext = file.filename.split(".")[-1]
        input_path = TMP_DIR / f"input_{uuid.uuid4()}.{ext}"
        with input_path.open("wb") as f:
            f.write(await file.read())

        # Chemin du fichier converti en WAV
        output_path = TMP_DIR / f"converted_{uuid.uuid4()}.wav"

        # Conversion en WAV mono 16bit avec ffmpeg
        subprocess.run([
            "ffmpeg", "-y", "-i", str(input_path),
            "-ar", "16000", "-ac", "1", "-f", "wav", str(output_path)
        ], check=True)

        # Lecture du fichier WAV
        wf = wave.open(str(output_path), "rb")
        rec = KaldiRecognizer(model, wf.getframerate())
        text = ""

        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                text += res.get("text", "") + " "

        final_res = json.loads(rec.FinalResult())
        text += final_res.get("text", "")

        # Nettoyage des fichiers temporaires
        wf.close()
        input_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)

        return {"text": text.strip() or "(aucune transcription détectée)"}

    except subprocess.CalledProcessError:
        return {"error": "Erreur lors de la conversion audio avec ffmpeg"}
    except Exception as e:
        return {"error": f"Erreur inattendue : {str(e)}"}
