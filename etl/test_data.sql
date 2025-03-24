INSERT INTO aide_ligne_fichier (nom_fichier) VALUES ('Fichier_test.pdf');

INSERT INTO aide_ligne_chunk (titre, contenu, id_source, page, nombre_tokens)
VALUES ('1.1 Introduction', 'Contenu du chunk', 1, 1, 42);

INSERT INTO aide_ligne_qa (question, réponse, id_chunk)
VALUES ('Quelle est la fonction du bouton ?', 'Il permet de valider la saisie.', 1);
