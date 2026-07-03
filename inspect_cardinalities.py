import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

import pandas as pd
import ast
from collections import Counter

path = r"c:\Users\firas\Documents\nosql projet\games.csv"

fixed_columns = [
    "AppID", "Name", "Release date", "Estimated owners", "Peak CCU", "Required age",
    "Price", "Discount", "DLC count", "About the game", "Supported languages",
    "Full audio languages", "Reviews", "Header image", "Website", "Support url",
    "Support email", "Windows", "Mac", "Linux", "Metacritic score", "Metacritic url",
    "User score", "Positive", "Negative", "Score rank", "Achievements", "Recommendations",
    "Notes", "Average playtime forever", "Average playtime two weeks",
    "Median playtime forever", "Median playtime two weeks", "Developers", "Publishers",
    "Categories", "Genres", "Tags", "Screenshots", "Movies",
]

df = pd.read_csv(path, header=0, names=fixed_columns, low_memory=False)


def split_simple(series):
    c = Counter()
    for v in series.dropna():
        for item in str(v).split(","):
            item = item.strip()
            if item:
                c[item] += 1
    return c


def split_pylist(series):
    c = Counter()
    for v in series.dropna():
        try:
            items = ast.literal_eval(v)
        except (ValueError, SyntaxError):
            items = []
        for item in items:
            item = str(item).strip()
            if item:
                c[item] += 1
    return c


for col in ["Genres", "Categories", "Tags", "Developers", "Publishers"]:
    c = split_simple(df[col])
    print(f"\n=== {col}: {len(c)} valeurs distinctes ===")
    print("Top 10:", c.most_common(10))

for col in ["Supported languages", "Full audio languages"]:
    c = split_pylist(df[col])
    print(f"\n=== {col}: {len(c)} valeurs distinctes ===")
    print("Top 10:", c.most_common(10))

# Cardinalite developpeurs/editeurs partages (many-to-many check)
dev_counts = split_simple(df["Developers"])
pub_counts = split_simple(df["Publishers"])
dev_names = set(dev_counts.keys())
pub_names = set(pub_counts.keys())
both = dev_names & pub_names
print(f"\nDevelopers uniques: {len(dev_names)}, Publishers uniques: {len(pub_names)}, communs (dev ET pub): {len(both)}")

# Combien de jeux ont plusieurs developpeurs / editeurs
multi_dev = df["Developers"].dropna().apply(lambda v: len(str(v).split(",")) > 1).sum()
multi_pub = df["Publishers"].dropna().apply(lambda v: len(str(v).split(",")) > 1).sum()
print(f"Jeux avec >1 developpeur: {multi_dev}, avec >1 editeur: {multi_pub}")

# Top developers par nombre de jeux (fan-out)
print("\nTop 10 developpeurs par nombre de jeux:", dev_counts.most_common(10))
print("Top 10 editeurs par nombre de jeux:", pub_counts.most_common(10))
