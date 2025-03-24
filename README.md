# Bot Support Client

Ce projet constitue la base d'un projet de création d'un bot de support client.
Il se compose d'un pipeline complet de traitement de documents PDF, extraction de texte, génération automatique de questions/réponses, insertion en base PostgreSQL, et exposition d’une API REST via FastAPI.
Ce pipeline permet d'extraire un dataset d'entrainement pour fine tuner un modèle LMM embarqué Mistral 7B v03.
Il met en place une démarche DEvOps et LLMOps de suivi de projet et de suivi du fine tuning d'un LLM d'IA. 

![CI - ETL Microservice](https://github.com/carozum/bot_support_client/actions/workflows/etl.yml/badge.svg)


## Fonctionnalités

- Upload de fichiers PDF via une interface (microservice `app`)
- Détection automatique des nouveaux fichiers avec `watchdog`
- Extraction du contenu (texte + images avec OCR)
- Nettoyage et structuration du contenu en chunks
- Génération automatique de Q/R avec GPT-4o
- Insertion en base PostgreSQL (3 tables relationnelles)
- API REST pour exposer les données à des fins d'entraînement ou de consultation
- Prêt à être connecté à un pipeline de fine-tuning (LLM)

## Architecture

```bash
.
├── app/                   # Interface upload (FastAPI)
├── watchdog/              # Détection + extraction + insertion en base
├── etl/                   # API REST pour exposer les données
├── data-brute/            # Répertoire des fichiers PDF (monté dans plusieurs services)
├── resultat_extraction/   # Fichiers JSON intermédiaires enrichis
├── .env                   # Variables d'environnement (non versionné)
├── docker-compose.yml     # Orchestration multi-conteneurs
└── README.md              # Ce fichier


## Endpoints principaux de l’API ETL
Méthode	Endpoint	Description
GET	/fichiers	Liste des fichiers présents en base
GET	/dataset	Export des Q/R au format JSONL
GET	/fichier/{id}	Chunks + Q/R associés à un fichier
GET	/chunks/{id}	Chunks seuls (pour RAG)
GET	/qa/{id}	Questions/réponses associées à un fichier
Swagger UI dispo sur : http://localhost:5000/docs

## Lancement
Assurez-vous d'avoir Docker installé, puis : docker-compose up --build

## Variables d’environnement (.env)
Exemple de .env (à adapter selon vos secrets) :

POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=etl_db

HUGGING_FACE_TOKEN=your_hf_token
OPENAI_API_KEY=your_openai_key

## Auteure

Caro Z. Ingénieur IA chez Octime. 
Dans le cadre de la certification Simplon de développeur IA
Spécialisation IA Générative 
