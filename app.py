
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# =====================================================
# CONFIGURAÇÃO
# =====================================================

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
BRANCO = "#FFFFFF"
CINZA = "#B8C4D6"

st.markdown("""
<style>
    .stApp {
        background: #0B1220;
        color: #FFFFFF;
    }

    /* Reduz o espaço superior dentro do aplicativo */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1600px;
    }

    [data-testid="stSidebar"] {
        background: #151F32;
        border-right: 1px solid #2A3850;
    }

    h1, h2, h3, h4, p, label {
        color: #FFFFFF !important;
    }

    [data-testid="stMetric"] {
        background: #151F32;
        border: 1px solid #2A3850;
        padding: 15px;
        border-radius: 12px;
    }

    [data-testid="stMetricLabel"] {
        color: #B8C4D6 !important;
    }

    [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
    }

    .hero {
        background: linear-gradient(110deg, #14243A, #173D42);
        padding: 18px 24px;
        border-radius: 14px;
        border: 1px solid #2A5260;
        margin-bottom: 20px;
    }

    .hero h1 {
        font-size: clamp(22px, 2.5vw, 32px);
        margin: 0;
        color: #FFFFFF !important;
    }

    .hero p {
        color: #D6E4F0 !important;
        margin: 6px 0 0 0;
        font-size: 14px;
    }

    .section-title {
        color: #FFFFFF;
        font-size: 21px;
        font-weight: 700;
        margin: 8px 0 14px 0;
    }

    div[data-testid="stPlotlyChart"] {
        background: #151F32;
        border: 1px solid #26364D;
        border-radius: 12px;
        padding: 5px;
    }

    .stButton button {
        border-radius: 8px;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #FFFFFF;
    }
</style>
""", unsafe_allow_html=True)


# =====================================================
# FUNÇÕES
# =====================================================

@st.cache_data(ttl=1800, show_spinner=False)
def carregar_partidas(temporada, token):
    url = "https://api.football-data.org/v4/competitions/BSA/matches"

    resposta = requests.get(
        url,
        headers={"X-Auth-Token": token},
        params={"season": temporada},
        timeout=30
    )

    if resposta.status_code == 403:
        raise RuntimeError(
            "A API negou o acesso. Verifique o token e "
            "a cobertura da temporada no seu plano."
        )

    if resposta.status_code == 429:
        raise RuntimeError(
            "Limite de consultas atingido. Aguarde e tente novamente."
        )

    resposta.raise_for_status()
    partidas = resposta.json().get("matches", [])

    linhas = []

    for p in partidas:
        placar = p.get("score", {}).get("fullTime", {})

        linhas.append({
            "ID": p.get("id"),
            "Rodada": p.get("matchday"),
            "Data UTC": p.get("utcDate"),
            "Mandante": p.get("homeTeam", {}).get("name") or "Não informado",
            "Visitante": p.get("awayTeam", {}).get("name") or "Não informado",
            "Gols mandante": placar.get("home"),
            "Gols visitante": placar.get("away"),
            "Status": p.get("status", "UNKNOWN")
        })

    df = pd.DataFrame(linhas)

    if df.empty:
        return df

    df["Data"] = (
        pd.to_datetime(df["Data UTC"], utc=True, errors="coerce")
        .dt.tz_convert("America/Sao_Paulo")
        .dt.tz_localize(None)
    )

    df["Rodada"] = pd.to_numeric(df["Rodada"], errors="coerce")

    return df


