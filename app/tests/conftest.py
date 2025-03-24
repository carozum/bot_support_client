# app/tests/conftest.py

import sys
from pathlib import Path

# Ajoute la racine du projet au PYTHONPATH
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
