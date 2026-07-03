import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

import pandas as pd
import numpy as np

path = r"c:\Users\firas\Documents\nosql projet\games.csv"

# Le header du CSV a 39 noms de colonnes mais chaque ligne de donnees a 40 champs :
# la colonne "DiscountDLC count" est en realite la fusion accidentelle de deux
# entetes ("Discount" et "DLC count"), la virgule ayant disparu. On corrige ici
# en fournissant explicitement la liste de 40 noms et en sautant la ligne de header d'origine.
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

print("=== Chargement (header corrige) ===")
df = pd.read_csv(path, header=0, names=fixed_columns, low_memory=False)
print("Shape:", df.shape)

print("\n=== Colonnes et dtypes ===")
print(df.dtypes)

print("\n=== Valeurs manquantes (count + %) ===")
na = df.isna().sum()
pct = (na / len(df) * 100).round(2)
missing = pd.DataFrame({"missing_count": na, "missing_pct": pct})
print(missing[missing["missing_count"] > 0].sort_values("missing_pct", ascending=False))

print("\n=== Doublons AppID ===")
print("AppID dupliques:", df["AppID"].duplicated().sum())
print("AppID unique count:", df["AppID"].nunique(), "/ total rows:", len(df))
print("AppID dtype:", df["AppID"].dtype)

print("\n=== Index du DataFrame (doit etre RangeIndex par defaut) ===")
print(type(df.index), df.index[:5].tolist())

print("\n=== Release date (corrige) sample ===")
print(df["Release date"].dropna().head(10).tolist())

print("\n=== Estimated owners (corrige) sample + value_counts ===")
print(df["Estimated owners"].dropna().head(10).tolist())
print(df["Estimated owners"].value_counts().head(15))

print("\n=== Discount / DLC count sample ===")
print(df[["Discount", "DLC count"]].describe())

print("\n=== Exemples bruts des colonnes 'listes' (format exact) ===")
list_cols = ["Supported languages", "Full audio languages", "Developers", "Publishers", "Categories", "Genres", "Tags"]
for col in list_cols:
    print(f"\n--- {col} (dtype={df[col].dtype}) ---")
    sample = df[col].dropna().head(3)
    for v in sample:
        print(repr(v)[:300])

print("\n=== Format des colonnes 'liste' : python-list-repr vs CSV simple ===")
for col in list_cols:
    non_null = df[col].dropna()
    starts_with_bracket = non_null.astype(str).str.startswith("[").mean()
    print(f"{col}: {starts_with_bracket*100:.1f}% des valeurs commencent par '['")

print("\n=== Types numeriques cles ===")
for col in ["Price", "Discount", "DLC count", "Metacritic score", "User score", "Positive", "Negative", "Recommendations", "Peak CCU", "Required age", "Achievements"]:
    print(col, df[col].dtype, "min:", df[col].min(), "max:", df[col].max())

print("\n=== Windows/Mac/Linux ===")
print(df[["Windows", "Mac", "Linux"]].dtypes)
print(df[["Windows", "Mac", "Linux"]].head(3))
print("Windows True count:", df["Windows"].sum(), "Mac True count:", df["Mac"].sum(), "Linux True count:", df["Linux"].sum())

print("\n=== Colonnes texte libre (longueur) ===")
for col in ["About the game", "Reviews", "Notes"]:
    lengths = df[col].dropna().astype(str).str.len()
    print(col, "count non-null:", lengths.count(), "avg len:", lengths.mean().round(1) if lengths.count() else None, "max len:", lengths.max() if lengths.count() else None)

print("\n=== Memory usage ===")
print(df.memory_usage(deep=True).sum() / 1e6, "MB")

print("\n=== Sauvegarde d'un echantillon corrige pour verification visuelle ===")
df.head(20).to_csv(r"c:\Users\firas\Documents\nosql projet\sample_corrected_20.csv", index=False)
print("OK -> sample_corrected_20.csv")
