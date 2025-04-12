from fastapi import FastAPI, HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List
import os
from models import FichierItem, DatasetItem, ChunkWithQA, ChunkOnly, QAItem, QAWithChunkItem, ChunkItem

app = FastAPI(
    title="ETL API",
    description="API pour interroger les données extraites, chunkées et enrichies dans PostgreSQL",
    version="1.0.0"
)

def get_connection():
    return psycopg2.connect(
        database=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "db"),
        port="5432",
        cursor_factory=RealDictCursor,
    )


# ----------- ROUTE 1 : /fichiers ----------- #

@app.get("/fichiers", response_model=List[FichierItem], summary="Lister les fichiers", tags=["Fichiers"])
def get_fichiers():
    """Retourne la liste des fichiers présents dans la base, triée par date d'insertion."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id_source, nom_fichier, created_at FROM aide_ligne_fichier ORDER BY created_at DESC")
                rows = cur.fetchall()
                return [
                    {
                        "id_source": r["id_source"],
                        "nom_fichier": r["nom_fichier"],
                        "created_at": r["created_at"].isoformat()
                    }
                    for r in rows
                ]
    except Exception as e:
        import traceback
        print("Erreur dans /fichiers :", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



# ----------- ROUTE 2 : /dataset ----------- #

@app.get("/dataset", response_model=List[DatasetItem], summary="Dataset Q/R", tags=["Dataset"])
def get_dataset():
    """Retourne toutes les paires question/réponse en les joignant avec leurs chunks et fichiers d'origine."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT question, réponse as response FROM aide_ligne_qa;")
            return cur.fetchall()
            # return [{"question": row["question"],"context":row[' "response": row["réponse"]} for row in rows]



# ------------------ ROUTE 3 : /qa/{id} ------------------------ #

@app.get("/qa/{id}", response_model=List[QAItem], summary="Q/R par fichier", tags=["QA"])
def get_qa_by_file_id(id: int):
    """Retourne toutes les Q/R associées à un fichier spécifique (via id_source)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT qa.id_qa, qa.question, qa.réponse, qa.id_chunk
                FROM aide_ligne_qa qa
                JOIN aide_ligne_chunk c ON c.id_chunk = qa.id_chunk
                WHERE c.id_source = %s
		ORDER BY qa.id_qa;
            """, (id,))
            return cur.fetchall()

# ------------------ ROUTE 4 : /fichier/{id} ------------------------ #

@app.get("/fichier/{id}", response_model=List[ChunkWithQA], summary="Chunks + Q/R", tags=["Chunks"])
def get_chunks_with_qa_by_file_id(id: int):
    """Retourne tous les chunks + Q/R associés à un fichier (id_source)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.id_chunk, c.titre, c.contenu, c.page, c.nombre_tokens,
                    COALESCE(json_agg(json_build_object('question', q.question, 'réponse', q.réponse))
                        FILTER (WHERE q.id_qa IS NOT NULL), '[]') as questions_reponses
                FROM aide_ligne_chunk c
                LEFT JOIN aide_ligne_qa q ON c.id_chunk = q.id_chunk
                WHERE c.id_source = %s
                GROUP BY c.id_chunk, c.titre, c.contenu, c.page, c.nombre_tokens
                ORDER BY c.page, c.id_chunk;
            """, (id,))
            return cur.fetchall()

# ------------------ ROUTE 5 : /chunks/{id} ------------------------ #

@app.get("/chunks/{id}", response_model=List[ChunkOnly], summary="Chunks seuls", tags=["Chunks"])
def get_chunks_by_file_id(id: int):
    """Retourne les chunks d'un fichier avec leurs métadonnées (titre, contenu, nb tokens, page...)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id_chunk, titre, contenu, page, nombre_tokens, id_source
                FROM aide_ligne_chunk
                WHERE id_source = %s;
            """, (id,))
            return cur.fetchall()

# ----------- ROUTE 6 : /qa ----------- #

@app.get("/qa", response_model=List[QAWithChunkItem], summary="Q/R + Contexte", tags=["QA"])
def get_qa_with_context():
    """Retourne les questions, réponses, et contexte associé (chunk)"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT qa.question, qa.réponse as response, c.contenu as context
                FROM aide_ligne_qa qa
                JOIN aide_ligne_chunk c ON qa.id_chunk = c.id_chunk;
            """)
            rows = cur.fetchall()
            return [
                {
                    "question": r["question"],
                    "response": r["response"],
                    "context": r["context"]
                }
                for r in rows
            ]


# ----------- ROUTE 7 : /chunks ----------- #

@app.get("/chunks", response_model=List[ChunkItem], summary="Chunks disponibles", tags=["Chunks"])
def get_chunks():
    """Retourne tous les chunks présents en base avec leur contenu et métadonné.es"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id_chunk, contenu, page, id_source
                FROM aide_ligne_chunk;
            """)
            rows = cur.fetchall()
            return [
                {
                    "id_chunk": r["id_chunk"],
                    "contenu": r["contenu"],
                    "page": r["page"],
                    "id_source": r["id_source"]
                }
                for r in rows
            ]

