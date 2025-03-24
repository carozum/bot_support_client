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
