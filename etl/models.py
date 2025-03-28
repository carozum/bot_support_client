from fastapi import APIRouter
from typing import List
from pydantic import BaseModel

# route /dataset
class DatasetItem(BaseModel):
    question: str
    response: str

# route /fichiers
class FichierItem(BaseModel):
    id_source: int
    nom_fichier: str

# route /qa/{id}
class QAItem(BaseModel):
    id_qa: int
    question: str
    réponse: str
    id_chunk: int

# route /fichier/{id}
class QA(BaseModel):
    question: str
    réponse: str

class ChunkWithQA(BaseModel):
    id_chunk: int
    titre: str
    contenu: str
    page: int
    nombre_tokens: int
    questions_reponses: List[QA]

# route /chunks/{id}
class ChunkOnly(BaseModel):
    id_chunk: int
    titre: str
    contenu: str
    page: int
    nombre_tokens: int
    id_source: int
