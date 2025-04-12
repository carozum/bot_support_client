import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageFilter, ImageOps
import io
import numpy as np
import openai
from openai import OpenAI
import os
import base64
import re
from transformers import AutoTokenizer
import json
import logging
from pathlib import Path
from semantic_chunkers import StatisticalChunker
from semantic_router.encoders import HuggingFaceEncoder

huggingface = os.environ['HUGGING_FACE_TOKEN']
# Charger le tokenizer du modèle Mistral 7B
tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.3", token=huggingface)

openai.api_key = os.environ["OPENAI_API_KEY"]
client = OpenAI()

encoder = HuggingFaceEncoder(name="sentence-transformers/all-mpnet-base-v2")
chunker = StatisticalChunker(
        threshold_adjustment=0.02,
        encoder = encoder,
        min_split_tokens = 400,
        max_split_tokens=600,
        window_size = 80
        )

def encode_image_to_base64(image_bytes):
    """Encode une image en Base64 pour l'envoyer à OpenAI."""
    return base64.b64encode(image_bytes).decode("utf-8")

def preprocess_image_for_ocr(image):
    """Améliore la qualité de l'image avant OCR (binarisation et ajustements)."""
    image = image.convert("L")  # Convertir en niveaux de gris
    image = image.filter(ImageFilter.SHARPEN)  # Augmenter la netteté
    image = ImageOps.autocontrast(image)  # Améliorer le contraste
    return image


def clean_text(text):
    """Nettoie le texte des caractères parasites et non lisibles."""
    text = text.replace("…", "").strip()
    text = re.sub(r"[^\w\s.,!?]", "", text)  # Supprime les caractères spéciaux
    text = re.sub(r"\s{2,}", " ", text).strip()  # Supprime les espaces inutiles
    text = re.sub(r"\b(Image|Photo|Screenshot)\b", "", text, flags=re.IGNORECASE)  # Évite les mots superflus
    text = re.sub(r"[^\x00-\x7F]+", "", text)  # Supprime les caractères non imprimables
    return text


def truncate(text):
    """Tronque le texte à la dernière phrase complète (dernier point trouvé) ou à la dernière virgule pour éviter qu'une description s'arrête au milieu d'une phrase."""
    last_period_index = text.rfind(".")
    last_coma_index = text.rfind(",")
    if last_period_index != -1:
        return text[: last_period_index + 1]
    elif last_coma_index != -1:
        return text[: last_coma_index + 1]
    else:
        return text


def review_extracted_text(extracted_text, max_tokens):
    """" Revoit le texte extrait pour estimer s'il peut contituer un texte alternatif. Concerne essentiellement les captures de boutons avec du texte"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Tu es un assistant qui relit les textes extraits par OCR des images et les nettoie des mots superflus ou reformule si nécessaire pour les rendre adaptés aux lecteurs d'écran. S'il n'y a rien à changer, rends le texte extrait comme il t'a été fourni. Si tu ne sais pas rends le texte extrait d'origine. Ta réponse est ce qui sera lu par le screen reader pour faire comprendre un bouton."},
            {"role": "user", "content": f"Voici le texte à travailler:  {extracted_text}"}
        ],
        max_tokens=max_tokens
    )

    return response.choices[0].message.content.strip()


def review_caption(caption, max_tokens):
    """ Revoit les textes alternatifs générés pour les images (essentiellement les captures d'écran qui ont en OCR plus de 30 characters)"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Tu es un assistant qui relit les textes alternatifs générés pour des images ou des boutons et les nettoie des mots superflus ou reformule si nécessaire pour les rendre adaptés aux lecteurs d'écran."},
            {"role": "user", "content": f"Nettoie le texte alternatif suivant pour qu'il soit adapté aux lecteurs d'écran :  {caption}"}
        ],
        max_tokens=max_tokens
    )
    logging.info(response.choices[0].message.content.strip())
    return response.choices[0].message.content.strip()

def generate_text_image(image_bytes, max_tokens=30):
    """Envoie l'image à OpenAI GPT-4o pour générer une description concise d'une image qui est une capture d'écran Octime"""
    image_base64 = encode_image_to_base64(image_bytes)
    image_url = f"data:image/png;base64,{image_base64}"
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Tu es un assistant qui génère des textes alternatifs pour des images, qui seront utilisés par des lecteurs d'écran."},
            {"role": "user", "content":   [
                {"type": "text", "text": "Génère le texte alternatif adapté aux lecteurs d'écran. Assure-toi que la phrase est complète et descriptive. Donne directement le texte."},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]}
        ],
        max_tokens=max_tokens
    )
    logging.info(response.choices[0].message.content.strip())
    return response.choices[0].message.content.strip()


