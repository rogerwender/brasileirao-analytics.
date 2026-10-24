
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================

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
BRANCO = "#FFFFFF"
CINZA = "#B8C4D6"

st.markdown(
    f"""
    <style>
        .stApp {{
            background-color: {FUNDO};
            color: {BRANCO};
        }}

        [data-testid="stSidebar"] {{
            background-color: {PAINEL};
        }}

        h1, h2, h3, h4, h5, h6,
        p, label, span, div {{
            color: inherit;
        }}

        h1, h2, h3, h4 {{
            color: {BRANCO} !important;
        }}

        [data-testid="stMetricLabel"] {{
            color: {CINZA} !important;
        }}

        [data-testid="stMetricValue"] {{
            color: {BRANCO} !important;
        }}

        [data-testid="stMetricDelta"] {{
            color: {VERDE} !important;
        }}

        [data-testid="stDataFrame"] {{
            border: 1px solid #2A3850;
            border-radius: 10px;
        }}

        .hero {{
            background: linear-gradient(110deg, #14243A, #173D42);
            padding: 26px 30px;
            border-radius: 16px;
            border: 1px solid #2A5260;
            margin-bottom: 22px;
        }}

        .hero h1 {{
            color: #FFFFFF !important;
            font-size: 32px;
            margin: 0;
        }}

        .hero p {{
            color: #D6E4F0 !important;
            margin: 8px 0 0 0;
            font-size: 15px;
        }}

        .section-title {{
            color: #FFFFFF !important;
            font-size: 21px;
            font-weight: 700;
            margin-top: 14px;
            margin-bottom: 12px;
        }}

        div[data-testid="stVerticalBlock"] div[data-testid="stMetric"] {{
            background-color: {PAINEL};
            border: 1px solid #2A3850;
            padding: 16px;
            border-radius: 12px;
        }}

        .stButton button {{
            border-radius: 8px;
        }}
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# CABEÇALHO
# =========================================================

st.markdown(
    """
    <div class="hero">
        <h1>⚽ BRASILEIRÃO ANALYTICS</h1>
        <p>
            Análise de partidas, gols e desempenho dos clubes
            do Campeonato Brasileiro Série A.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# CONFIGURAÇÃO DOS GRÁFICOS
# =========================================================

def configurar_grafico(fig, altura=380):
    fig.update_layout(
        template="plotly_dark",
        height=altura,
        paper_bgcolor=PAINEL,
        plot_bgcolor=PAINEL,
        font=dict(
            family="Arial",
            size=13,
            color=BRANCO
        ),
        title_font=dict(
            family="Arial",
            size=19,
            color=BRANCO
        ),
        legend=dict(
            font=dict(color=BRANCO),
            bgcolor="rgba(0,0,0,0)"
        ),
        margin=dict(l=20, r=20, t=65, b=25)
    )

    fig.update_xaxes(
        title_font=dict(color=BRANCO),
        tickfont=dict(color=BRANCO),
        gridcolor="#2A3850",
        zerolinecolor="#2A3850"
    )

    fig.update_yaxes(
        title_font=dict(color=BRANCO),
        tickfont=dict(color=BRANCO),
        gridcolor="#2A3850",
        zerolinecolor="#2A3850"
    )

    return fig


# =========================================================
# CARREGAMENTO DOS DADOS DA API
# =========================================================

@st.cache_data(ttl=1800, show_spinner=False)
def carregar_partidas(temporada, token_api):
    url = "https://api.football-data.org/v4/competitions/BSA/matches"

    headers = {
        "X-Auth-Token": token_api
    }

    params = {
        "season": temporada
    }

    resposta = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    if resposta.status_code == 403:
        raise RuntimeError(
            "A API negou o acesso à temporada solicitada. "
            "Verifique as permissões do seu token e a cobertura "
            "da temporada no football-data.org."
        )

    if resposta.status_code == 429:
        raise RuntimeError(
            "Limite de consultas da API atingido. "
            "Aguarde um pouco antes de tentar novamente."
        )

    resposta.raise_for_status()

    dados = resposta.json()
    partidas = dados.get("matches", [])

    linhas = []

    for partida in partidas:
        placar = partida.get("score", {}).get("fullTime", {})

        linhas.append({
            "ID": partida.get("id"),
            "Rodada": partida.get("matchday"),
            "Data UTC": partida.get("utcDate"),
            "Mandante": partida.get("homeTeam", {}).get("name")
                or "Não informado",
            "Visitante": partida.get("awayTeam", {}).get("name")
                or "Não informado",
            "Gols mandante": placar.get("home"),
            "Gols visitante": placar.get("away"),
            "Status": partida.get("status", "UNKNOWN")
        })

    colunas = [
        "ID",
        "Rodada",
        "Data UTC",
        "Mandante",
        "Visitante",
        "Gols mandante",
        "Gols visitante",
        "Status"
    ]

    df_partidas = pd.DataFrame(linhas, columns=colunas)

    if not df_partidas.empty:
        datas = pd.to_datetime(
            df_partidas["Data UTC"],
            utc=True,
            errors="coerce"
        )

        df_partidas["Data"] = (
            datas.dt.tz_convert("America/Sao_Paulo")
            .dt.tz_localize(None)
        )

        df_partidas["Rodada"] = pd.to_numeric(
            df_partidas["Rodada"],
            errors="coerce"
        )

    else:
        df_partidas["Data"] = pd.Series(dtype="datetime64[ns]")

    return df_partidas


# =========================================================
# FILTROS
# =========================================================

st.sidebar.markdown("## ⚙️ Filtros")

temporada = st.sidebar.selectbox(
    "Temporada",
    options=[2026, 2025, 2024],
    index=0
)

if st.sidebar.button("🔄 Atualizar dados", use_container_width=True):
    carregar_partidas.clear()
    st.rerun()

token = st.secrets.get("FOOTBALL_DATA_TOKEN", "")

if not token:
    st.error(
        "Token da API não encontrado. Configure "
        "`FOOTBALL_DATA_TOKEN` em Settings → Secrets "
        "nas configurações do aplicativo Streamlit."
    )
    st.stop()


# =========================================================
# CONSULTA E TRATAMENTO DE ERROS
# =========================================================

try:
    with st.spinner("Carregando partidas do Brasileirão..."):
        df = carregar_partidas(temporada, token)

except requests.exceptions.Timeout:
    st.error("A consulta demorou demais. Tente novamente.")
    st.stop()

except requests.exceptions.RequestException as erro:
    st.error(f"Erro ao consultar a API: {erro}")
    st.stop()

except RuntimeError as erro:
    st.error(str(erro))
    st.stop()

except Exception as erro:
    st.error(f"Não foi possível carregar os dados: {erro}")
    st.stop()


if df.empty:
    st.warning(
        f"A API não retornou partidas para a temporada {temporada}. "
        "Verifique se a temporada está disponível no seu plano."
    )
    st.stop()


# =========================================================
# FILTRO ÚNICO DE TIME
# =========================================================

times = sorted(
    set(df["Mandante"].dropna().tolist())
    | set(df["Visitante"].dropna().tolist())
)

time_selecionado = st.sidebar.selectbox(
    "Time",
    options=["Todos os times"] + times,
    index=0
)

if time_selecionado != "Todos os times":
    df = df[
        (df["Mandante"] == time_selecionado)
        | (df["Visitante"] == time_selecionado)
    ].copy()

if df.empty:
    st.warning("Não foram encontradas partidas para os filtros selecionados.")
    st.stop()


# =========================================================
# INDICADORES E JOGOS FINALIZADOS
# =========================================================

status_finalizados = ["FINISHED", "AWARDED"]

jogos_finalizados = df[
    df["Status"].isin(status_finalizados)
    & df["Gols mandante"].notna()
    & df["Gols visitante"].notna()
].copy()

total_partidas = len(df)
total_finalizados = len(jogos_finalizados)
total_gols = 0
media_gols = 0.0
percentual_mandante = 0.0

if total_finalizados > 0:
    jogos_finalizados["Total de gols"] = (
        jogos_finalizados["Gols mandante"]
        + jogos_finalizados["Gols visitante"]
    )

    total_gols = int(jogos_finalizados["Total de gols"].sum())

    media_gols = total_gols / total_finalizados

    vitorias_mandante = (
        jogos_finalizados["Gols mandante"]
        > jogos_finalizados["Gols visitante"]
    ).sum()

    empates = (
        jogos_finalizados["Gols mandante"]
        == jogos_finalizados["Gols visitante"]
    ).sum()

    percentual_mandante = (
        vitorias_mandante / total_finalizados
    ) * 100


# =========================================================
# INDICADORES PRINCIPAIS
# =========================================================

st.markdown(
    '<div class="section-title">📊 Visão geral</div>',
    unsafe_allow_html=True
)

if time_selecionado == "Todos os times":
    subtitulo = f"Temporada {temporada} · Todos os clubes"
else:
    subtitulo = f"Temporada {temporada} · {time_selecionado}"

st.caption(subtitulo)

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Partidas disponíveis",
    f"{total_partidas:,}".replace(",", ".")
)

