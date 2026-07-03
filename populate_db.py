"""
Peuple la base MongoDB 'steam_catalog' a partir de games.csv, selon le schema
a 5 collections valide : games, companies, genres, categories, tags.

Notes sur le CSV source :
- Le header officiel a 39 noms de colonnes mais chaque ligne a 40 champs :
  "DiscountDLC count" est la fusion accidentelle de "Discount" et "DLC count".
  On corrige en fournissant explicitement les 40 noms de colonnes.
- "Supported languages" / "Full audio languages" sont au format repr Python
  ("['English', 'French']") -> parse avec ast.literal_eval.
- "Developers" / "Publishers" / "Categories" / "Genres" / "Tags" sont de simples
  chaines separees par des virgules. Pour Developers/Publishers, environ 1.1%
  des lignes contiennent une raison sociale avec virgule interne (ex: "Accolade, Inc.",
  "TAITO CORP.,M2 Co., Ltd."). Un split naif sur "," casse ces raisons sociales et
  fait apparaitre "Inc.", "LLC", "Ltd." comme de faux "developpeurs" a part entiere
  (constate lors des premieres requetes metier). On utilise donc un split par regex
  qui ne coupe pas une virgule immediatement suivie d'un suffixe juridique courant
  (Inc., LLC, Ltd., Co., Corp., GmbH, S.A., S.L., B.V., Oy, KG, plc). Heuristique
  best-effort, pas parfaite a 100%, mais elimine l'essentiel du bruit observe.
"""
import ast
import re
import sys
import io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="backslashreplace")

import pandas as pd
import numpy as np
from pymongo import MongoClient, ASCENDING
from pymongo.errors import BulkWriteError

CSV_PATH = r"c:\Users\firas\Documents\nosql projet\games.csv"
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "steam_catalog"

FIXED_COLUMNS = [
    "AppID", "Name", "Release date", "Estimated owners", "Peak CCU", "Required age",
    "Price", "Discount", "DLC count", "About the game", "Supported languages",
    "Full audio languages", "Reviews", "Header image", "Website", "Support url",
    "Support email", "Windows", "Mac", "Linux", "Metacritic score", "Metacritic url",
    "User score", "Positive", "Negative", "Score rank", "Achievements", "Recommendations",
    "Notes", "Average playtime forever", "Average playtime two weeks",
    "Median playtime forever", "Median playtime two weeks", "Developers", "Publishers",
    "Categories", "Genres", "Tags", "Screenshots", "Movies",
]


def split_simple(value):
    if pd.isna(value) or str(value).strip() == "":
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


LEGAL_SUFFIX_RE = re.compile(
    r",(?!\s*(?:Inc\.?|LLC|Ltd\.?|Co\.?|Corp\.?|GmbH|S\.A\.?|S\.L\.?|B\.V\.?|Oy|KG|plc)\b)",
    re.IGNORECASE,
)


def split_company_names(value):
    """Comme split_simple, mais ne coupe pas une virgule suivie d'un suffixe
    juridique (", Inc.", ", LLC", ", Ltd.", ...) afin de ne pas casser les
    raisons sociales composees. Voir note en tete de fichier."""
    if pd.isna(value) or str(value).strip() == "":
        return []
    return [item.strip() for item in LEGAL_SUFFIX_RE.split(str(value)) if item.strip()]


def split_pylist(value):
    if pd.isna(value) or str(value).strip() == "":
        return []
    try:
        items = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return []
    return [str(item).strip() for item in items if str(item).strip()]