def generate_text_button(image_bytes, max_tokens=15):
    """Envoie l'image à OpenAI GPT-4o pour générer une description concise d'une image qui est une icône"""
    image_base64 = encode_image_to_base64(image_bytes)
    image_url = f"data:image/png;base64,{image_base64}"
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Tu es un assistant qui génère des textes alternatifs pour des icônes et boutons inclus dans une documentation en ligne afin de la rendre accessible au screen reader."},
            {"role": "user", "content":   [
                {"type": "text", "text": "Décrit l'icone' de façon adaptée aux lecteurs d'écran. Donne directement le texte."},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]}
        ],
        max_tokens=max_tokens
    )
    logging.info(response.choices[0].message.content.strip())
    return response.choices[0].message.content.strip()


def calculate_tokens(text):
    """Calcule le nombre de tokens dans le texte en utilisant le tokenizer du modèle Mistral 7B"""
    tokens = tokenizer.encode(text)
    return len(tokens)


def clean_chunk_content(content, title_to_remove):
    """Nettoie le contenu des chunks en enlevant les informations de bas de page."""
    lines = content.split("\n")
    cleaned_lines = []
    escaped_title = re.escape(title_to_remove)
    for line in lines:
        if re.match(r"Page \d+", line):
            continue
        if re.match(r"=+", line):
            continue
        if re.match(rf"\d+ {escaped_title}", line):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)



def generate_content_from_pdf(pdf_path):
    # Obtenir le nom du fichier avec l'extension
    file_name_with_extension = os.path.basename(pdf_path)
    file_name, _= os.path.splitext(file_name_with_extension) # Enlever l'extension du fichier
    logging.info(file_name)
    if "Employé" in file_name :
        prefix = "Employé"
        titre = file_name.replace("Employé ", "")
    elif "Manager" in file_name:
        prefix = "Manager"
        titre = file_name.replace("Manager ", "")
    elif "Gestion" in file_name:
        prefix = "Gestion"
        titre = file_name.replace("Gestion ", "")
        logging.info(f"titre: {titre}")
        logging.info(f"prefix: {prefix}")
    else:
        prefix = "Inconnu"
        titre = file_name  # ou file_name.replace(".pdf", "")
        logging.warning(f"Aucun préfixe détecté pour {file_name}, titre = {titre}")
   
    doc = fitz.open(pdf_path)
    
    # Extraction et reconstruction du texte
    final_document = ""

    for page_num in range(len(doc)):
        page = doc[page_num]

        ### 1. EXTRAIRE LE TEXTE GLOBAL (LIGNE PAR LIGNE) ###
        text_blocks = page.get_text("blocks")
        text_elements = [{"type": "text", "content": blk[4].strip(), "x": blk[0], "y": blk[1], "width": blk[2] - blk[0]} for blk in text_blocks if blk[4].strip()]
        
        ### 2. EXTRAIRE LES IMAGES ET LEURS POSITIONS ###
        image_elements = []
        for img_index, img in enumerate(page.get_images(full=True)):
            logging.info(f"Image {img_index} détectée sur la page {page_num}")
            xref = img[0]  # Identifiant unique de l'image
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            # Protection contre images sans bbox
            rects = page.get_image_rects(xref)
            bbox = rects[0]  # Obtenir la position de l'image (x1, y1, x2, y2)

            # Charger l'image avec PIL
            image = Image.open(io.BytesIO(image_bytes))
            image = preprocess_image_for_ocr(image)
            
            # Application de l'OCR
            extracted_text = pytesseract.image_to_string(image, config='--psm 6').strip()
            extracted_text = clean_text(extracted_text)
            logging.info(f"Texte OCR brut : {extracted_text}")
            
            # Classification des images via OpenAI
            if len(extracted_text) > 30:
                placeholder = f"[Image: {truncate(review_caption(generate_text_image(image_bytes, 30), 30))}]"
            elif len(extracted_text) > 5:
                # placeholder = f"[Image: {extracted_text}]"
                placeholder = f"[Bouton: {truncate(review_caption(generate_text_button(image_bytes, 15), 15))}]"
            else:
                if extracted_text == "de,":
                    placeholder = "[Alt: attention]"
                else : 
                    placeholder = f"[Icône: {truncate(review_caption(generate_text_button(image_bytes, 15), 15))}]"
                    
                    if ("triangle" in placeholder.lower() or "triangulaire" in placeholder.lower() or "pyramide" in placeholder.lower()) and not "triangle rouge" in placeholder.lower():
                        placeholder = ""
            logging.info(f"Placeholder généré : {placeholder}")
                
            
            image_elements.append({"type": "image", "content": placeholder, "x": bbox[0], "y": bbox[1], "width": bbox[2] - bbox[0]})
        
        ### 3. TRIER LES ÉLÉMENTS PAR POSITION ###
        all_elements = text_elements + image_elements
        all_elements = sorted(all_elements, key=lambda e: (e["y"], e["x"]))
        
        ### 4. RECONSTRUCTION DU TEXTE ###
        page_text = "\n"
        for e in all_elements:
            content = e['content'].replace("OCTIME - Module web Employé ", "").replace("                                                                                                                                                                                                                  © 2025 OCTIME", "").replace("OCTIME - Gestion v 11 ", "").replace("                                                                                                                                                                                                                  © 2025 OCTIME", "")            
            page_text += f"{content}\n"

        final_document += page_text + "\n"

    chunks = chunker(docs=[final_document])
    #print(chunks)

    # Etape 1 regrouper les splits
    chunks_list = [chunks[0][i].splits for i in range(len(chunks[0]))]
    logging.info(len(chunks_list))

    # Étape 2 — concaténer les splits
    chunks_flat = []
    for chunk in chunks_list:
        chunk_string = " ".join(chunk).strip()
        chunks_flat.append(chunk_string)
    logging.info(f"chunks_flat {len(chunks_flat)}")

    # Étape 3 — construire les objets JSON
    json_data = []

    for i, chunk_text in enumerate(chunks_flat):
        if not chunk_text:
            continue
        nb_tokens = calculate_tokens(chunk_text)
        json_data.append({
            "titre": f"Chunk {i+1}",
            "contenu": chunk_text,
            "page": None,
            "nom_fichier": os.path.basename(pdf_path),
            "nombre_tokens": nb_tokens
        })
        logging.info({
            "titre": f"Chunk {i+1}",
            "contenu": chunk_text,
            "page": None,
            "nom_fichier": os.path.basename(pdf_path),
            "nombre_tokens": nb_tokens
        })
    logging.info("Extraction et reconstruction terminées !")
    return json_data, prefix, titre


