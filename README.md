# Catalogue de jeux Steam — Projet NoSQL (MongoDB)

Projet universitaire : modélisation d'un catalogue de produits (jeux vidéo Steam) en
base MongoDB, avec API et interface web. Dataset réel : [Steam Games Dataset (Kaggle)](https://www.kaggle.com/datasets/fronkongames/steam-games-dataset).

Pour la description complète du projet (justification NoSQL, schéma détaillé,
résultats des requêtes), voir **[RAPPORT_PROJET.pdf](RAPPORT_PROJET.pdf)**.

## Prérequis

- Python 3.11+
- MongoDB installé et lancé localement (`mongodb://localhost:27017`)
- `games.csv` present a la racine du projet (dataset Kaggle, non versionne dans git — voir `.gitignore`)

## Installation

```bash
pip install -r requirements.txt
```

## Lancer le projet

```bash
# 1. Peupler la base MongoDB depuis games.csv (a faire une seule fois, ou pour rafraichir)
python populate_db.py

# 2. Lancer l'API
uvicorn api:app --reload --port 8000
# Documentation interactive : http://127.0.0.1:8000/docs

# 3. Lancer l'interface (dans un autre terminal)
streamlit run app_streamlit.py
# http://localhost:8501
```

## Structure du projet

| Fichier | Rôle |
|---|---|
| `games.csv` | Dataset source (non versionné, a telecharger depuis Kaggle) |
| `inspect_games.py` | Inspection du CSV (types, valeurs manquantes, format des colonnes) |
| `inspect_cardinalities.py` | Cardinalités réelles des genres/catégories/tags/développeurs/éditeurs |
| `populate_db.py` | Peuplement de la base MongoDB `steam_catalog` (5 collections) depuis le CSV |
| `queries.py` | Les 13 requêtes métier (pipelines d'agrégation), utilisées par l'API |
| `business_queries.py` | Les mêmes 13 requêtes, exécutées et affichées en console (validation) |
| `api.py` | API FastAPI exposant les 13 requêtes |
| `app_streamlit.py` | Interface Streamlit (tableaux + graphiques) consommant l'API |
| `erd_diagram.png` | Schéma ERD des 5 collections |
| `RAPPORT_PROJET.md` / `.pdf` | Rapport complet du projet |

## Schéma de la base (`steam_catalog`)

5 collections : `games` (centrale), `companies` (développeurs/éditeurs, référencée),
`genres`, `categories`, `tags` (rollups analytiques). Détails et justification dans
le rapport, section 2.

## Besoins utilisateurs couverts

13 questions métier (genres dominants, développeurs les plus prolifiques, répartition
des prix, support multi-plateforme, combinaisons de catégories, etc.) — liste complète
et résultats réels dans le rapport, section 5.
