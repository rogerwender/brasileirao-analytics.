
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------
# CONFIGURAÇÃO VISUAL
# --------------------------------------------------
st.set_page_config(
    page_title="Brasileirão Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

FUNDO = "#0B1220"
PAINEL = "#151F32"
VERDE = "#00D4A0"
AZUL = "#60A5FA"
AMARELO = "#FBBF24"
VERMELHO = "#FB7185"
TEXTO = "#F1F5F9"
CINZA = "#94A3B8"

st.markdown(f"""
<style>
    .stApp {{
        background-color: {FUNDO};
        color: {TEXTO};
    }}
    [data-testid="stSidebar"] {{
        background-color: {PAINEL};
    }}
    h1, h2, h3 {{
        color: {TEXTO} !important;
    }}
    div[data-testid="stMetric"] {{
        background-color: {PAINEL};
        border: 1px solid #26354D;
        padding: 18px;
        border-radius: 12px;
    }}
    div[data-testid="stMetricLabel"] {{
        color: {CINZA};
    }}
    div[data-testid="stMetricValue"] {{
        color: {VERDE};
    }}
    .subtitulo {{
        color: {CINZA};
        font-size: 14px;
    }}
    .secao {{
        border-left: 4px solid {VERDE};
        padding-left: 12px;
        margin-top: 20px;
    }}
</style>
""", unsafe_allow_html=True)

# Tema consistente para todos os gráficos
TEMA = dict(
    paper_bgcolor=PAINEL,
    plot_bgcolor=PAINEL,
    font=dict(color=TEXTO, family="Arial"),
    margin=dict(l=20, r=20, t=55, b=30),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXTO)
    ),
)

st.title("⚽ BRASILEIRÃO ANALYTICS")
st.markdown(
    '<p class="subtitulo">'
    'Dados, desempenho e histórias do Campeonato Brasileiro Série A'
    '</p>',
    unsafe_allow_html=True
)

# --------------------------------------------------
# CONEXÃO COM A API
# --------------------------------------------------
token = st.secrets.get("FOOTBALL_DATA_TOKEN", "")

if not token:
    st.warning(
        "Configure FOOTBALL_DATA_TOKEN nos Secrets do Streamlit."
    )
    st.stop()


@st.cache_data(ttl=1800, show_spinner=False)
def carregar_partidas(temporada, token_api):
    url = (
        "https://api.football-data.org/v4/"
        "competitions/BSA/matches"
    )

    resposta = requests.get(
        url,
        headers={"X-Auth-Token": token_api},
        params={"season": temporada},
        timeout=30,
    )
    resposta.raise_for_status()

    dados = resposta.json()
    partidas = []

    for jogo in dados.get("matches", []):
        placar = jogo.get("score", {}).get("fullTime", {})

        partidas.append({
            "ID": jogo.get("id"),
            "Rodada": jogo.get("matchday"),
            "Data": jogo.get("utcDate"),
            "Mandante": jogo.get("homeTeam", {}).get("name"),
            "Visitante": jogo.get("awayTeam", {}).get("name"),
            "Gols mandante": placar.get("home"),
            "Gols visitante": placar.get("away"),
            "Status": jogo.get("status"),
        })

    df = pd.DataFrame(partidas)

    if df.empty:
        return df

    df["Data"] = pd.to_datetime(df["Data"], utc=True).dt.tz_convert(
        "America/Sao_Paulo"
    ).dt.tz_localize(None)

    df["Rodada"] = pd.to_numeric(df["Rodada"], errors="coerce")
    df["Gols mandante"] = pd.to_numeric(
        df["Gols mandante"], errors="coerce"
    )
    df["Gols visitante"] = pd.to_numeric(
        df["Gols visitante"], errors="coerce"
    )

    return df


# --------------------------------------------------
# FILTROS GERAIS
# --------------------------------------------------
with st.sidebar:
    st.title("🎛️ Filtros")
    st.caption("Explore diferentes recortes do campeonato.")

    temporada = st.selectbox(
        "Temporada",
        [2026, 2025, 2024],
        index=0,
    )

try:
    with st.spinner("Buscando partidas na API..."):
        df = carregar_partidas(temporada, token)

except requests.HTTPError as erro:
    codigo = erro.response.status_code

    if codigo == 403:
        st.error(
            "Acesso negado pela API. Confira o token e as "
            "permissões da sua conta."
        )
    elif codigo == 429:
        st.error("Limite de chamadas atingido. Tente novamente mais tarde.")
    else:
        st.error(f"Erro HTTP {codigo}: {erro}")
    st.stop()

except requests.RequestException as erro:
    st.error(f"Falha na conexão: {erro}")
    st.stop()

if df.empty:
    st.info("Nenhuma partida foi retornada para essa temporada.")
    st.stop()

clubes = sorted(
    set(df["Mandante"].dropna()) |
    set(df["Visitante"].dropna())
)

