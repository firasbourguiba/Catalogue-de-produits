"""
Les 13 requetes metier (agregations MongoDB) sur la base steam_catalog,
factorisees en fonctions reutilisables par l'API (voir business_queries.py
pour la version originale qui a servi a valider chaque requete avec de
vrais resultats).
"""
from pymongo import MongoClient
from pymongo.mongo_client import MongoClient as MongoClientType

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "steam_catalog"

_client = MongoClient(MONGO_URI)
db = _client[DB_NAME]


def _serialize(doc):
    return {k: (str(v) if type(v).__name__ == "ObjectId" else v) for k, v in doc.items()}


def collection_stats():
    return {
        "games": db.games.estimated_document_count(),
        "companies": db.companies.estimated_document_count(),
        "genres": db.genres.estimated_document_count(),
        "categories": db.categories.estimated_document_count(),
        "tags": db.tags.estimated_document_count(),
    }


def top_genres(limit=10):
    pipeline = [
        {"$unwind": "$genres"},
        {"$group": {"_id": "$genres", "game_count": {"$sum": 1}, "avg_price": {"$avg": "$pricing.price"}}},
        {"$sort": {"game_count": -1}},
        {"$limit": limit},
    ]
    return [_serialize(d) for d in db.games.aggregate(pipeline)]


def top_developers(limit=10):
    pipeline = [
        {"$unwind": "$developer_ids"},
        {"$group": {
            "_id": "$developer_ids",
            "game_count": {"$sum": 1},
            "avg_metacritic": {"$avg": {"$cond": [{"$gt": ["$stats.metacritic_score", 0]}, "$stats.metacritic_score", None]}},
        }},
        {"$sort": {"game_count": -1}},
        {"$limit": limit},
        {"$lookup": {"from": "companies", "localField": "_id", "foreignField": "_id", "as": "company"}},
        {"$unwind": "$company"},
        {"$project": {"_id": 0, "developer": "$company.name", "game_count": 1, "avg_metacritic": {"$round": ["$avg_metacritic", 1]}}},
    ]
    return [_serialize(d) for d in db.games.aggregate(pipeline)]


def price_distribution():
    pipeline = [
        {"$bucket": {
            "groupBy": "$pricing.price",
            "boundaries": [0, 0.01, 5, 10, 20, 30, 60, 1000],
            "default": "autre",
            "output": {"game_count": {"$sum": 1}, "avg_recommendations": {"$avg": "$stats.recommendations"}},
        }},
    ]
    return [_serialize(d) for d in db.games.aggregate(pipeline)]


def best_game_by_genre(min_reviews=100, limit=15):
    pipeline = [
        {"$unwind": "$genres"},
        {"$match": {"$expr": {"$gte": [{"$add": ["$stats.positive", "$stats.negative"]}, min_reviews]}}},
        {"$addFields": {"positive_ratio": {"$divide": ["$stats.positive", {"$add": ["$stats.positive", "$stats.negative"]}]}}},
        {"$sort": {"genres": 1, "positive_ratio": -1}},
        {"$group": {"_id": "$genres", "best_game": {"$first": "$name"}, "positive_ratio": {"$first": "$positive_ratio"}, "total_reviews": {"$first": {"$add": ["$stats.positive", "$stats.negative"]}}}},
        {"$sort": {"positive_ratio": -1}},
        {"$limit": limit},
    ]
    return [_serialize(d) for d in db.games.aggregate(pipeline)]


