
import requests
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Brasileirão Analytics",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Brasileirão Analytics")
st.write("Meu primeiro aplicativo conectado a uma API de futebol.")

# O token fica nos Secrets do Streamlit, não no código público.
token = st.secrets.get("FOOTBALL_DATA_TOKEN", "")

if not token:
    st.warning(
        "Configure o token da API nos Secrets do Streamlit "
        "para carregar os jogos."
    )
    st.stop()


@st.cache_data(ttl=1800)
def carregar_partidas(temporada, token_api):
    url = (
        "https://api.football-data.org/v4/"
        "competitions/BSA/matches"
    )

    headers = {"X-Auth-Token": token_api}
    params = {"season": temporada}

    resposta = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    resposta.raise_for_status()
    dados = resposta.json()

    partidas = []

    for jogo in dados.get("matches", []):
        placar = jogo.get("score", {}).get("fullTime", {})

        partidas.append({
            "Rodada": jogo.get("matchday"),
            "Data": jogo.get("utcDate"),
            "Mandante": jogo.get("homeTeam", {}).get("name"),
            "Visitante": jogo.get("awayTeam", {}).get("name"),
            "Gols mandante": placar.get("home"),
            "Gols visitante": placar.get("away"),
            "Status": jogo.get("status")
        })

    return pd.DataFrame(partidas)


temporada = st.selectbox(
    "Selecione a temporada",
    [2026, 2025, 2024],
    index=0
)

try:
    df = carregar_partidas(temporada, token)

    if df.empty:
        st.info("A API não retornou partidas para essa temporada.")
    else:
        finalizadas = df[df["Status"] == "FINISHED"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Partidas retornadas", len(df))
        col2.metric("Partidas finalizadas", len(finalizadas))
        col3.metric("Temporada", temporada)

        st.subheader("Jogos do Brasileirão")
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.caption(
            "Fonte: football-data.org | "
            "Cache de 30 minutos."
        )

except requests.HTTPError as erro:
    codigo = erro.response.status_code

    if codigo == 403:
        st.error(
            "A API recusou o acesso. Verifique se sua conta "
            "tem permissão para consultar essa competição."
        )
    elif codigo == 429:
        st.error(
            "Limite de chamadas atingido. Aguarde antes de tentar novamente."
        )
    else:
        st.error(f"Erro HTTP {codigo}: {erro}")

except requests.RequestException as erro:
    st.error(f"Falha na conexão com a API: {erro}")

except Exception as erro:
    st.error(f"Erro ao carregar os dados: {erro}")
