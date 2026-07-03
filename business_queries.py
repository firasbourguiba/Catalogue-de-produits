"""
13 besoins utilisateurs (questions metier) et leurs requetes d'agregation MongoDB
associees, executees reellement sur la base 'steam_catalog' peuplee par populate_db.py.
"""
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="backslashreplace")

import json
from bson import ObjectId
from pymongo import MongoClient

# Surchargeable via la variable d'environnement MONGO_URI (utile si la base
# ne tourne pas en local par defaut, ex: MongoDB Atlas ou un autre hote).
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)
db = client["steam_catalog"]


def show(title, pipeline_desc, cursor, limit_print=10):
    print("\n" + "=" * 100)
    print(title)
    print("-" * 100)
    print(pipeline_desc)
    print("-" * 100)
    results = list(cursor)
    for doc in results[:limit_print]:
        doc = {k: (str(v) if isinstance(v, ObjectId) else v) for k, v in doc.items()}
        print(json.dumps(doc, ensure_ascii=False, default=str))
    print(f"(total resultats retournes: {len(results)})")
    return results


# Q1
q1_pipeline = [
    {"$unwind": "$genres"},
    {"$group": {"_id": "$genres", "game_count": {"$sum": 1}, "avg_price": {"$avg": "$pricing.price"}}},
    {"$sort": {"game_count": -1}},
    {"$limit": 10},
]
show(
    "Q1. Quels sont les 10 genres les plus representes dans le catalogue, et leur prix moyen ?",
    "db.games.aggregate([$unwind genres, $group count+avg_price, $sort, $limit])",
    db.games.aggregate(q1_pipeline),
)

# Q2
q2_pipeline = [
    {"$unwind": "$developer_ids"},
    {"$group": {
        "_id": "$developer_ids",
        "game_count": {"$sum": 1},
        "avg_metacritic": {"$avg": {"$cond": [{"$gt": ["$stats.metacritic_score", 0]}, "$stats.metacritic_score", None]}},
    }},
    {"$sort": {"game_count": -1}},
    {"$limit": 10},
    {"$lookup": {"from": "companies", "localField": "_id", "foreignField": "_id", "as": "company"}},
    {"$unwind": "$company"},
    {"$project": {"_id": 0, "developer": "$company.name", "game_count": 1, "avg_metacritic": {"$round": ["$avg_metacritic", 1]}}},
]
show(
    "Q2. Quels sont les 10 developpeurs les plus prolifiques, et leur note metacritic moyenne ?",
    "db.games.aggregate([$unwind developer_ids, $group, $sort, $limit, $lookup companies, $project])",
    db.games.aggregate(q2_pipeline),
)

# Q3
q3_pipeline = [
    {"$bucket": {
        "groupBy": "$pricing.price",
        "boundaries": [0, 0.01, 5, 10, 20, 30, 60, 1000],
        "default": "autre",
        "output": {"game_count": {"$sum": 1}, "avg_recommendations": {"$avg": "$stats.recommendations"}},
    }},
]
show(
    "Q3. Comment se repartissent les jeux par tranche de prix (gratuit / <5 / 5-10 / 10-20 / 20-30 / 30-60 / 60+) ?",
    "db.games.aggregate([$bucket sur pricing.price])",
    db.games.aggregate(q3_pipeline),
)

# Q4
q4_pipeline = [
    {"$unwind": "$genres"},
    {"$match": {"$expr": {"$gte": [{"$add": ["$stats.positive", "$stats.negative"]}, 100]}}},
    {"$addFields": {"positive_ratio": {"$divide": ["$stats.positive", {"$add": ["$stats.positive", "$stats.negative"]}]}}},
    {"$sort": {"genres": 1, "positive_ratio": -1}},
    {"$group": {"_id": "$genres", "best_game": {"$first": "$name"}, "positive_ratio": {"$first": "$positive_ratio"}, "total_reviews": {"$first": {"$add": ["$stats.positive", "$stats.negative"]}}}},
    {"$sort": {"positive_ratio": -1}},
    {"$limit": 10},
]
show(
    "Q4. Pour chaque genre (avec >=100 avis), quel est le jeu le mieux note par la communaute (ratio avis positifs) ?",
    "db.games.aggregate([$unwind genres, $match seuil avis, $addFields ratio, $sort, $group $first, $sort, $limit])",
    db.games.aggregate(q4_pipeline),
)