def releases_by_year():
    pipeline = [
        {"$match": {"release_date": {"$ne": None}}},
        {"$group": {"_id": {"$year": "$release_date"}, "game_count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    return [_serialize(d) for d in db.games.aggregate(pipeline)]


def platform_support_by_genre(min_games=500):
    pipeline = [
        {"$unwind": "$genres"},
        {"$group": {
            "_id": "$genres",
            "total": {"$sum": 1},
            "windows": {"$sum": {"$cond": ["$platforms.windows", 1, 0]}},
            "mac": {"$sum": {"$cond": ["$platforms.mac", 1, 0]}},
            "linux": {"$sum": {"$cond": ["$platforms.linux", 1, 0]}},
        }},
        {"$match": {"total": {"$gte": min_games}}},
        {"$project": {
            "total": 1,
            "pct_mac": {"$round": [{"$multiply": [{"$divide": ["$mac", "$total"]}, 100]}, 1]},
            "pct_linux": {"$round": [{"$multiply": [{"$divide": ["$linux", "$total"]}, 100]}, 1]},
        }},
        {"$sort": {"pct_linux": -1}},
    ]
    return [_serialize(d) for d in db.games.aggregate(pipeline)]


def top_category_combos(limit=10):
    pipeline = [
        {"$match": {"categories.1": {"$exists": True}}},
        {"$project": {"categories": 1, "categories_copy": "$categories"}},
        {"$unwind": "$categories"},
        {"$unwind": "$categories_copy"},
        {"$match": {"$expr": {"$lt": ["$categories", "$categories_copy"]}}},
        {"$group": {"_id": {"a": "$categories", "b": "$categories_copy"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    return [_serialize(d) for d in db.games.aggregate(pipeline)]


def best_tags_by_positive_ratio(min_reviews=20, min_games=50, limit=10):
    pipeline = [
        {"$unwind": "$tags"},
        {"$match": {"$expr": {"$gte": [{"$add": ["$stats.positive", "$stats.negative"]}, min_reviews]}}},
        {"$addFields": {"positive_ratio": {"$divide": ["$stats.positive", {"$add": ["$stats.positive", "$stats.negative"]}]}}},
        {"$group": {"_id": "$tags", "avg_positive_ratio": {"$avg": "$positive_ratio"}, "game_count": {"$sum": 1}}},
        {"$match": {"game_count": {"$gte": min_games}}},
        {"$sort": {"avg_positive_ratio": -1}},
        {"$limit": limit},
    ]
    return [_serialize(d) for d in db.games.aggregate(pipeline)]


def language_stats(top_n=10):
    pipeline = [
        {"$facet": {
            "moyenne_globale": [
                {"$project": {"nb_langues": {"$size": "$languages.supported"}}},
                {"$group": {"_id": None, "avg_nb_langues": {"$avg": "$nb_langues"}}},
            ],
            "top_multilingues": [
                {"$project": {"name": 1, "nb_langues": {"$size": "$languages.supported"}}},
                {"$sort": {"nb_langues": -1}},
                {"$limit": top_n},
            ],
        }},
    ]
    result = list(db.games.aggregate(pipeline))
    return result[0] if result else {}


def top_publishers(min_games=5, limit=10):
    pipeline = [
        {"$unwind": "$publisher_ids"},
        {"$group": {"_id": "$publisher_ids", "game_count": {"$sum": 1}, "avg_recommendations": {"$avg": "$stats.recommendations"}}},
        {"$match": {"game_count": {"$gte": min_games}}},
        {"$sort": {"avg_recommendations": -1}},
        {"$limit": limit},
        {"$lookup": {"from": "companies", "localField": "_id", "foreignField": "_id", "as": "company"}},
        {"$unwind": "$company"},
        {"$project": {"_id": 0, "publisher": "$company.name", "game_count": 1, "avg_recommendations": {"$round": ["$avg_recommendations", 0]}}},
    ]
    return [_serialize(d) for d in db.games.aggregate(pipeline)]


def dlc_impact():
    pipeline = [
        {"$bucket": {
            "groupBy": "$pricing.dlc_count",
            "boundaries": [0, 1, 4, 11, 100000],
            "default": "autre",
            "output": {
                "game_count": {"$sum": 1},
                "avg_recommendations": {"$avg": "$stats.recommendations"},
                "avg_positive_ratio": {"$avg": {"$cond": [
                    {"$gt": [{"$add": ["$stats.positive", "$stats.negative"]}, 0]},
                    {"$divide": ["$stats.positive", {"$add": ["$stats.positive", "$stats.negative"]}]},
                    None,
                ]}},
            },
        }},
    ]
    return [_serialize(d) for d in db.games.aggregate(pipeline)]


def top_free_to_play(limit=10):
    pipeline = [
        {"$match": {"pricing.price": 0, "genres": "Free To Play"}},
        {"$sort": {"stats.recommendations": -1}},
        {"$limit": limit},
        {"$project": {"_id": 0, "name": 1, "recommendations": "$stats.recommendations", "positive": "$stats.positive", "negative": "$stats.negative"}},
    ]
    return [_serialize(d) for d in db.games.aggregate(pipeline)]


def self_published_studios(limit=10):
    pipeline = [
        {"$match": {"$expr": {"$gt": [{"$size": {"$setIntersection": ["$developer_ids", "$publisher_ids"]}}, 0]}}},
        {"$unwind": "$developer_ids"},
        {"$group": {"_id": "$developer_ids", "self_published_game_count": {"$sum": 1}}},
        {"$sort": {"self_published_game_count": -1}},
        {"$limit": limit},
        {"$lookup": {"from": "companies", "localField": "_id", "foreignField": "_id", "as": "company"}},
        {"$unwind": "$company"},
        {"$project": {"_id": 0, "studio": "$company.name", "self_published_game_count": 1}},
    ]
    return [_serialize(d) for d in db.games.aggregate(pipeline)]