def configurar_grafico(fig, altura=380):
    fig.update_layout(
        template="plotly_dark",
        height=altura,
        paper_bgcolor=PAINEL,
        plot_bgcolor=PAINEL,
        font=dict(color=BRANCO, size=13, family="Arial"),
        title_font=dict(color=BRANCO, size=19),
        legend=dict(
            font=dict(color=BRANCO),
            bgcolor="rgba(0,0,0,0)"
        ),
        margin=dict(l=20, r=25, t=65, b=25)
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


# =====================================================
# MENU LATERAL E NAVEGAÇÃO
# =====================================================

st.sidebar.markdown("## ⚽ Brasileirão")
st.sidebar.caption("Painel de análise de dados")

pagina = st.sidebar.radio(
    "Navegação",
    [
        "Visão geral",
        "Gols",
        "Desempenho",
        "Partidas"
    ],
    index=0,
    format_func=lambda x: {
        "Visão geral": "📊  Visão geral",
        "Gols": "⚽  Gols",
        "Desempenho": "🏆  Desempenho",
        "Partidas": "🗓️  Partidas"
    }[x]
)

st.sidebar.divider()
st.sidebar.markdown("### Filtros")

temporada = st.sidebar.selectbox(
    "Temporada",
    [2026, 2025, 2024],
    index=0
)

token = st.secrets.get("FOOTBALL_DATA_TOKEN", "")

if not token:
    st.error(
        "Token não encontrado. Configure "
        "FOOTBALL_DATA_TOKEN em Settings → Secrets "
        "nas configurações do Streamlit."
    )
    st.stop()

if st.sidebar.button("🔄 Atualizar dados", use_container_width=True):
    carregar_partidas.clear()
    st.rerun()


# =====================================================
# CARREGAR DADOS
# =====================================================

try:
    with st.spinner("Carregando partidas..."):
        dados = carregar_partidas(temporada, token)

except requests.exceptions.RequestException as e:
    st.error(f"Erro de comunicação com a API: {e}")
    st.stop()

except RuntimeError as e:
    st.error(str(e))
    st.stop()

except Exception as e:
    st.error(f"Não foi possível carregar os dados: {e}")
    st.stop()

if dados.empty:
    st.warning(
        f"Nenhuma partida foi retornada para {temporada}. "
        "Verifique a disponibilidade dessa temporada na API."
    )
    st.stop()


# O filtro de time considera mandante OU visitante.
times = sorted(
    set(dados["Mandante"].dropna())
    | set(dados["Visitante"].dropna())
)

time_selecionado = st.sidebar.selectbox(
    "Time",
    ["Todos os times"] + times
)

df = dados.copy()

if time_selecionado != "Todos os times":
    df = df[
        (df["Mandante"] == time_selecionado)
        | (df["Visitante"] == time_selecionado)
    ].copy()

if df.empty:
    st.info("Não há partidas para os filtros selecionados.")
    st.stop()


# =====================================================
# CABEÇALHO COMPACTO
# =====================================================

st.markdown("""
<div class="hero">
    <h1>⚽ BRASILEIRÃO ANALYTICS</h1>
    <p>Estatísticas, gols e desempenho do Campeonato Brasileiro Série A</p>
</div>
""", unsafe_allow_html=True)

st.caption(
    f"Temporada {temporada}  ·  "
    + (
        "Todos os clubes"
        if time_selecionado == "Todos os times"
        else time_selecionado
    )
)


# =====================================================
# INDICADORES
# =====================================================

finalizados = df[
    df["Status"].isin(["FINISHED", "AWARDED"])
    & df["Gols mandante"].notna()
    & df["Gols visitante"].notna()
].copy()

finalizados["Total de gols"] = (
    finalizados["Gols mandante"] + finalizados["Gols visitante"]
)

total_jogos = len(finalizados)
total_gols = int(finalizados["Total de gols"].sum()) if total_jogos else 0
media_gols = total_gols / total_jogos if total_jogos else 0

vitorias_casa = (
    finalizados["Gols mandante"] > finalizados["Gols visitante"]
).sum() if total_jogos else 0

pct_casa = 100 * vitorias_casa / total_jogos if total_jogos else 0

if pagina == "Visão geral":
    st.markdown(
        '<div class="section-title">Indicadores principais</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Partidas disponíveis", f"{len(df):,}".replace(",", "."))
    c2.metric("Partidas finalizadas", f"{total_jogos:,}".replace(",", "."))
    c3.metric("Gols marcados", f"{total_gols:,}".replace(",", "."))
    c4.metric("Média de gols", f"{media_gols:.2f}".replace(".", ","))

    if total_jogos == 0:
        st.info("Ainda não há partidas finalizadas para apresentar estatísticas.")
    else:
        vitorias_fora = (
            finalizados["Gols mandante"] < finalizados["Gols visitante"]
        ).sum()

        empates = (
            finalizados["Gols mandante"] == finalizados["Gols visitante"]
        ).sum()

        resultados = pd.DataFrame({
            "Resultado": [
                "Vitória do mandante",
                "Empate",
                "Vitória do visitante"
            ],
            "Quantidade": [
                int(vitorias_casa),
                int(empates),
                int(vitorias_fora)
            ]
        })

        fig = px.pie(
            resultados,
            names="Resultado",
            values="Quantidade",
            hole=0.58,
            title="Distribuição dos resultados",
            color="Resultado",
            color_discrete_map={
                "Vitória do mandante": VERDE,
                "Empate": AMARELO,
                "Vitória do visitante": AZUL
            }
        )

        fig.update_traces(
            textposition="inside",
            textinfo="percent+label",
            textfont=dict(color=BRANCO)
        )

        st.plotly_chart(
            configurar_grafico(fig),
            use_container_width=True
        )


# =====================================================
# PÁGINA: GOLS
# =====================================================

elif pagina == "Gols":
    st.markdown(
        '<div class="section-title">Análise de gols</div>',
        unsafe_allow_html=True
    )

    if finalizados.empty:
        st.info("Não existem jogos finalizados para calcular os gols.")
    else:
        casa = int(finalizados["Gols mandante"].sum())
        fora = int(finalizados["Gols visitante"].sum())

        fig_local = px.bar(
            pd.DataFrame({
                "Local": ["Mandante", "Visitante"],
                "Gols": [casa, fora]
            }),
            x="Local",
            y="Gols",
            color="Local",
            text="Gols",
            title="Gols marcados: mandante x visitante",
            color_discrete_map={
                "Mandante": VERDE,
                "Visitante": AZUL
            }
        )

        fig_local.update_traces(
            textposition="outside",
            textfont=dict(color=BRANCO)
        )
        fig_local.update_layout(showlegend=False)

        st.plotly_chart(
            configurar_grafico(fig_local),
            use_container_width=True
        )

        por_rodada = (
            finalizados.dropna(subset=["Rodada"])
            .groupby("Rodada")
            .agg(
                Gols=("Total de gols", "sum"),
                Jogos=("ID", "count")
            )
            .reset_index()
            .sort_values("Rodada")
        )

        if not por_rodada.empty:
            por_rodada["Média por jogo"] = (
                por_rodada["Gols"] / por_rodada["Jogos"]
            )

            fig_rodada = go.Figure()

            fig_rodada.add_bar(
                x=por_rodada["Rodada"],
                y=por_rodada["Gols"],
                name="Total de gols",
                marker_color=VERDE
            )

            fig_rodada.add_scatter(
                x=por_rodada["Rodada"],
                y=por_rodada["Média por jogo"],
                name="Média por jogo",
                mode="lines+markers",
                line=dict(color=AMARELO, width=3),
                yaxis="y2"
            )

            fig_rodada.update_layout(
                title="Gols por rodada",
                xaxis_title="Rodada",
                yaxis=dict(title="Total de gols"),
                yaxis2=dict(
                    title="Média de gols",
                    overlaying="y",
                    side="right",
                    showgrid=False,
                    tickfont=dict(color=BRANCO),
                    title_font=dict(color=BRANCO)
                )
            )

            st.plotly_chart(
                configurar_grafico(fig_rodada, 430),
                use_container_width=True
            )

        gols_clubes = {}

        for _, jogo in finalizados.iterrows():
            mandante = jogo["Mandante"]
            visitante = jogo["Visitante"]

            gols_clubes[mandante] = (
                gols_clubes.get(mandante, 0)
                + int(jogo["Gols mandante"])
            )
            gols_clubes[visitante] = (
                gols_clubes.get(visitante, 0)
                + int(jogo["Gols visitante"])
            )

        ranking = pd.DataFrame([
            {"Time": time, "Gols": gols}
            for time, gols in gols_clubes.items()
        ]).sort_values("Gols", ascending=True)

        fig_ranking = px.bar(
            ranking,
            x="Gols",
            y="Time",
            orientation="h",
            text="Gols",
            title="Gols por clube nos jogos filtrados",
            color="Gols",
            color_continuous_scale=["#176B5B", VERDE]
        )

        fig_ranking.update_layout(coloraxis_showscale=False)

        fig_ranking.update_traces(
            textposition="outside",
            textfont=dict(color=BRANCO)
        )

        st.plotly_chart(
            configurar_grafico(
                fig_ranking,
                max(400, len(ranking) * 30)
            ),
            use_container_width=True
        )


# =====================================================
# PÁGINA: DESEMPENHO
# =====================================================

elif pagina == "Desempenho":
    st.markdown(
        '<div class="section-title">Desempenho dos clubes</div>',
        unsafe_allow_html=True
    )

    if finalizados.empty:
        st.info("Não existem jogos finalizados para calcular o desempenho.")
    else:
        estatisticas = {}

        for _, jogo in finalizados.iterrows():
            mandante = jogo["Mandante"]
            visitante = jogo["Visitante"]
            gc = int(jogo["Gols mandante"])
            gf = int(jogo["Gols visitante"])

            for time in [mandante, visitante]:
                if time not in estatisticas:
                    estatisticas[time] = {
                        "Time": time,
                        "Jogos": 0,
                        "Vitórias": 0,
                        "Empates": 0,
                        "Derrotas": 0,
                        "Gols pró": 0,
                        "Gols contra": 0,
                        "Pontos": 0
                    }

            estatisticas[mandante]["Jogos"] += 1
            estatisticas[visitante]["Jogos"] += 1

            estatisticas[mandante]["Gols pró"] += gc
            estatisticas[mandante]["Gols contra"] += gf
            estatisticas[visitante]["Gols pró"] += gf
            estatisticas[visitante]["Gols contra"] += gc

            if gc > gf:
                estatisticas[mandante]["Vitórias"] += 1
                estatisticas[mandante]["Pontos"] += 3
                estatisticas[visitante]["Derrotas"] += 1
            elif gc < gf:
                estatisticas[visitante]["Vitórias"] += 1
                estatisticas[visitante]["Pontos"] += 3
                estatisticas[mandante]["Derrotas"] += 1
            else:
                estatisticas[mandante]["Empates"] += 1
                estatisticas[visitante]["Empates"] += 1
                estatisticas[mandante]["Pontos"] += 1
                estatisticas[visitante]["Pontos"] += 1

        tabela = pd.DataFrame(list(estatisticas.values()))
        tabela["Saldo de gols"] = tabela["Gols pró"] - tabela["Gols contra"]

        tabela = tabela.sort_values(
            ["Pontos", "Vitórias", "Saldo de gols", "Gols pró"],
            ascending=[False, False, False, False]
        ).reset_index(drop=True)

        tabela.insert(0, "Posição", range(1, len(tabela) + 1))

        if time_selecionado != "Todos os times":
            tabela = tabela[tabela["Time"] == time_selecionado]

        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "Classificação calculada apenas com as partidas finalizadas "
            "incluídas nos dados filtrados. Não substitui a tabela oficial."
        )


# =====================================================
# PÁGINA: PARTIDAS
# =====================================================

elif pagina == "Partidas":
    st.markdown(
        '<div class="section-title">Partidas do campeonato</div>',
        unsafe_allow_html=True
    )

    busca = st.text_input(
        "Buscar clube",
        placeholder="Digite o nome de um time..."
    )

    tabela = df.copy()

    if busca.strip():
        termo = busca.strip()
        tabela = tabela[
            tabela["Mandante"].str.contains(
                termo, case=False, na=False
            )
            | tabela["Visitante"].str.contains(
                termo, case=False, na=False
            )
        ]

    tabela = tabela.sort_values(
        ["Rodada", "Data"],
        na_position="last"
    )

    def placar(linha):
        gc = linha["Gols mandante"]
        gf = linha["Gols visitante"]

        if pd.notna(gc) and pd.notna(gf):
            return f"{int(gc)} x {int(gf)}"

        return "—"

    tabela["Placar"] = tabela.apply(placar, axis=1)

    tabela["Data e hora"] = (
        pd.to_datetime(tabela["Data"], errors="coerce")
        .dt.strftime("%d/%m/%Y %H:%M")
    )

    tabela["Rodada"] = tabela["Rodada"].apply(
        lambda x: str(int(x)) if pd.notna(x) else "—"
    )

    exibicao = tabela[[
        "Rodada",
        "Data e hora",
        "Mandante",
        "Placar",
        "Visitante",
        "Status"
    ]]

    st.caption(f"{len(exibicao)} partida(s) encontrada(s).")

    st.dataframe(
        exibicao,
        use_container_width=True,
        hide_index=True
    )

    csv = exibicao.to_csv(
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    st.download_button(
        "⬇️ Baixar partidas em CSV",
        data=csv,
        file_name=f"brasileirao_{temporada}.csv",
        mime="text/csv"
    )


# =====================================================
# RODAPÉ
# =====================================================

st.divider()

st.caption(
    "Fonte: football-data.org · Cache de dados de 30 minutos. "
    "Use Atualizar dados para solicitar uma nova consulta."
)