with st.sidebar:
    mandantes = st.multiselect(
        "Time mandante",
        clubes,
        placeholder="Todos os mandantes",
    )

    visitantes = st.multiselect(
        "Time visitante",
        clubes,
        placeholder="Todos os visitantes",
    )

    rodadas = sorted(df["Rodada"].dropna().astype(int).unique())

    rodadas_escolhidas = st.multiselect(
        "Rodadas",
        rodadas,
        default=rodadas,
        placeholder="Todas as rodadas",
    )

    situacoes = sorted(df["Status"].dropna().unique())

    status_escolhidos = st.multiselect(
        "Situação da partida",
        situacoes,
        default=["FINISHED"] if "FINISHED" in situacoes else situacoes,
        format_func=lambda x: {
            "FINISHED": "Finalizada",
            "IN_PLAY": "Em andamento",
            "PAUSED": "Intervalo",
            "SCHEDULED": "Agendada",
            "TIMED": "Com horário definido",
            "POSTPONED": "Adiada",
            "SUSPENDED": "Suspensa",
            "CANCELLED": "Cancelada",
            "AWARDED": "Resultado atribuído",
        }.get(x, x),
    )

    if st.button("🔄 Atualizar dados da API", use_container_width=True):
        carregar_partidas.clear()
        st.rerun()

# --------------------------------------------------
# APLICAÇÃO DOS FILTROS
# --------------------------------------------------
filtrado = df.copy()

if mandantes:
    filtrado = filtrado[filtrado["Mandante"].isin(mandantes)]

if visitantes:
    filtrado = filtrado[filtrado["Visitante"].isin(visitantes)]

if rodadas_escolhidas:
    filtrado = filtrado[
        filtrado["Rodada"].isin(rodadas_escolhidas)
    ]
else:
    filtrado = filtrado.iloc[0:0]

if status_escolhidos:
    filtrado = filtrado[filtrado["Status"].isin(status_escolhidos)]
else:
    filtrado = filtrado.iloc[0:0]

# Jogos com placar válido e finalizado são usados nas estatísticas.
jogos = filtrado[
    (filtrado["Status"] == "FINISHED")
    & filtrado["Gols mandante"].notna()
    & filtrado["Gols visitante"].notna()
].copy()

jogos["Gols mandante"] = jogos["Gols mandante"].astype(int)
jogos["Gols visitante"] = jogos["Gols visitante"].astype(int)
jogos["Total gols"] = jogos["Gols mandante"] + jogos["Gols visitante"]

jogos["Resultado"] = "Empate"
jogos.loc[
    jogos["Gols mandante"] > jogos["Gols visitante"], "Resultado"
] = "Vitória do mandante"
jogos.loc[
    jogos["Gols mandante"] < jogos["Gols visitante"], "Resultado"
] = "Vitória do visitante"

# --------------------------------------------------
# INDICADORES
# --------------------------------------------------
st.markdown(
    '<div class="secao"><h3>📊 O campeonato em números</h3></div>',
    unsafe_allow_html=True
)

total_jogos = len(jogos)
total_gols = int(jogos["Total gols"].sum()) if total_jogos else 0
media_gols = total_gols / total_jogos if total_jogos else 0
vitorias_casa = (
    int((jogos["Resultado"] == "Vitória do mandante").sum())
    if total_jogos else 0
)
pct_casa = vitorias_casa / total_jogos * 100 if total_jogos else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Jogos finalizados", f"{total_jogos:,}".replace(",", "."))
c2.metric("Gols marcados", f"{total_gols:,}".replace(",", "."))
c3.metric("Média de gols/jogo", f"{media_gols:.2f}".replace(".", ","))
c4.metric("Vitórias dos mandantes", f"{pct_casa:.1f}%".replace(".", ","))

if total_jogos == 0:
    st.info(
        "Não há partidas finalizadas no recorte selecionado. "
        "Altere os filtros para visualizar as estatísticas."
    )

# --------------------------------------------------
# STORYTELLING: RESULTADOS E GOLS
# --------------------------------------------------
st.markdown(
    '<div class="secao"><h3>🎯 1. Quem está levando a melhor?</h3></div>',
    unsafe_allow_html=True
)

st.caption(
    "Compare o peso do mando de campo e a distribuição dos resultados "
    "nas partidas finalizadas do recorte."
)

if total_jogos:
    a, b = st.columns(2)

    ordem_resultados = [
        "Vitória do mandante",
        "Empate",
        "Vitória do visitante",
    ]

    cores_resultados = {
        "Vitória do mandante": VERDE,
        "Empate": AMARELO,
        "Vitória do visitante": AZUL,
    }

    contagem = (
        jogos["Resultado"]
        .value_counts()
        .reindex(ordem_resultados, fill_value=0)
        .rename_axis("Resultado")
        .reset_index(name="Partidas")
    )

    with a:
        fig = px.pie(
            contagem,
            names="Resultado",
            values="Partidas",
            hole=0.62,
            color="Resultado",
            color_discrete_map=cores_resultados,
            title="Distribuição dos resultados",
        )
        fig.update_traces(
            textposition="inside",
            textinfo="percent+value",
            marker=dict(line=dict(color=PAINEL, width=3)),
        )
        fig.update_layout(**TEMA)
        st.plotly_chart(fig, use_container_width=True)

    gols_local = jogos["Gols mandante"].sum()
    gols_visitante = jogos["Gols visitante"].sum()

    with b:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=["Mandantes", "Visitantes"],
            y=[gols_local, gols_visitante],
            marker_color=[VERDE, AZUL],
            text=[int(gols_local), int(gols_visitante)],
            textposition="outside",
            name="Gols",
        ))
        fig.update_layout(
            title="Quem marcou mais gols?",
            yaxis_title="Gols marcados",
            showlegend=False,
            **TEMA,
        )
        st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# STORYTELLING: EVOLUÇÃO POR RODADA
