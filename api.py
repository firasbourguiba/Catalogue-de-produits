"""
API FastAPI exposant les 13 requetes metier sur la base MongoDB steam_catalog.
Lancer avec : uvicorn api:app --reload --port 8000
Documentation interactive : http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

import queries

app = FastAPI(
    title="Steam Catalog API",
    description="API du projet NoSQL - catalogue de jeux Steam (MongoDB)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Steam Catalog API",
        "docs": "/docs",
        "endpoints": [
            "/api/genres/top",
            "/api/developers/top",
            "/api/price-distribution",
            "/api/genres/best-game",
            "/api/releases/by-year",
            "/api/genres/platform-support",
            "/api/categories/top-combos",
            "/api/tags/best-ratio",
            "/api/languages/stats",
            "/api/publishers/top",
            "/api/dlc/impact",
            "/api/games/free-to-play/top",
            "/api/studios/self-published",
        ],
    }


@app.get("/api/stats", summary="Compteurs des collections (pour tuiles de synthese)")
def stats():
    return queries.collection_stats()


@app.get("/api/genres/top", summary="Q1 - Genres les plus representes et leur prix moyen")
def genres_top(limit: int = Query(10, ge=1, le=50)):
    return queries.top_genres(limit=limit)


@app.get("/api/developers/top", summary="Q2 - Developpeurs les plus prolifiques et leur note metacritic moyenne")
def developers_top(limit: int = Query(10, ge=1, le=50)):
    return queries.top_developers(limit=limit)


@app.get("/api/price-distribution", summary="Q3 - Repartition des jeux par tranche de prix")
def price_distribution():
    return queries.price_distribution()


@app.get("/api/genres/best-game", summary="Q4 - Meilleur jeu par genre selon le ratio d'avis positifs")
def genres_best_game(min_reviews: int = Query(100, ge=1), limit: int = Query(15, ge=1, le=50)):
    return queries.best_game_by_genre(min_reviews=min_reviews, limit=limit)


@app.get("/api/releases/by-year", summary="Q5 - Evolution du nombre de sorties de jeux par annee")
def releases_by_year():
    return queries.releases_by_year()


@app.get("/api/genres/platform-support", summary="Q6 - Pourcentage de support Mac/Linux par genre majeur")
def genres_platform_support(min_games: int = Query(500, ge=1)):
    return queries.platform_support_by_genre(min_games=min_games)


@app.get("/api/categories/top-combos", summary="Q7 - Combinaisons de categories les plus frequentes")
def categories_top_combos(limit: int = Query(10, ge=1, le=50)):
    return queries.top_category_combos(limit=limit)


@app.get("/api/tags/best-ratio", summary="Q8 - Tags associes au meilleur ratio d'avis positifs")
def tags_best_ratio(min_reviews: int = Query(20, ge=1), min_games: int = Query(50, ge=1), limit: int = Query(10, ge=1, le=50)):
    return queries.best_tags_by_positive_ratio(min_reviews=min_reviews, min_games=min_games, limit=limit)


@app.get("/api/languages/stats", summary="Q9 - Nombre moyen de langues supportees et jeux les plus multilingues")
def languages_stats(top_n: int = Query(10, ge=1, le=50)):
    return queries.language_stats(top_n=top_n)


@app.get("/api/publishers/top", summary="Q10 - Editeurs avec la meilleure moyenne de recommandations par jeu")
def publishers_top(min_games: int = Query(5, ge=1), limit: int = Query(10, ge=1, le=50)):
    return queries.top_publishers(min_games=min_games, limit=limit)


@app.get("/api/dlc/impact", summary="Q11 - Lien entre nombre de DLC et succes du jeu")
def dlc_impact():
    return queries.dlc_impact()


@app.get("/api/games/free-to-play/top", summary="Q12 - Jeux Free To Play les plus recommandes")
def games_free_to_play_top(limit: int = Query(10, ge=1, le=50)):
    return queries.top_free_to_play(limit=limit)


@app.get("/api/studios/self-published", summary="Q13 - Studios qui s'auto-editent le plus")
def studios_self_published(limit: int = Query(10, ge=1, le=50)):
    return queries.self_published_studios(limit=limit)