# Q5
q5_pipeline = [
    {"$match": {"release_date": {"$ne": None}}},
    {"$group": {"_id": {"$year": "$release_date"}, "game_count": {"$sum": 1}}},
    {"$sort": {"_id": 1}},
]
show(
    "Q5. Comment evolue le nombre de sorties de jeux par annee ?",
    "db.games.aggregate([$match date non nulle, $group $year, $sort])",
    db.games.aggregate(q5_pipeline),
    limit_print=40,
)

# Q6
q6_pipeline = [
    {"$unwind": "$genres"},
    {"$group": {
        "_id": "$genres",
        "total": {"$sum": 1},
        "windows": {"$sum": {"$cond": ["$platforms.windows", 1, 0]}},
        "mac": {"$sum": {"$cond": ["$platforms.mac", 1, 0]}},
        "linux": {"$sum": {"$cond": ["$platforms.linux", 1, 0]}},
    }},
    {"$match": {"total": {"$gte": 500}}},
    {"$project": {
        "total": 1,
        "pct_mac": {"$round": [{"$multiply": [{"$divide": ["$mac", "$total"]}, 100]}, 1]},
        "pct_linux": {"$round": [{"$multiply": [{"$divide": ["$linux", "$total"]}, 100]}, 1]},
    }},
    {"$sort": {"pct_linux": -1}},
]
show(
    "Q6. Pour les genres majeurs (>=500 jeux), quel pourcentage de jeux supporte Mac / Linux ?",
    "db.games.aggregate([$unwind genres, $group sum booleans, $match seuil, $project pct, $sort])",
    db.games.aggregate(q6_pipeline),
    limit_print=15,
)

