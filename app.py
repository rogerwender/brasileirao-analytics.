
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==================================================
# CONFIGURAÇÃO
# ==================================================
st.set_page_config(
    page_title="Brasileirão Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

BG = "#0B1220"
PANEL = "#151F32"
BORDER = "#26354D"
WHITE = "#FFFFFF"
GREEN = "#00D4A0"
BLUE = "#60A5FA"
YELLOW = "#FBBF24"
RED = "#FB7185"
MUTED = "#B8C4D6"

st.markdown(f"""
<style>
    .stApp {{
        background-color: {BG};
        color: {WHITE};
    }}

    [data-testid="stSidebar"] {{
        background-color: {PANEL};
        border-right: 1px solid {BORDER};
    }}

    h1, h2, h3, h4,
    [data-testid="stHeader"],
    [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"] {{
        color: {WHITE} !important;
    }}

    p, label, [data-testid="stCaptionContainer"] {{
        color: {MUTED};
    }}

    [data-testid="stMetric"] {{
        background: {PANEL};
        border: 1px solid {BORDER};
        padding: 18px;
        border-radius: 12px;
    }}

    [data-testid="stMetricValue"] {{
        color: {GREEN} !important;
    }}

    .hero {{
        background: linear-gradient(115deg, #14263B, #102D32);
        border: 1px solid #245047;
        border-radius: 16px;
        padding: 24px 26px;
        margin-bottom: 20px;
    }}

    .hero h1 {{
        color: {WHITE} !important;
        margin-bottom: 6px;
    }}

    .hero p {{
        color: #D7E3EF;
        margin-bottom: 0;
    }}

    .section-title {{
        color: {WHITE};
        font-size: 22px;
        font-weight: 700;
        border-left: 4px solid {GREEN};
        padding-left: 12px;
        margin: 22px 0 6px 0;
    }}

    .section-description {{
        color: {MUTED};
        font-size: 14px;
        margin-bottom: 12px;
    }}

    div.stButton > button {{
        border-radius: 8px;
        border: 1px solid {GREEN};
    }}

    div[data-testid="stDownloadButton"] button {{
        border-radius: 8px;
    }}
</style>
""", unsafe_allow_html=True)

# Tema dos gráficos
CHART_THEME = dict(
    paper_bgcolor=PANEL,
    plot_bgcolor=PANEL,
    font=dict(color=WHITE, family="Arial"),
    margin=dict(l=20, r=20, t=60, b=35),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color=WHITE),
    ),
)


def configurar_eixos(fig):
    fig.update_layout(
        template="plotly_dark",
        title_font=dict(
            color="#FFFFFF",
            size=20
        ),
        font=dict(
            color="#FFFFFF",
            size=13
        ),
        paper_bgcolor="#151F32",
        plot_bgcolor="#151F32",
        legend=dict(
            font=dict(color="#FFFFFF")
        ),
        margin=dict(l=20, r=20, t=65, b=20),
    )

    fig.update_xaxes(
        title_font=dict(color="#FFFFFF"),
        tickfont=dict(color="#FFFFFF"),
        gridcolor="#2A3850",
        zerolinecolor="#2A3850"
    )

    fig.update_yaxes(
        title_font=dict(color="#FFFFFF"),
        tickfont=dict(color="#FFFFFF"),
        gridcolor="#2A3850",
        zerolinecolor="#2A3850"
    )

    return fig


def titulo_secao(titulo, descricao):
    st.markdown(
        f'<div class="section-title">{titulo}</div>'
        f'<div class="section-description">{descricao}</div>',
        unsafe_allow_html=True,
    )

# ==================================================
# CABEÇALHO
# ==================================================
st.markdown("""
<div class="hero">
    <h1>⚽ BRASILEIRÃO ANALYTICS</h1>
    <p>Resultados, desempenho e histórias do Campeonato Brasileiro Série A</p>
</div>
""", unsafe_allow_html=True)