c2.metric(
    "Partidas finalizadas",
    f"{total_finalizados:,}".replace(",", ".")
)

c3.metric(
    "Gols marcados",
    f"{total_gols:,}".replace(",", ".")
)

c4.metric(
    "Média de gols por jogo",
    f"{media_gols:.2f}".replace(".", ",")
)

if total_finalizados == 0:
    st.info(
        "Ainda não há partidas finalizadas com placar disponível "
        "para os filtros selecionados."
    )


# =========================================================
# GRÁFICOS
# =========================================================

st.markdown(
    '<div class="section-title">📈 Análise dos jogos</div>',
    unsafe_allow_html=True
)

if total_finalizados > 0:

    # -----------------------------------------------------
    # 1. DISTRIBUIÇÃO DOS RESULTADOS
    # -----------------------------------------------------

    resultados = []

    for _, jogo in jogos_finalizados.iterrows():
        gols_casa = jogo["Gols mandante"]
        gols_fora = jogo["Gols visitante"]

        if gols_casa > gols_fora:
            resultado = "Vitória do mandante"
        elif gols_casa < gols_fora:
            resultado = "Vitória do visitante"
        else:
            resultado = "Empate"

        resultados.append(resultado)

    df_resultados = pd.Series(resultados).value_counts().reset_index()
    df_resultados.columns = ["Resultado", "Quantidade"]

    cores_resultados = {
        "Vitória do mandante": VERDE,
        "Empate": AMARELO,
        "Vitória do visitante": AZUL
    }

    fig_resultados = px.pie(
        df_resultados,
        names="Resultado",
        values="Quantidade",
        hole=0.60,
        title="Distribuição dos resultados",
        color="Resultado",
        color_discrete_map=cores_resultados
    )

    fig_resultados.update_traces(
        textposition="inside",
        textinfo="percent+label",
        textfont=dict(color=BRANCO, size=12)
    )

    fig_resultados = configurar_grafico(fig_resultados)

    # -----------------------------------------------------
    # 2. GOLS MARCADOS COMO MANDANTE E VISITANTE
    # -----------------------------------------------------

    gols_casa = int(jogos_finalizados["Gols mandante"].sum())
    gols_fora = int(jogos_finalizados["Gols visitante"].sum())

    df_gols_local = pd.DataFrame({
        "Local": ["Mandante", "Visitante"],
        "Gols": [gols_casa, gols_fora]
    })

    fig_gols_local = px.bar(
        df_gols_local,
        x="Local",
        y="Gols",
        title="Gols: mandante x visitante",
        color="Local",
        color_discrete_map={
            "Mandante": VERDE,
            "Visitante": AZUL
        },
        text="Gols"
    )

    fig_gols_local.update_traces(
        textposition="outside",
        textfont=dict(color=BRANCO)
    )

    fig_gols_local.update_layout(showlegend=False)
    fig_gols_local = configurar_grafico(fig_gols_local)

    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            fig_resultados,
            use_container_width=True
        )

    with col2:
        st.plotly_chart(
            fig_gols_local,
            use_container_width=True
        )

    # -----------------------------------------------------
    # 3. GOLS POR RODADA
    # -----------------------------------------------------

    df_rodadas = jogos_finalizados.dropna(subset=["Rodada"]).copy()

    if not df_rodadas.empty:
        df_rodadas["Rodada"] = df_rodadas["Rodada"].astype(int)

        gols_por_rodada = (
            df_rodadas.groupby("Rodada")
            .agg(
                Gols=("Total de gols", "sum"),
                Jogos=("ID", "count")
            )
            .reset_index()
            .sort_values("Rodada")
        )

        gols_por_rodada["Média de gols"] = (
            gols_por_rodada["Gols"] / gols_por_rodada["Jogos"]
        )

        fig_rodadas = make_subplots(specs=[[{"secondary_y": True}]])

        fig_rodadas.add_trace(
            go.Bar(
                x=gols_por_rodada["Rodada"],
                y=gols_por_rodada["Gols"],
                name="Total de gols",
                marker_color=VERDE
            ),
            secondary_y=False
        )

        fig_rodadas.add_trace(
            go.Scatter(
                x=gols_por_rodada["Rodada"],
                y=gols_por_rodada["Média de gols"],
                name="Média de gols",
                mode="lines+markers",
                line=dict(color=AMARELO, width=3),
                marker=dict(size=7)
            ),
            secondary_y=True
        )

        fig_rodadas.update_layout(
            title="Gols e média de gols por rodada",
            xaxis_title="Rodada",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        fig_rodadas.update_yaxes(
            title_text="Total de gols",
            secondary_y=False
        )

        fig_rodadas.update_yaxes(
            title_text="Média de gols",
            secondary_y=True,
            showgrid=False
        )

        fig_rodadas = configurar_grafico(fig_rodadas, altura=420)

        st.plotly_chart(
            fig_rodadas,
            use_container_width=True
        )

    # -----------------------------------------------------
    # 4. RANKING DE GOLS POR CLUBE NOS JOGOS FILTRADOS
    # -----------------------------------------------------

    gols_marcados = {}

    for _, jogo in jogos_finalizados.iterrows():
        mandante = jogo["Mandante"]
        visitante = jogo["Visitante"]

        gols_marcados[mandante] = (
            gols_marcados.get(mandante, 0)
            + int(jogo["Gols mandante"])
        )

        gols_marcados[visitante] = (
            gols_marcados.get(visitante, 0)
            + int(jogo["Gols visitante"])
        )

    df_ranking = pd.DataFrame(
        [
            {"Time": time, "Gols": gols}
            for time, gols in gols_marcados.items()
        ]
    )

    if not df_ranking.empty:
        df_ranking = df_ranking.sort_values(
            "Gols",
            ascending=True
        )

        titulo_ranking = (
            "Gols por clube nos jogos filtrados"
            if time_selecionado == "Todos os times"
            else f"Gols nos jogos de {time_selecionado}"
        )

        fig_ranking = px.bar(
            df_ranking,
            x="Gols",
            y="Time",
            orientation="h",
            title=titulo_ranking,
            text="Gols",
            color="Gols",
            color_continuous_scale=["#176B5B", VERDE]
        )

        fig_ranking.update_traces(
            textposition="outside",
            textfont=dict(color=BRANCO)
        )

        fig_ranking.update_layout(
            coloraxis_showscale=False,
            yaxis=dict(
                categoryorder="total ascending"
            )
        )

        fig_ranking = configurar_grafico(
            fig_ranking,
            altura=max(380, len(df_ranking) * 32)
        )

        st.plotly_chart(
            fig_ranking,
            use_container_width=True
        )


# =========================================================
# TABELA DE PARTIDAS
# =========================================================

st.markdown(
    '<div class="section-title">🗓️ Partidas</div>',
    unsafe_allow_html=True
)

busca = st.text_input(
    "Buscar clube na tabela",
    placeholder="Digite o nome de um time..."
)

df_tabela = df.copy()

if busca.strip():
    termo = busca.strip().casefold()

    df_tabela = df_tabela[
        df_tabela["Mandante"].str.casefold().str.contains(
            termo, na=False
        )
        | df_tabela["Visitante"].str.casefold().str.contains(
            termo, na=False
        )
    ]

df_tabela = df_tabela.sort_values(
    ["Rodada", "Data"],
    na_position="last"
)

def formatar_placar(linha):
    gols_casa = linha["Gols mandante"]
    gols_fora = linha["Gols visitante"]

    if pd.notna(gols_casa) and pd.notna(gols_fora):
        return f"{int(gols_casa)} x {int(gols_fora)}"

    return "—"

df_tabela["Placar"] = df_tabela.apply(
    formatar_placar,
    axis=1
)

df_tabela["Data"] = pd.to_datetime(
    df_tabela["Data"],
    errors="coerce"
).dt.strftime("%d/%m/%Y %H:%M")

df_tabela["Rodada"] = df_tabela["Rodada"].apply(
    lambda valor: int(valor) if pd.notna(valor) else "—"
)

df_tabela["Rodada"] = df_tabela["Rodada"].astype(str)

df_exibicao = df_tabela[
    [
        "Rodada",
        "Data",
        "Mandante",
        "Placar",
        "Visitante",
        "Status"
    ]
].rename(columns={
    "Rodada": "Rodada",
    "Data": "Data e hora",
    "Mandante": "Mandante",
    "Placar": "Placar",
    "Visitante": "Visitante",
    "Status": "Status"
})

st.caption(
    f"{len(df_exibicao)} partida(s) encontrada(s) "
    "para os filtros selecionados."
)

st.dataframe(
    df_exibicao,
    use_container_width=True,
    hide_index=True
)

csv = df_exibicao.to_csv(
    index=False,
    sep=";",
    encoding="utf-8-sig"
)

st.download_button(
    label="⬇️ Baixar partidas em CSV",
    data=csv,
    file_name=f"brasileirao_{temporada}.csv",
    mime="text/csv",
    use_container_width=False
)


# =========================================================
# RODAPÉ
# =========================================================

st.divider()

st.caption(
    "Fonte: football-data.org · Atualização automática dos dados "
    "em cache a cada 30 minutos. Use “Atualizar dados” para "
    "solicitar uma nova consulta."
)