def generate_questions_truth(text, nb_tokens):
    n = nb_tokens // 512 + 1
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[
                {"role": "system", "content": f"""Tu es un assistant au sein de la société Octime et tu génères des questions réponses sur la base de contenu qui te sont fournis. Tes réponses doivent être détaillées et précises. Tu réponds sous la forme d'une liste de {n} JSON dont le format est le suivant : 
                {{
                    "question 1":{{"la question que tu génères":"la réponse que tu génères à ta question}},
                    "question 2":{{"la question que tu génères":"la réponse que tu génères à ta question}},
                    ...
                }}"""},
                {"role": "user", "content": f"Génère {n} questions avec leur réponse au format JSON demandé sur le contenu suivant:\n\n{text}"}
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content

        # Si le retour est du JSON sous forme de string, le parser
        try:
            llm_answer = json.loads(content)
        except json.JSONDecodeError:
            logging.warning(f"Réponse LLM non parseable en JSON :\n{content}")
            return {}

        llm_answer = json.loads(response.choices[0].message.content)
        logging.info(f"question truth {llm_answer}")
        return llm_answer
    except Exception as e:
        logging.info(f"Erreur lors de la génération des questions/réponses : {e}")
        return {}


def transform_questions_answers(questions_answers):
    """Transforme les questions/réponses en une liste de JSON avec le format [{question: réponse}, {question: réponse}]"""
    transformed = []
    if not questions_answers:
        return transformed
    for key, value in questions_answers.items():
        for question, answer in value.items():
            transformed.append({"question": question, "réponse": answer})
            logging.info(f"Q/A:{question} / {answer}")
    return transformed


def generate_questions_from_json(input_json_path, output_json_path):
    """Génère des questions/réponses à partir d'un JSON existant et sauvegarde le résultat dans un nouveau JSON."""
    # Ouvrir le JSON existant
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Générer des questions/réponses pour chaque chunk de contenu
    for chunk in data:
        if "questions_reponses" not in chunk or not chunk["questions_reponses"]:
            content = chunk["contenu"]
            nb_tokens = calculate_tokens(content)
            questions_answers = generate_questions_truth(content, nb_tokens)
            transformed_questions_answers = transform_questions_answers(questions_answers)
            chunk["questions_reponses"] = transformed_questions_answers


    # Sauvegarder le résultat dans un nouveau JSON
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    logging.info(f"Questions et réponses générées et sauvegardées dans {output_json_path} !")