# ==================================================
# API
# ==================================================
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

    df["Data"] = (
        pd.to_datetime(df["Data"], utc=True)
        .dt.tz_convert("America/Sao_Paulo")
        .dt.tz_localize(None)
    )

    for coluna in ["Rodada", "Gols mandante", "Gols visitante"]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    return df


# ==================================================
# FILTROS SIMPLIFICADOS
# ==================================================
with st.sidebar:
    st.markdown("## 🎛️ Explorar campeonato")
    st.caption("Escolha o recorte da análise.")

    temporada = st.selectbox(
        "Temporada",
        [2026, 2025, 2024],
        index=0,
    )

try:
    with st.spinner("Carregando partidas..."):
        df = carregar_partidas(temporada, token)

except requests.HTTPError as erro:
    codigo = erro.response.status_code

    if codigo == 403:
        st.error("Acesso negado. Confira o token e as permissões da API.")
    elif codigo == 429:
        st.error("Limite de consultas atingido. Tente mais tarde.")
    else:
        st.error(f"Erro HTTP {codigo}: {erro}")
    st.stop()

except requests.RequestException as erro:
    st.error(f"Falha na conexão com a API: {erro}")
    st.stop()

if df.empty:
    st.info("Não foram encontradas partidas para essa temporada.")
    st.stop()

clubes = sorted(
    set(df["Mandante"].dropna()) |
    set(df["Visitante"].dropna())
)

rodadas_disponiveis = sorted(
    df["Rodada"].dropna().astype(int).unique()
)

with st.sidebar:
    mandante = st.selectbox(
        "Time mandante",
        ["Todos os clubes"] + clubes,
    )

    visitante = st.selectbox(
        "Time visitante",
        ["Todos os clubes"] + clubes,
    )

    fase = st.radio(
        "Período do campeonato",
        [
            "Campeonato inteiro",
            "Rodadas iniciais",
            "Meio do campeonato",
            "Reta final",
        ],
    )

    st.divider()

    if st.button("🔄 Atualizar dados", use_container_width=True):
        carregar_partidas.clear()
        st.rerun()

    st.caption("Fonte: football-data.org")
    st.caption("Cache de 30 minutos")

# ==================================================
# APLICAR FILTROS
# ==================================================
filtrado = df.copy()

if mandante != "Todos os clubes":
    filtrado = filtrado[filtrado["Mandante"] == mandante]

if visitante != "Todos os clubes":
    filtrado = filtrado[filtrado["Visitante"] == visitante]