# --------------------------------------------------
st.markdown(
    '<div class="secao"><h3>📈 2. Como os gols evoluem por rodada?</h3></div>',
    unsafe_allow_html=True
)

st.caption(
    "A curva mostra a quantidade de gols nas partidas finalizadas "
    "de cada rodada, respeitando os filtros selecionados."
)

if total_jogos and jogos["Rodada"].notna().any():
    gols_rodada = (
        jogos.dropna(subset=["Rodada"])
        .groupby("Rodada", as_index=False)
        .agg(
            Gols=("Total gols", "sum"),
            Partidas=("ID", "count"),
        )
        .sort_values("Rodada")
    )

    gols_rodada["Média de gols"] = (
        gols_rodada["Gols"] / gols_rodada["Partidas"]
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=gols_rodada["Rodada"],
        y=gols_rodada["Gols"],
        name="Gols",
        marker_color=VERDE,
        opacity=0.85,
    ))
    fig.add_trace(go.Scatter(
        x=gols_rodada["Rodada"],
        y=gols_rodada["Média de gols"],
        name="Média de gols por jogo",
        yaxis="y2",
        mode="lines+markers",
        line=dict(color=AMARELO, width=3),
        marker=dict(size=7),
    ))
    fig.update_layout(
        title="Gols e média de gols por rodada",
        xaxis_title="Rodada",
        yaxis=dict(title="Total de gols"),
        yaxis2=dict(
            title="Média de gols por jogo",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        **TEMA,
    )
    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# STORYTELLING: RANKING OFENSIVO
# --------------------------------------------------
st.markdown(
    '<div class="secao"><h3>🔥 3. Quais clubes mais produzem gols?</h3></div>',
    unsafe_allow_html=True
)

st.caption(
    "O ranking soma os gols marcados como mandante e visitante "
    "nos jogos incluídos no recorte."
)

if total_jogos:
    gols_casa = jogos[["Mandante", "Gols mandante"]].rename(
        columns={"Mandante": "Clube", "Gols mandante": "Gols"}
    )
    gols_fora = jogos[["Visitante", "Gols visitante"]].rename(
        columns={"Visitante": "Clube", "Gols visitante": "Gols"}
    )

    ranking = pd.concat([gols_casa, gols_fora], ignore_index=True)
    ranking = (
        ranking.groupby("Clube", as_index=False)["Gols"]
        .sum()
        .sort_values("Gols", ascending=True)
    )

    fig = px.bar(
        ranking,
        x="Gols",
        y="Clube",
        orientation="h",
        text="Gols",
        color="Gols",
        color_continuous_scale=["#1E3A5F", VERDE],
        title="Ranking de gols marcados",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        coloraxis_showscale=False,
        xaxis_title="Gols",
        yaxis_title="",
        **TEMA,
    )
    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# TABELA DE PARTIDAS
# --------------------------------------------------
st.markdown(
    '<div class="secao"><h3>📋 4. Explore os jogos</h3></div>',
    unsafe_allow_html=True
)

busca = st.text_input(
    "Pesquisar clube",
    placeholder="Digite parte do nome do mandante ou visitante...",
)

tabela = filtrado.copy()

if busca.strip():
    mascara = (
        tabela["Mandante"].str.contains(busca, case=False, na=False)
        | tabela["Visitante"].str.contains(busca, case=False, na=False)
    )
    tabela = tabela[mascara]

tabela["Data"] = tabela["Data"].dt.strftime("%d/%m/%Y %H:%M")

tabela = tabela.rename(columns={
    "Gols mandante": "Gols casa",
    "Gols visitante": "Gols fora",
})

tabela = tabela[
    [
        "Data", "Rodada", "Mandante", "Gols casa",
        "Gols fora", "Visitante", "Status"
    ]
].sort_values(["Rodada", "Data"], na_position="last")

st.dataframe(
    tabela,
    use_container_width=True,
    hide_index=True,
    height=450,
)

csv = tabela.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "⬇️ Baixar jogos filtrados em CSV",
    data=csv,
    file_name=f"brasileirao_{temporada}_jogos.csv",
    mime="text/csv",
)

st.markdown("---")
st.caption(
    "Fonte: football-data.org · Projeto de portfólio de análise de dados. "
    "Os indicadores refletem os filtros aplicados e os jogos finalizados."
)
