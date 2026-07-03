"""
Interface Streamlit consommant l'API FastAPI (api.py) pour afficher les 13
requetes metier du catalogue Steam (tableaux + graphiques).

Lancer avec : streamlit run app_streamlit.py
Necessite l'API demarree au prealable : uvicorn api:app --port 8000
"""
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

API_BASE = "http://127.0.0.1:8000"

# Palette (voir skill dataviz / references/palette.md)
CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]
SEQUENTIAL_BLUE = "#2a78d6"
CHART_SURFACE = "#fcfcfb"
GRIDLINE = "#e1e0d9"
MUTED_INK = "#898781"
PRIMARY_INK = "#0b0b0b"

st.set_page_config(page_title="Steam Catalog - Dashboard NoSQL", layout="wide")


def base_layout(fig, title):
    fig.update_layout(
        title=title,
        plot_bgcolor=CHART_SURFACE,
        paper_bgcolor=CHART_SURFACE,
        font=dict(color=PRIMARY_INK, family="system-ui, -apple-system, Segoe UI, sans-serif"),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    fig.update_xaxes(gridcolor=GRIDLINE, linecolor=MUTED_INK)
    fig.update_yaxes(gridcolor=GRIDLINE, linecolor=MUTED_INK)
    return fig


@st.cache_data(ttl=60)
def get_json(endpoint, params=None):
    r = requests.get(f"{API_BASE}{endpoint}", params=params or {}, timeout=15)
    r.raise_for_status()
    return r.json()


st.title("Catalogue de jeux Steam - Dashboard NoSQL (MongoDB)")
st.caption("Donnees reelles issues de games.csv (125 855 jeux), servies par une API FastAPI connectee a MongoDB.")

# Tuiles de synthese
try:
    stats = get_json("/api/stats")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Jeux", f"{stats['games']:,}".replace(",", " "))
    c2.metric("Developpeurs/Editeurs", f"{stats['companies']:,}".replace(",", " "))
    c3.metric("Genres", stats["genres"])
    c4.metric("Categories", stats["categories"])
    c5.metric("Tags", stats["tags"])
except requests.exceptions.ConnectionError:
    st.error("Impossible de contacter l'API sur http://127.0.0.1:8000. Demarrez-la avec : uvicorn api:app --port 8000")
    st.stop()

st.divider()

QUESTIONS = {
    "Q1. Genres dominants et prix moyen": "q1",
    "Q2. Developpeurs les plus prolifiques": "q2",
    "Q3. Repartition par tranche de prix": "q3",
    "Q4. Meilleur jeu par genre (ratio d'avis positifs)": "q4",
    "Q5. Sorties de jeux par annee": "q5",
    "Q6. Support Mac/Linux par genre": "q6",
    "Q7. Combinaisons de categories frequentes": "q7",
    "Q8. Tags au meilleur ratio d'avis positifs": "q8",
    "Q9. Langues supportees": "q9",
    "Q10. Editeurs les plus rentables (recommandations)": "q10",
    "Q11. Impact du nombre de DLC": "q11",
    "Q12. Top Free To Play": "q12",
    "Q13. Studios auto-edites": "q13",
}

choice = st.sidebar.radio("Besoin utilisateur", list(QUESTIONS.keys()))
qid = QUESTIONS[choice]
st.header(choice)

if qid == "q1":
    limit = st.slider("Nombre de genres", 5, 20, 10)
    data = get_json("/api/genres/top", {"limit": limit})
    df = pd.DataFrame(data).rename(columns={"_id": "genre"})
    st.dataframe(df, use_container_width=True)
    fig = px.bar(df.sort_values("game_count"), x="game_count", y="genre", orientation="h",
                 color_discrete_sequence=[SEQUENTIAL_BLUE])
    st.plotly_chart(base_layout(fig, "Nombre de jeux par genre"), use_container_width=True)
    fig2 = px.bar(df.sort_values("avg_price"), x="avg_price", y="genre", orientation="h",
                  color_discrete_sequence=["#1baf7a"])
    st.plotly_chart(base_layout(fig2, "Prix moyen par genre (EUR)"), use_container_width=True)

elif qid == "q2":
    limit = st.slider("Nombre de developpeurs", 5, 20, 10)
    data = get_json("/api/developers/top", {"limit": limit})
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
    fig = px.bar(df.sort_values("game_count"), x="game_count", y="developer", orientation="h",
                 color_discrete_sequence=[SEQUENTIAL_BLUE])
    st.plotly_chart(base_layout(fig, "Nombre de jeux par developpeur"), use_container_width=True)

elif qid == "q3":
    data = get_json("/api/price-distribution")
    df = pd.DataFrame(data)
    df["tranche"] = df["_id"].astype(str)
    st.dataframe(df, use_container_width=True)
    fig = px.bar(df, x="tranche", y="game_count", color_discrete_sequence=[SEQUENTIAL_BLUE])
    st.plotly_chart(base_layout(fig, "Nombre de jeux par tranche de prix"), use_container_width=True)
    fig2 = px.bar(df, x="tranche", y="avg_recommendations", color_discrete_sequence=["#1baf7a"])
    st.plotly_chart(base_layout(fig2, "Recommandations moyennes par tranche de prix"), use_container_width=True)

elif qid == "q4":
    min_reviews = st.slider("Seuil minimum d'avis", 10, 500, 100)
    data = get_json("/api/genres/best-game", {"min_reviews": min_reviews, "limit": 15})
    df = pd.DataFrame(data).rename(columns={"_id": "genre"})
    st.dataframe(df, use_container_width=True)
    fig = px.bar(df.sort_values("total_reviews"), x="total_reviews", y="genre", orientation="h",
                 hover_data=["best_game", "positive_ratio"], color_discrete_sequence=[SEQUENTIAL_BLUE])
    st.plotly_chart(base_layout(fig, "Nombre d'avis du jeu le mieux note par genre"), use_container_width=True)

elif qid == "q5":
    data = get_json("/api/releases/by-year")
    df = pd.DataFrame(data).rename(columns={"_id": "annee"})
    df = df[(df["annee"] >= 2000) & (df["annee"] <= 2025)]
    st.dataframe(df, use_container_width=True)
    fig = px.line(df, x="annee", y="game_count", markers=True, color_discrete_sequence=[SEQUENTIAL_BLUE])
    st.plotly_chart(base_layout(fig, "Nombre de sorties de jeux par annee (2000-2025)"), use_container_width=True)

elif qid == "q6":
    min_games = st.slider("Nombre minimum de jeux par genre", 100, 5000, 500)
    data = get_json("/api/genres/platform-support", {"min_games": min_games})
    df = pd.DataFrame(data).rename(columns={"_id": "genre"})
    st.dataframe(df, use_container_width=True)
    long_df = df.melt(id_vars=["genre", "total"], value_vars=["pct_mac", "pct_linux"], var_name="plateforme", value_name="pourcentage")
    long_df["plateforme"] = long_df["plateforme"].map({"pct_mac": "Mac", "pct_linux": "Linux"})
    fig = px.bar(long_df, x="genre", y="pourcentage", color="plateforme", barmode="group",
                 color_discrete_sequence=CATEGORICAL)
    st.plotly_chart(base_layout(fig, "% de jeux supportant Mac / Linux par genre"), use_container_width=True)

elif qid == "q7":
    limit = st.slider("Nombre de combinaisons", 5, 20, 10)
    data = get_json("/api/categories/top-combos", {"limit": limit})
    df = pd.DataFrame(data)
    df["combo"] = df["_id"].apply(lambda d: f"{d['a']} + {d['b']}")
    df = df[["combo", "count"]]
    st.dataframe(df, use_container_width=True)
    fig = px.bar(df.sort_values("count"), x="count", y="combo", orientation="h",
                 color_discrete_sequence=[SEQUENTIAL_BLUE])
    st.plotly_chart(base_layout(fig, "Combinaisons de categories les plus frequentes"), use_container_width=True)

elif qid == "q8":
    min_games = st.slider("Nombre minimum de jeux par tag", 10, 200, 50)
    data = get_json("/api/tags/best-ratio", {"min_games": min_games, "limit": 15})
    df = pd.DataFrame(data).rename(columns={"_id": "tag"})
    df["avg_positive_ratio_pct"] = (df["avg_positive_ratio"] * 100).round(1)
    st.dataframe(df, use_container_width=True)
    fig = px.bar(df.sort_values("avg_positive_ratio_pct"), x="avg_positive_ratio_pct", y="tag", orientation="h",
                 color_discrete_sequence=["#1baf7a"])
    st.plotly_chart(base_layout(fig, "Ratio moyen d'avis positifs par tag (%)"), use_container_width=True)

elif qid == "q9":
    data = get_json("/api/languages/stats", {"top_n": 15})
    avg = data["moyenne_globale"][0]["avg_nb_langues"] if data.get("moyenne_globale") else 0
    st.metric("Nombre moyen de langues supportees par jeu", f"{avg:.2f}")
    df = pd.DataFrame(data["top_multilingues"])
    st.dataframe(df, use_container_width=True)
    fig = px.bar(df.sort_values("nb_langues"), x="nb_langues", y="name", orientation="h",
                 color_discrete_sequence=[SEQUENTIAL_BLUE])
    st.plotly_chart(base_layout(fig, "Jeux les plus multilingues"), use_container_width=True)

elif qid == "q10":
    min_games = st.slider("Nombre minimum de jeux par editeur", 1, 30, 5)
    data = get_json("/api/publishers/top", {"min_games": min_games, "limit": 10})
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
    fig = px.bar(df.sort_values("avg_recommendations"), x="avg_recommendations", y="publisher", orientation="h",
                 color_discrete_sequence=[SEQUENTIAL_BLUE])
    st.plotly_chart(base_layout(fig, "Recommandations moyennes par editeur"), use_container_width=True)

elif qid == "q11":
    data = get_json("/api/dlc/impact")
    df = pd.DataFrame(data)
    df["tranche_dlc"] = df["_id"].astype(str)
    df["avg_positive_ratio_pct"] = (df["avg_positive_ratio"] * 100).round(1)
    st.dataframe(df, use_container_width=True)
    fig = px.bar(df, x="tranche_dlc", y="avg_recommendations", color_discrete_sequence=[SEQUENTIAL_BLUE])
    st.plotly_chart(base_layout(fig, "Recommandations moyennes par nombre de DLC"), use_container_width=True)
    fig2 = px.bar(df, x="tranche_dlc", y="avg_positive_ratio_pct", color_discrete_sequence=["#1baf7a"])
    st.plotly_chart(base_layout(fig2, "Ratio d'avis positifs moyen par nombre de DLC (%)"), use_container_width=True)

elif qid == "q12":
    limit = st.slider("Nombre de jeux", 5, 20, 10)
    data = get_json("/api/games/free-to-play/top", {"limit": limit})
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
    fig = px.bar(df.sort_values("recommendations"), x="recommendations", y="name", orientation="h",
                 color_discrete_sequence=[SEQUENTIAL_BLUE])
    st.plotly_chart(base_layout(fig, "Jeux Free To Play les plus recommandes"), use_container_width=True)

elif qid == "q13":
    limit = st.slider("Nombre de studios", 5, 20, 10)
    data = get_json("/api/studios/self-published", {"limit": limit})
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
    fig = px.bar(df.sort_values("self_published_game_count"), x="self_published_game_count", y="studio", orientation="h",
                 color_discrete_sequence=[SEQUENTIAL_BLUE])
    st.plotly_chart(base_layout(fig, "Nombre de jeux auto-edites par studio"), use_container_width=True)
