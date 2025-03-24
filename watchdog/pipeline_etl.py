import psycopg2
import json
import os
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import logging

# Import des fonctions depuis ton script d'extraction
from extraction import (
    generate_content_from_pdf,
    calculate_tokens,
    generate_questions_truth,
    transform_questions_answers
)

# Configuration de la base de données PostgreSQL
DB_CONFIG = {
    "dbname": "etl_db",
    "user": os.environ['POSTGRES_USER'],
    "password": os.environ['POSTGRES_PASSWORD'],
    "host": os.environ.get("POSTGRES_HOST", "db"),
    "port": "5432"
}

# Répertoire montés
EXTRACTION_DIR = Path("/app/resultat_extraction")
DATA_BRUTE = Path("/app/data-brute")

# Configuration des logs
logging.basicConfig(
    filename="/app/log/pipeline.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def create_database_if_not_exists():
    """Vérifie si la base existe et la crée si nécessaire."""
    conn = psycopg2.connect(
        dbname="postgres", # connexion à la base par défaut
        user=DB_CONFIG["user"], 
        password=DB_CONFIG["password"], 
        host=DB_CONFIG["host"])
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'etl_db';") # pour vérifier l'existence avant de créer la base
    exists = cur.fetchone()
    if not exists:
        cur.execute("CREATE DATABASE etl_db;")
        logging.info("Base de données 'etl_db' créée !")
    cur.close()
    conn.close()


def setup_database():
    """Crée les tables dans PostgreSQL selon la nouvelle structure."""
    create_tables_sql = """
    -- Création de la table des fichiers sources
    CREATE TABLE IF NOT EXISTS aide_ligne_fichier (
        id_source SERIAL PRIMARY KEY,  -- Clé primaire, auto-incrémentée
        nom_fichier TEXT NOT NULL UNIQUE,  -- Nom du fichier, unique pour éviter les doublons
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Date d'insertion automatique
    );

    -- Création de la table des chunks extraits
    CREATE TABLE IF NOT EXISTS aide_ligne_chunk (
        id_chunk SERIAL PRIMARY KEY,  -- Clé primaire, auto-incrémentée
        titre TEXT,  -- Titre du chunk
        contenu TEXT NOT NULL,  -- Contenu du chunk, obligatoire
        id_source INT NOT NULL,  -- Référence au fichier source
        page INTEGER,  -- Numéro de la page du chunk
        nombre_tokens INTEGER,  -- Nombre de tokens dans le chunk
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Date d'insertion automatique
        FOREIGN KEY (id_source) REFERENCES aide_ligne_fichier(id_source) ON DELETE CASCADE  -- Suppression en cascade si le fichier source est supprimé
    );

    -- Création de la table des questions-réponses associées aux chunks
    CREATE TABLE IF NOT EXISTS aide_ligne_qa (
        id_qa SERIAL PRIMARY KEY,  -- Clé primaire, auto-incrémentée
        question TEXT NOT NULL,  -- Question générée
        réponse TEXT NOT NULL,  -- Réponse correspondante
        id_chunk INT NOT NULL,  -- Référence au chunk source
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Date d'insertion automatique
        FOREIGN KEY (id_chunk) REFERENCES aide_ligne_chunk(id_chunk) ON DELETE CASCADE  -- Suppression en cascade si le chunk est supprimé
    );
    """
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(create_tables_sql)
            conn.commit()
        logging.info("Tables créées avec succès !")
    except Exception as e:
        logging.info(f"Erreur lors de la création des tables : {e}")


def insert_file_and_chunks(pdf_file, data):
    # Insérer le fichier dans aide_ligne_fichier
    try: 
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # insérer le fichier dans aide_ligne_fichier
        cur.execute("""
            INSERT INTO aide_ligne_fichier (nom_fichier) VALUES (%s)
            ON CONFLICT (nom_fichier) DO NOTHING RETURNING id_source;;
        """, (pdf_file.name,))
        result = cur.fetchone()
        id_source = result[0] if result else None

        if id_source is None:
            logging.info(f"Le fichier {pdf_file.name} existe déjà en base.")
            return
        
        inserted_chunks = 0
        inserted_qas = 0

        # Insérer les chunks
        for chunk in data:
            # logging.info(chunk)
            cur.execute("""
                INSERT INTO aide_ligne_chunk (titre, contenu, id_source, page, nombre_tokens)
                VALUES (%s, %s, %s, %s, %s) RETURNING id_chunk;
            """, (chunk.get("titre"), chunk["contenu"], id_source, chunk.get("page"), chunk.get("nombre_tokens")))
            id_chunk = cur.fetchone()[0]
            inserted_chunks += 1
            
            # Insérer les QA
            for qa in chunk.get("questions_reponses", []):
                cur.execute("""
                    INSERT INTO aide_ligne_qa (question, réponse, id_chunk)
                    VALUES (%s, %s, %s);
                """, (qa["question"], qa["réponse"], id_chunk))
                inserted_qas += 1
    
        conn.commit()
        cur.close()
        conn.close()
        logging.info(f"{inserted_chunks} chunks insérés et {inserted_qas} Q/A insérées en base avec succès !")
        logging.info("Données insérées en base avec succès !")
    except Exception as e:
        logging.info(f"Erreur lors de l'insertion des données en base : {e}")


# ############################################################################################
# automatisation de la surveillance du répertoire data-brute
# ############################################################################################

def remove_file_from_database(file_name):
    """Supprime les données associées à un fichier JSON supprimé."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        # Supprimer les chunks et Q/A associées en cascade
        cur.execute("""
            DELETE FROM aide_ligne_fichier WHERE nom_fichier = %s RETURNING id_source;
        """, (file_name,))
        
        deleted_source = cur.fetchone()
        
        if deleted_source:
            logging.info(f"Suppression réussie en base pour {file_name}")
        else:
            logging.info(f"Aucun fichier trouvé en base pour {file_name}, peut-être déjà supprimé.")

        conn.commit()
    except Exception as e:
        logging.info(f"Erreur lors de la suppression : {e}")
    finally:
        cur.close()
        conn.close()



def fichier_deja_traite(nom_fichier):
    """Vérifie si un fichier a déjà été traité (présent en base)"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM aide_ligne_fichier WHERE nom_fichier = %s", (nom_fichier,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result is not None
    except Exception as e:
        logging.info(f"Erreur vérification base : {e}")
        return False



class WatchdogHandler(FileSystemEventHandler):
    """Détecte les nouveaux fichiers dans data_brute et lance l'extraction."""
    def on_created(self, event):
        if event.src_path.endswith(".pdf"):
            logging.info(f"Nouveau fichier détecté : {event.src_path}")
            pdf_path = Path(event.src_path)
            logging.info(f"Nouveau PDF détecté : {pdf_path.name}")
            
            # Vérification base
            if fichier_deja_traite(pdf_path.name):
                logging.info(f"⏭️ Le fichier {pdf_path.name} a déjà été traité. Ignoré.")
                return

            try:
                # Étape 1 : extraction + parsing
                json_data, prefix, titre = generate_content_from_pdf(str(pdf_path))

                # Étape 2 : génération des Q/R
                for chunk in json_data:
                    if "questions_reponses" not in chunk or not chunk["questions_reponses"]:
                        nb_tokens = calculate_tokens(chunk["contenu"])
                        qa = generate_questions_truth(chunk["contenu"], nb_tokens)
                        chunk["questions_reponses"] = transform_questions_answers(qa)

                # Étape 3 : sauvegarde finale
                output_json = EXTRACTION_DIR / f"{prefix} {titre}_QA.json"
                with open(output_json, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=4)

                # Étape 4 : insertion en base
                insert_file_and_chunks(pdf_path, json_data)

            except Exception as e:
                logging.info(f"Erreur lors du traitement de {pdf_path.name} : {e}")
    
    
    def on_deleted(self, event):
        """Lorsqu'un fichier PDF est supprimé de data_brute/, on supprime les données associées en base."""
        path = Path(event.src_path)

        if path.suffix.lower() == ".pdf":
            logging.info(f"PDF supprimé : {path.name} → suppression des données en base...")
            remove_file_from_database(path.name)
            
            # Supprimer le JSON enrichi correspondant s’il existe
            json_path = Path("/app/resultat_extraction") / (path.stem + "_QA.json")
            if json_path.exists():
                json_path.unlink()
                logging.info(f"Fichier {json_path.name} supprimé.")



def start_watchdog():
    """Démarre le watcher pour surveiller le répertoire data_brute."""
    observer = Observer()
    event_handler = WatchdogHandler()
    observer.schedule(event_handler, str(DATA_BRUTE), recursive=False)
    observer.start()
    logging.info("Watchdog en cours... Surveille les nouveaux fichiers PDF.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    
    
# Exécution automatique
# def main():
    # vérifier si la base est déjà crée sinon la créer
    # create_database_if_not_exists()
    # setup_database()
    # start_watchdog()
def main():
    setup_database()
    start_watchdog()   

if __name__ == "__main__":
    main()