def parse_release_date(value):
    if pd.isna(value):
        return None
    for fmt in ("%b %d, %Y", "%b %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value).strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def none_if_nan(value):
    if value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None
    return value


def build_game_doc(row, dev_ids_by_name, pub_ids_by_name):
    developers = split_company_names(row["Developers"])
    publishers = split_company_names(row["Publishers"])
    return {
        "_id": int(row["AppID"]),
        "name": none_if_nan(row["Name"]),
        "release_date": parse_release_date(row["Release date"]),
        "estimated_owners": none_if_nan(row["Estimated owners"]),
        "required_age": int(row["Required age"]),
        "pricing": {
            "price": float(row["Price"]),
            "discount": int(row["Discount"]),
            "dlc_count": int(row["DLC count"]),
        },
        "platforms": {
            "windows": bool(row["Windows"]),
            "mac": bool(row["Mac"]),
            "linux": bool(row["Linux"]),
        },
        "media": {
            "header_image": none_if_nan(row["Header image"]),
            "screenshots": split_simple(row["Screenshots"]),
            "movies": none_if_nan(row["Movies"]),
        },
        "links": {
            "website": none_if_nan(row["Website"]),
            "support_url": none_if_nan(row["Support url"]),
            "support_email": none_if_nan(row["Support email"]),
        },
        "languages": {
            "supported": split_pylist(row["Supported languages"]),
            "full_audio": split_pylist(row["Full audio languages"]),
        },
        "stats": {
            "metacritic_score": int(row["Metacritic score"]),
            "metacritic_url": none_if_nan(row["Metacritic url"]),
            "user_score": int(row["User score"]),
            "positive": int(row["Positive"]),
            "negative": int(row["Negative"]),
            "recommendations": int(row["Recommendations"]),
            "achievements": int(row["Achievements"]),
            "score_rank": none_if_nan(row["Score rank"]),
            "peak_ccu": int(row["Peak CCU"]),
            "playtime": {
                "avg_forever": int(row["Average playtime forever"]),
                "avg_2weeks": int(row["Average playtime two weeks"]),
                "median_forever": int(row["Median playtime forever"]),
                "median_2weeks": int(row["Median playtime two weeks"]),
            },
        },
        "about_the_game": none_if_nan(row["About the game"]),
        "reviews_quote": none_if_nan(row["Reviews"]),
        "notes": none_if_nan(row["Notes"]),
        "genres": split_simple(row["Genres"]),
        "categories": split_simple(row["Categories"]),
        "tags": split_simple(row["Tags"]),
        "developer_ids": [dev_ids_by_name[d] for d in developers if d in dev_ids_by_name],
        "publisher_ids": [pub_ids_by_name[p] for p in publishers if p in pub_ids_by_name],
    }


def main():
    print("=== Lecture du CSV ===")
    df = pd.read_csv(CSV_PATH, header=0, names=FIXED_COLUMNS, low_memory=False)
    print("Lignes chargees:", len(df))

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    print("=== Reinitialisation des collections ===")
    for coll in ["games", "companies", "genres", "categories", "tags"]:
        db[coll].drop()

    # Collection companies (developers + publishers fusionnes)
    print("=== Construction de la collection companies ===")
    dev_counter = {}
    pub_counter = {}
    for value in df["Developers"]:
        for name in split_company_names(value):
            dev_counter[name] = dev_counter.get(name, 0) + 1
    for value in df["Publishers"]:
        for name in split_company_names(value):
            pub_counter[name] = pub_counter.get(name, 0) + 1

    all_names = set(dev_counter) | set(pub_counter)
    companies_docs = []
    dev_ids_by_name = {}
    pub_ids_by_name = {}
    from bson import ObjectId
    for name in sorted(all_names):
        roles = []
        if name in dev_counter:
            roles.append("developer")
        if name in pub_counter:
            roles.append("publisher")
        oid = ObjectId()
        companies_docs.append({
            "_id": oid,
            "name": name,
            "roles": roles,
            "game_count_as_developer": dev_counter.get(name, 0),
            "game_count_as_publisher": pub_counter.get(name, 0),
        })
        if name in dev_counter:
            dev_ids_by_name[name] = oid
        if name in pub_counter:
            pub_ids_by_name[name] = oid

    if companies_docs:
        db.companies.insert_many(companies_docs)
    print("companies inserees:", len(companies_docs))

    # Collections genres / categories / tags (rollup)
    print("=== Construction des collections genres / categories / tags ===")
    for col_name, coll, doc_type in [
        ("Genres", db.genres, "genre"),
        ("Categories", db.categories, "category"),
        ("Tags", db.tags, "tag"),
    ]:
        counter = {}
        price_sum = {}
        metacritic_sum = {}
        metacritic_n = {}
        for value, price, metacritic in zip(df[col_name], df["Price"], df["Metacritic score"]):
            for item in split_simple(value):
                counter[item] = counter.get(item, 0) + 1
                price_sum[item] = price_sum.get(item, 0.0) + float(price)
                if metacritic and metacritic > 0:
                    metacritic_sum[item] = metacritic_sum.get(item, 0) + metacritic
                    metacritic_n[item] = metacritic_n.get(item, 0) + 1
        docs = []
        for item, count in sorted(counter.items()):
            docs.append({
                "_id": item,
                "type": doc_type,
                "game_count": count,
                "avg_price": round(price_sum[item] / count, 2),
                "avg_metacritic": round(metacritic_sum[item] / metacritic_n[item], 2) if item in metacritic_n else None,
            })
        if docs:
            coll.insert_many(docs)
        print(f"{col_name}: {len(docs)} documents inseres dans {coll.name}")

    # Collection games
    print("=== Construction et insertion de la collection games ===")
    batch = []
    inserted = 0
    for _, row in df.iterrows():
        batch.append(build_game_doc(row, dev_ids_by_name, pub_ids_by_name))
        if len(batch) >= 5000:
            db.games.insert_many(batch, ordered=False)
            inserted += len(batch)
            print(f"  ... {inserted} jeux inseres")
            batch = []
    if batch:
        db.games.insert_many(batch, ordered=False)
        inserted += len(batch)
    print("games inseres:", inserted)

    # Index utiles
    print("=== Creation des index ===")
    db.games.create_index([("genres", ASCENDING)])
    db.games.create_index([("categories", ASCENDING)])
    db.games.create_index([("tags", ASCENDING)])
    db.games.create_index([("developer_ids", ASCENDING)])
    db.games.create_index([("publisher_ids", ASCENDING)])
    db.games.create_index([("release_date", ASCENDING)])
    db.games.create_index([("name", ASCENDING)])
    db.companies.create_index([("name", ASCENDING)])

    print("\n=== Verification finale ===")
    print("games:", db.games.count_documents({}))
    print("companies:", db.companies.count_documents({}))
    print("genres:", db.genres.count_documents({}))
    print("categories:", db.categories.count_documents({}))
    print("tags:", db.tags.count_documents({}))


if __name__ == "__main__":
    main()
