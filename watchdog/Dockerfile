FROM python:3.10-slim

# Installer les dépendances système (tesseract + poppler-utils)
RUN apt-get update && \
    apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Dossier de travail
WORKDIR /app

# copie et installation des requirements python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Création des dossiers nécessaires
RUN mkdir -p /app/data-brute
RUN mkdir -p /app/resultat_extraction
RUN mkdir -p /app/log

# copie du reste du code
COPY . .

# lancer la pipeline automatique
CMD ["python", "pipeline_etl.py", "--watch"]