# Divide as rodadas disponíveis em três partes.
# Isso funciona mesmo quando a temporada ainda está em andamento.
if rodadas_disponiveis and fase != "Campeonato inteiro":
    quantidade = len(rodadas_disponiveis)
    tamanho = max(1, quantidade // 3)

    if fase == "Rodadas iniciais":
        rodadas_fase = rodadas_disponiveis[:tamanho]
    elif fase == "Meio do campeonato":
        inicio = tamanho
        fim = max(inicio + 1, quantidade - tamanho)
        rodadas_fase = rodadas_disponiveis[inicio:fim]
    else:
        rodadas_fase = rodadas_disponiveis[-tamanho:]

    filtrado = filtrado[
        filtrado["Rodada"].isin(rodadas_fase)
    ]

# Só jogos efetivamente finalizados e com placar completo
jogos = filtrado[
    (filtrado["Status"] == "FINISHED")
    & filtrado["Gols mandante"].notna()
    & filtrado["Gols visitante"].notna()
].copy()

jogos["Gols mandante"] = jogos["Gols mandante"].astype(int)
jogos["Gols visitante"] = jogos["Gols visitante"].astype(int)
jogos["Total gols"] = (
    jogos["Gols mandante"] + jogos["Gols visitante"]
)

jogos["Resultado"] = "Empate"
jogos.loc[
    jogos["Gols mandante"] > jogos["Gols visitante"],
    "Resultado"
] = "Vitória do mandante"
jogos.loc[
    jogos["Gols mandante"] < jogos["Gols visitante"],
    "Resultado"
] = "Vitória do visitante"

# ==================================================
# RESUMO EXECUTIVO
# ==================================================
titulo_secao(
    "📊 Visão geral",
    "Indicadores do recorte selecionado. As estatísticas consideram apenas jogos finalizados.",
)

total_jogos = len(jogos)
total_gols = int(jogos["Total gols"].sum()) if total_jogos else 0
media_gols = total_gols / total_jogos if total_jogos else 0

vitorias_casa = (
    int((jogos["Resultado"] == "Vitória do mandante").sum())
    if total_jogos else 0
)

pct_casa = (
    vitorias_casa / total_jogos * 100
    if total_jogos else 0
)

vitorias_fora = (
    int((jogos["Resultado"] == "Vitória do visitante").sum())
    if total_jogos else 0
)

pct_fora = (
    vitorias_fora / total_jogos * 100
    if total_jogos else 0
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Jogos finalizados", f"{total_jogos:,}".replace(",", "."))
c2.metric("Gols marcados", f"{total_gols:,}".replace(",", "."))
c3.metric("Média de gols / jogo", f"{media_gols:.2f}".replace(".", ","))
c4.metric("Vitórias em casa", f"{pct_casa:.1f}%".replace(".", ","))

if mandante != "Todos os clubes" or visitante != "Todos os clubes":
    descricao_mandante = (
        mandante if mandante != "Todos os clubes" else "qualquer mandante"
    )
    descricao_visitante = (
        visitante if visitante != "Todos os clubes" else "qualquer visitante"
    )
    st.caption(
        f"Confrontos: {descricao_mandante} × {descricao_visitante} "
        f"· Temporada {temporada} · {fase}"
    )
else:
    st.caption(f"Temporada {temporada} · {fase}")

if total_jogos == 0:
    st.info("Nenhum jogo finalizado nesse recorte. Altere os filtros.")

# ==================================================
# STORY 1 — RESULTADOS E MANDO
# ==================================================
titulo_secao(
    "🏟️ O fator casa faz diferença?",
    "Compare a distribuição dos resultados e a produção ofensiva dos mandantes e visitantes.",
)

if total_jogos:
    esquerda, direita = st.columns(2)

    ordem = [
        "Vitória do mandante",
        "Empate",
        "Vitória do visitante",
    ]

    contagem = (
        jogos["Resultado"].value_counts()
        .reindex(ordem, fill_value=0)
        .rename_axis("Resultado")
        .reset_index(name="Partidas")
    )

    with esquerda:
        fig = px.pie(
            contagem,
            names="Resultado",
            values="Partidas",
            hole=0.64,
            color="Resultado",
            color_discrete_map={
                "Vitória do mandante": GREEN,
                "Empate": YELLOW,
                "Vitória do visitante": BLUE,
            },
            title="Como terminam as partidas?",
        )
        fig.update_traces(
            textposition="inside",
            textinfo="percent+value",
            marker=dict(line=dict(color=PANEL, width=3)),
        )
        fig.update_layout(**CHART_THEME)
        st.plotly_chart(fig, use_container_width=True)

    with direita:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=["Mandantes", "Visitantes"],
            y=[
                int(jogos["Gols mandante"].sum()),
                int(jogos["Gols visitante"].sum()),
            ],
            marker_color=[GREEN, BLUE],
            text=[
                int(jogos["Gols mandante"].sum()),
                int(jogos["Gols visitante"].sum()),
            ],
            textposition="outside",
        ))
        fig.update_layout(
            title="Gols: casa versus fora",
            yaxis_title="Gols marcados",
            showlegend=False,
        )
        configurar_eixos(fig)
        st.plotly_chart(fig, use_container_width=True)