# Q7
q7_pipeline = [
    {"$match": {"categories.1": {"$exists": True}}},
    {"$project": {"categories": 1, "categories_copy": "$categories"}},
    {"$unwind": "$categories"},
    {"$unwind": "$categories_copy"},
    {"$match": {"$expr": {"$lt": ["$categories", "$categories_copy"]}}},
    {"$group": {"_id": {"a": "$categories", "b": "$categories_copy"}, "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
    {"$limit": 10},
]
show(
    "Q7. Quelles sont les 10 combinaisons de 2 categories (fonctionnalites) les plus frequentes ensemble ?",
    "db.games.aggregate([$match >=2 categories, $project categories+copie, $unwind x2 (produit cartesien intra-doc), $match a<b, $group count, $sort, $limit])",
    db.games.aggregate(q7_pipeline),
)

# Q8
# Note : "User score" est un champ quasi abandonne par Steam (renseigne sur
# seulement 0.03% des jeux, 40/125855 - verifie en base). On utilise donc a la
# place le ratio d'avis positifs (positive / (positive+negative)), bien mieux
# renseigne, comme indicateur de satisfaction par tag.
q8_pipeline = [
    {"$unwind": "$tags"},
    {"$match": {"$expr": {"$gte": [{"$add": ["$stats.positive", "$stats.negative"]}, 20]}}},
    {"$addFields": {"positive_ratio": {"$divide": ["$stats.positive", {"$add": ["$stats.positive", "$stats.negative"]}]}}},
    {"$group": {"_id": "$tags", "avg_positive_ratio": {"$avg": "$positive_ratio"}, "game_count": {"$sum": 1}}},
    {"$match": {"game_count": {"$gte": 50}}},
    {"$sort": {"avg_positive_ratio": -1}},
    {"$limit": 10},
]
show(
    "Q8. Parmi les tags avec au moins 50 jeux notes (>=20 avis), lesquels ont le meilleur ratio d'avis positifs moyen ?",
    "db.games.aggregate([$unwind tags, $match seuil avis, $addFields ratio, $group avg, $match seuil jeux, $sort, $limit])",
    db.games.aggregate(q8_pipeline),
)

# Q9
q9_pipeline = [
    {"$facet": {
        "moyenne_globale": [
            {"$project": {"nb_langues": {"$size": "$languages.supported"}}},
            {"$group": {"_id": None, "avg_nb_langues": {"$avg": "$nb_langues"}}},
        ],
        "top_10_multilingues": [
            {"$project": {"name": 1, "nb_langues": {"$size": "$languages.supported"}}},
            {"$sort": {"nb_langues": -1}},
            {"$limit": 10},
        ],
    }},
]
show(
    "Q9. Quel est le nombre moyen de langues supportees par jeu, et quels jeux en supportent le plus ?",
    "db.games.aggregate([$facet: moyenne globale + top 10 jeux multilingues])",
    db.games.aggregate(q9_pipeline),
    limit_print=2,
)

# Q10
q10_pipeline = [
    {"$unwind": "$publisher_ids"},
    {"$group": {"_id": "$publisher_ids", "game_count": {"$sum": 1}, "avg_recommendations": {"$avg": "$stats.recommendations"}}},
    {"$match": {"game_count": {"$gte": 5}}},
    {"$sort": {"avg_recommendations": -1}},
    {"$limit": 10},
    {"$lookup": {"from": "companies", "localField": "_id", "foreignField": "_id", "as": "company"}},
    {"$unwind": "$company"},
    {"$project": {"_id": 0, "publisher": "$company.name", "game_count": 1, "avg_recommendations": {"$round": ["$avg_recommendations", 0]}}},
]
show(
    "Q10. Quels editeurs (>=5 jeux) ont la meilleure moyenne de recommandations par jeu ?",
    "db.games.aggregate([$unwind publisher_ids, $group, $match seuil, $sort, $limit, $lookup companies])",
    db.games.aggregate(q10_pipeline),
)

# Q11
q11_pipeline = [
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
show(
    "Q11. Le nombre de DLC est-il lie au succes d'un jeu (recommandations, ratio d'avis positifs) ?",
    "db.games.aggregate([$bucket sur pricing.dlc_count (0 / 1-3 / 4-10 / 11+)])",
    db.games.aggregate(q11_pipeline),
)

# Q12
q12_pipeline = [
    {"$match": {"pricing.price": 0, "genres": "Free To Play"}},
    {"$sort": {"stats.recommendations": -1}},
    {"$limit": 10},
    {"$project": {"_id": 0, "name": 1, "recommendations": "$stats.recommendations", "positive": "$stats.positive", "negative": "$stats.negative"}},
]
show(
    "Q12. Quels sont les 10 jeux Free To Play les plus recommandes (a mettre en avant sur la page d'accueil) ?",
    "db.games.aggregate([$match price=0 et genre Free To Play, $sort, $limit, $project])",
    db.games.aggregate(q12_pipeline),
)

# Q13
q13_pipeline = [
    {"$match": {"$expr": {"$gt": [{"$size": {"$setIntersection": ["$developer_ids", "$publisher_ids"]}}, 0]}}},
    {"$unwind": "$developer_ids"},
    {"$group": {"_id": "$developer_ids", "self_published_game_count": {"$sum": 1}}},
    {"$sort": {"self_published_game_count": -1}},
    {"$limit": 10},
    {"$lookup": {"from": "companies", "localField": "_id", "foreignField": "_id", "as": "company"}},
    {"$unwind": "$company"},
    {"$project": {"_id": 0, "studio": "$company.name", "self_published_game_count": 1}},
]
show(
    "Q13. Quels studios s'auto-editent le plus (developpeur = editeur), et combien de jeux cela represente ?",
    "db.games.aggregate([$match setIntersection dev/pub, $unwind, $group, $sort, $limit, $lookup companies])",
    db.games.aggregate(q13_pipeline),
)

print("\n\n=== TERMINE ===")