# ==================================================
# STORY 2 — EVOLUÇÃO POR RODADA
# ==================================================
titulo_secao(
    "📈 Como o campeonato produz gols?",
    "Veja o volume de gols por rodada e a média por partida.",
)

if total_jogos and jogos["Rodada"].notna().any():
    por_rodada = (
        jogos.dropna(subset=["Rodada"])
        .groupby("Rodada", as_index=False)
        .agg(
            Gols=("Total gols", "sum"),
            Partidas=("ID", "count"),
        )
        .sort_values("Rodada")
    )

    por_rodada["Média"] = por_rodada["Gols"] / por_rodada["Partidas"]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=por_rodada["Rodada"],
        y=por_rodada["Gols"],
        name="Gols",
        marker_color=GREEN,
    ))

    fig.add_trace(go.Scatter(
        x=por_rodada["Rodada"],
        y=por_rodada["Média"],
        name="Média por jogo",
        yaxis="y2",
        mode="lines+markers",
        line=dict(color=YELLOW, width=3),
        marker=dict(size=7),
    ))

    fig.update_layout(
        title="Gols e média por rodada",
        xaxis_title="Rodada",
        yaxis=dict(title="Total de gols"),
        yaxis2=dict(
            title="Média por jogo",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
    )

    configurar_eixos(fig)
    st.plotly_chart(fig, use_container_width=True)

# ==================================================
# STORY 3 — RANKING DE GOLS
# ==================================================
titulo_secao(
    "🔥 Quem tem o ataque mais produtivo?",
    "Ranking de gols marcados pelos clubes nas partidas que atendem aos filtros.",
)

if total_jogos:
    gols_casa = jogos[["Mandante", "Gols mandante"]].rename(
        columns={"Mandante": "Clube", "Gols mandante": "Gols"}
    )
    gols_fora = jogos[["Visitante", "Gols visitante"]].rename(
        columns={"Visitante": "Clube", "Gols visitante": "Gols"}
    )

    ranking = pd.concat(
        [gols_casa, gols_fora],
        ignore_index=True,
    )

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
        color_continuous_scale=["#1E3A5F", GREEN],
        title="Gols marcados por clube",
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(
        coloraxis_showscale=False,
        xaxis_title="Gols marcados",
        yaxis_title="",
    )

    configurar_eixos(fig)
    st.plotly_chart(fig, use_container_width=True)

# ==================================================
# TABELA DE PARTIDAS
# ==================================================
titulo_secao(
    "📋 Partidas",
    "Consulte os placares, pesquise clubes e exporte o recorte para CSV.",
)

busca = st.text_input(
    "Pesquisar mandante ou visitante",
    placeholder="Ex.: Flamengo, Palmeiras, Grêmio...",
)

tabela = filtrado.copy()

if busca.strip():
    mascara = (
        tabela["Mandante"].str.contains(busca, case=False, na=False)
        | tabela["Visitante"].str.contains(busca, case=False, na=False)
    )
    tabela = tabela[mascara]

tabela = tabela.sort_values(
    ["Rodada", "Data"],
    na_position="last",
)

tabela["Data"] = tabela["Data"].dt.strftime("%d/%m/%Y %H:%M")

tabela = tabela.rename(columns={
    "Gols mandante": "Gols casa",
    "Gols visitante": "Gols fora",
})

colunas = [
    "Data",
    "Rodada",
    "Mandante",
    "Gols casa",
    "Gols fora",
    "Visitante",
    "Status",
]

st.dataframe(
    tabela[colunas],
    use_container_width=True,
    hide_index=True,
    height=420,
)

st.download_button(
    "⬇️ Exportar partidas em CSV",
    data=tabela[colunas].to_csv(index=False).encode("utf-8-sig"),
    file_name=f"brasileirao_{temporada}.csv",
    mime="text/csv",
)

st.divider()
st.caption(
    "Fonte: football-data.org · Projeto de portfólio de análise de dados. "
    "Estatísticas calculadas sobre os jogos finalizados do recorte selecionado."
)
