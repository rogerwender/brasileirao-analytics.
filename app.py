import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# =========================================================
# 1. CONFIGURAÇÕES GERAIS
# =========================================================

st.set_page_config(
    page_title="Brasileirão Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

CORES = {
    "fundo": "#0B1120",
    "painel": "#121C2E",
    "painel_hover": "#19263B",
    "borda": "#26364D",
    "texto": "#F4F7FB",
    "texto_secundario": "#A9B8CC",
    "verde": "#2DD4A7",
    "azul": "#60A5FA",
    "amarelo": "#FBBF24",
    "vermelho": "#FB7185",
    "roxo": "#A78BFA",
}

STATUS_FINALIZADOS = {"FINISHED", "AWARDED"}
TEMPORADAS = [2026, 2025, 2024, 2023, 2022, 2021, 2020]


# =========================================================
# 2. ESTILO VISUAL
# =========================================================

def aplicar_estilo():
    """Aplica o tema visual do aplicativo."""
    st.markdown(
        f"""
        <style>
        :root {{
            color-scheme: dark;
        }}

        .stApp {{
            background: {CORES["fundo"]};
            color: {CORES["texto"]};
        }}

        .block-container {{
            max-width: 1550px;
            padding-top: 1.1rem;
            padding-bottom: 2.5rem;
        }}

        [data-testid="stHeader"] {{
            background: rgba(11, 17, 32, 0.85);
        }}

        [data-testid="stSidebar"] {{
            background: {CORES["painel"]};
            border-right: 1px solid {CORES["borda"]};
        }}

        [data-testid="stSidebar"] .block-container {{
            padding-top: 1.4rem;
        }}

        h1, h2, h3, h4, p, label {{
            color: {CORES["texto"]};
        }}

        h1, h2, h3 {{
            letter-spacing: -0.025em;
        }}

        [data-testid="stCaptionContainer"] p {{
            color: {CORES["texto_secundario"]} !important;
        }}

        [data-testid="stMetric"] {{
            background: linear-gradient(145deg, #162238, #111B2C);
            border: 1px solid {CORES["borda"]};
            padding: 17px 18px;
            border-radius: 15px;
        }}

        [data-testid="stMetricLabel"] p {{
            color: {CORES["texto_secundario"]} !important;
            font-size: 0.84rem;
        }}

        [data-testid="stMetricValue"] {{
            color: {CORES["texto"]} !important;
            font-weight: 700;
        }}

        [data-testid="stPlotlyChart"] {{
            background: {CORES["painel"]};
            border: 1px solid {CORES["borda"]};
            border-radius: 15px;
            padding: 7px 7px 0 7px;
        }}

        [data-testid="stDataFrame"] {{
            border: 1px solid {CORES["borda"]};
            border-radius: 12px;
            overflow: hidden;
        }}

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div {{
            background-color: #0D1728;
            border-color: {CORES["borda"]};
            border-radius: 9px;
        }}

        div[data-testid="stRadio"] label {{
            background: #0D1728;
            border: 1px solid {CORES["borda"]};
            border-radius: 9px;
            padding: 8px 10px;
            margin-bottom: 5px;
        }}

        .hero {{
            background:
                radial-gradient(circle at 90% 0%, rgba(45,212,167,0.16), transparent 30%),
                linear-gradient(120deg, #15243A, #112B35);
            border: 1px solid #2A4B58;
            border-radius: 18px;
            padding: 22px 26px;
            margin-bottom: 20px;
        }}

        .hero-eyebrow {{
            color: {CORES["verde"]};
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-size: 0.72rem;
            font-weight: 700;
            margin-bottom: 8px;
        }}

        .hero-title {{
            color: #FFFFFF;
            font-size: clamp(1.65rem, 3vw, 2.25rem);
            line-height: 1.1;
            font-weight: 800;
            letter-spacing: -0.04em;
            margin: 0;
        }}

        .hero-subtitle {{
            color: #C3D1E1;
            font-size: 0.94rem;
            margin-top: 9px;
        }}

        .section-heading {{
            font-size: 1.15rem;
            font-weight: 750;
            color: {CORES["texto"]};
            margin: 0.5rem 0 0.15rem 0;
        }}

        .section-description {{
            color: {CORES["texto_secundario"]};
            font-size: 0.85rem;
            margin-bottom: 0.85rem;
        }}

        .filter-note {{
            color: {CORES["texto_secundario"]};
            font-size: 0.78rem;
            line-height: 1.45;
        }}

        .stButton button, .stDownloadButton button {{
            border-radius: 9px;
            font-weight: 650;
        }}

        hr {{
            border-color: {CORES["borda"]};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 3. API E CARREGAMENTO DOS DADOS
# =========================================================

@st.cache_data(ttl=1800, show_spinner=False)
def carregar_partidas(temporada: int, token: str) -> pd.DataFrame:
    """Consulta a API e devolve uma tabela normalizada de partidas."""
    url = "https://api.football-data.org/v4/competitions/BSA/matches"
    resposta = requests.get(
        url,
        headers={"X-Auth-Token": token},
        params={"season": temporada},
        timeout=30,
    )

    if resposta.status_code == 403:
        raise RuntimeError(
            "A API recusou o acesso. Confira o token e se a temporada "
            "está disponível no seu plano do football-data.org."
        )
    if resposta.status_code == 429:
        raise RuntimeError(
            "O limite de consultas da API foi atingido. Aguarde um pouco "
            "ou tente novamente mais tarde."
        )

    resposta.raise_for_status()
    partidas = resposta.json().get("matches", [])

    colunas = [
        "ID", "Rodada", "Data UTC", "Mandante", "Visitante",
        "Gols mandante", "Gols visitante", "Status"
    ]
    registros = []

    for partida in partidas:
        placar = partida.get("score", {}).get("fullTime", {})
        registros.append({
            "ID": partida.get("id"),
            "Rodada": partida.get("matchday"),
            "Data UTC": partida.get("utcDate"),
            "Mandante": partida.get("homeTeam", {}).get("name") or "Não informado",
            "Visitante": partida.get("awayTeam", {}).get("name") or "Não informado",
            "Gols mandante": placar.get("home"),
            "Gols visitante": placar.get("away"),
            "Status": partida.get("status", "UNKNOWN"),
        })

    df = pd.DataFrame(registros, columns=colunas)
    if df.empty:
        df["Data"] = pd.Series(dtype="datetime64[ns]")
        return df

    df["Data"] = (
        pd.to_datetime(df["Data UTC"], utc=True, errors="coerce")
        .dt.tz_convert("America/Sao_Paulo")
        .dt.tz_localize(None)
    )
    df["Rodada"] = pd.to_numeric(df["Rodada"], errors="coerce")
    return df


def preparar_jogos_finalizados(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna somente partidas finalizadas com placar disponível."""
    jogos = df[
        df["Status"].isin(STATUS_FINALIZADOS)
        & df["Gols mandante"].notna()
        & df["Gols visitante"].notna()
    ].copy()

    if not jogos.empty:
        jogos["Gols mandante"] = jogos["Gols mandante"].astype(int)
        jogos["Gols visitante"] = jogos["Gols visitante"].astype(int)
        jogos["Total de gols"] = jogos["Gols mandante"] + jogos["Gols visitante"]

    return jogos


# =========================================================
# 4. COMPONENTES REUTILIZÁVEIS
# =========================================================

def titulo_secao(titulo: str, descricao: str = ""):
    """Mostra um título de seção e uma descrição opcional."""
    st.markdown(
        f'<div class="section-heading">{titulo}</div>'
        + (f'<div class="section-description">{descricao}</div>' if descricao else ""),
        unsafe_allow_html=True,
    )


def estilizar_grafico(fig, altura: int = 370):
    """Aplica o padrão visual a todos os gráficos Plotly."""
    fig.update_layout(
        template="plotly_dark",
        height=altura,
        paper_bgcolor=CORES["painel"],
        plot_bgcolor=CORES["painel"],
        font=dict(
            family="Arial, sans-serif",
            size=12,
            color=CORES["texto"],
        ),
        title=dict(
            font=dict(size=17, color=CORES["texto"]),
            x=0.03,
            xanchor="left",
        ),
        margin=dict(l=18, r=18, t=62, b=20),
        legend=dict(
            font=dict(color=CORES["texto_secundario"], size=11),
            bgcolor="rgba(0,0,0,0)",
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=1,
        ),
        hoverlabel=dict(
            bgcolor="#1D2A40",
            bordercolor=CORES["borda"],
            font=dict(color="#FFFFFF", size=12),
        ),
    )
    fig.update_xaxes(
        gridcolor="rgba(169,184,204,0.10)",
        zerolinecolor="rgba(169,184,204,0.15)",
        tickfont=dict(color=CORES["texto_secundario"]),
        title_font=dict(color=CORES["texto_secundario"]),
        showline=False,
    )
    fig.update_yaxes(
        gridcolor="rgba(169,184,204,0.10)",
        zerolinecolor="rgba(169,184,204,0.15)",
        tickfont=dict(color=CORES["texto_secundario"]),
        title_font=dict(color=CORES["texto_secundario"]),
        showline=False,
    )
    return fig


def mostrar_indicadores(df: pd.DataFrame, jogos: pd.DataFrame):
    """Exibe os quatro indicadores principais."""
    quantidade = len(jogos)
    gols = int(jogos["Total de gols"].sum()) if quantidade else 0
    media = gols / quantidade if quantidade else 0
    mandante_vence = (
        int((jogos["Gols mandante"] > jogos["Gols visitante"]).sum())
        if quantidade else 0
    )
    pct_mandante = 100 * mandante_vence / quantidade if quantidade else 0

    colunas = st.columns(4)
    colunas[0].metric("Partidas no filtro", f"{len(df):,}".replace(",", "."))
    colunas[1].metric("Jogos finalizados", f"{quantidade:,}".replace(",", "."))
    colunas[2].metric("Total de gols", f"{gols:,}".replace(",", "."))
    colunas[3].metric(
        "Média de gols",
        f"{media:.2f}".replace(".", ","),
        help=f"Vitórias dos mandantes: {pct_mandante:.1f}% dos jogos finalizados.",
    )


def criar_resultados(jogos: pd.DataFrame) -> pd.DataFrame:
    """Resume vitórias dos mandantes, empates e vitórias dos visitantes."""
    casa = int((jogos["Gols mandante"] > jogos["Gols visitante"]).sum())
    empate = int((jogos["Gols mandante"] == jogos["Gols visitante"]).sum())
    fora = int((jogos["Gols mandante"] < jogos["Gols visitante"]).sum())
    return pd.DataFrame({
        "Resultado": ["Vitória do mandante", "Empate", "Vitória do visitante"],
        "Quantidade": [casa, empate, fora],
    })


def criar_ranking_gols(jogos: pd.DataFrame) -> pd.DataFrame:
    """Calcula os gols por clube nas partidas incluídas no filtro."""
    gols = {}
    for _, partida in jogos.iterrows():
        casa = partida["Mandante"]
        fora = partida["Visitante"]
        gols[casa] = gols.get(casa, 0) + int(partida["Gols mandante"])
        gols[fora] = gols.get(fora, 0) + int(partida["Gols visitante"])

    return pd.DataFrame(
        [{"Time": time, "Gols": total} for time, total in gols.items()]
    ).sort_values("Gols", ascending=True) if gols else pd.DataFrame(columns=["Time", "Gols"])


def criar_classificacao(jogos: pd.DataFrame) -> pd.DataFrame:
    """Calcula pontos e estatísticas a partir dos jogos carregados."""
    times = {}

    def obter_time(nome):
        if nome not in times:
            times[nome] = {
                "Time": nome, "J": 0, "V": 0, "E": 0, "D": 0,
                "GP": 0, "GC": 0, "Pontos": 0,
            }
        return times[nome]

    for _, jogo in jogos.iterrows():
        casa = obter_time(jogo["Mandante"])
        fora = obter_time(jogo["Visitante"])
        gc = int(jogo["Gols mandante"])
        gf = int(jogo["Gols visitante"])

        casa["J"] += 1
        fora["J"] += 1
        casa["GP"] += gc
        casa["GC"] += gf
        fora["GP"] += gf
        fora["GC"] += gc

        if gc > gf:
            casa["V"] += 1
            casa["Pontos"] += 3
            fora["D"] += 1
        elif gc < gf:
            fora["V"] += 1
            fora["Pontos"] += 3
            casa["D"] += 1
        else:
            casa["E"] += 1
            fora["E"] += 1
            casa["Pontos"] += 1
            fora["Pontos"] += 1

    tabela = pd.DataFrame(list(times.values()))
    if tabela.empty:
        return tabela

    tabela["SG"] = tabela["GP"] - tabela["GC"]
    tabela = tabela.sort_values(
        ["Pontos", "V", "SG", "GP"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    tabela.insert(0, "Pos.", range(1, len(tabela) + 1))
    return tabela


# =========================================================
# 5. ESTILO, NAVEGAÇÃO E FILTROS
# =========================================================

aplicar_estilo()

st.sidebar.markdown("## ⚽ Brasileirão")
st.sidebar.caption("CENTRAL DE ANÁLISES")
st.sidebar.divider()

pagina = st.sidebar.radio(
    "Navegação",
    ["Visão geral", "Gols", "Classificação", "Partidas"],
    format_func=lambda item: {
        "Visão geral": "◈  Visão geral",
        "Gols": "⚽  Gols",
        "Classificação": "🏆  Classificação",
        "Partidas": "▤  Partidas",
    }[item],
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.markdown("### Filtros")

temporada = st.sidebar.selectbox("Temporada", TEMPORADAS, index=0)
token = st.secrets.get("FOOTBALL_DATA_TOKEN", "")

if st.sidebar.button("↻  Atualizar dados", use_container_width=True):
    carregar_partidas.clear()
    st.rerun()

st.sidebar.markdown(
    '<p class="filter-note">Os filtros de temporada e time são aplicados '
    'às páginas e aos gráficos.</p>',
    unsafe_allow_html=True,
)

if not token:
    st.error(
        "Token não encontrado. Configure FOOTBALL_DATA_TOKEN em "
        "Settings → Secrets nas configurações do Streamlit."
    )
    st.stop()

try:
    with st.spinner("Buscando partidas..."):
        dados = carregar_partidas(temporada, token)
except requests.exceptions.Timeout:
    st.error("A consulta excedeu o tempo limite. Tente novamente.")
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

if dados.empty:
    st.warning(
        f"A API não retornou partidas para {temporada}. "
        "Confira a cobertura da temporada no seu plano."
    )
    st.stop()

times_disponiveis = sorted(
    set(dados["Mandante"].dropna()) | set(dados["Visitante"].dropna())
)
time_selecionado = st.sidebar.selectbox(
    "Time",
    ["Todos os times"] + times_disponiveis,
)

df = dados.copy()
if time_selecionado != "Todos os times":
    df = df[
        (df["Mandante"] == time_selecionado)
        | (df["Visitante"] == time_selecionado)
    ].copy()

jogos = preparar_jogos_finalizados(df)

# Cabeçalho do conteúdo: compacto para aproveitar a área visível.
st.markdown(
    f"""
    <div class="hero">
        <div class="hero-eyebrow">Painel de dados · Série A</div>
        <div class="hero-title">Brasileirão Analytics</div>
        <div class="hero-subtitle">
            Temporada {temporada} &nbsp;·&nbsp;
            {time_selecionado}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 6. PÁGINA: VISÃO GERAL
# =========================================================

if pagina == "Visão geral":
    titulo_secao("Resumo da temporada", "Indicadores calculados com as partidas disponíveis.")
    mostrar_indicadores(df, jogos)

    if jogos.empty:
        st.info("Ainda não há partidas finalizadas para exibir gráficos.")
    else:
        col1, col2 = st.columns([1, 1.25], gap="large")

        with col1:
            resultados = criar_resultados(jogos)
            fig = px.pie(
                resultados,
                names="Resultado",
                values="Quantidade",
                hole=0.68,
                title="Resultados das partidas",
                color="Resultado",
                color_discrete_map={
                    "Vitória do mandante": CORES["verde"],
                    "Empate": CORES["amarelo"],
                    "Vitória do visitante": CORES["azul"],
                },
            )
            fig.update_traces(
                textposition="inside",
                textinfo="percent",
                textfont=dict(color="#FFFFFF", size=12),
                marker=dict(line=dict(color=CORES["painel"], width=3)),
                hovertemplate="%{label}<br>Jogos: %{value}<br>%{percent}<extra></extra>",
            )
            st.plotly_chart(estilizar_grafico(fig), use_container_width=True)

        with col2:
            ranking = criar_ranking_gols(jogos).sort_values("Gols", ascending=False).head(10)
            ranking = ranking.sort_values("Gols", ascending=True)
            fig = px.bar(
                ranking,
                x="Gols",
                y="Time",
                orientation="h",
                text="Gols",
                title="Clubes com mais gols nos jogos filtrados",
                color="Gols",
                color_continuous_scale=["#1B6658", CORES["verde"]],
            )
            fig.update_traces(
                textposition="outside",
                textfont=dict(color=CORES["texto"]),
                marker_line_width=0,
                hovertemplate="%{y}<br>Gols: %{x}<extra></extra>",
            )
            fig.update_layout(
                coloraxis_showscale=False,
                yaxis=dict(categoryorder="total ascending"),
            )
            st.plotly_chart(estilizar_grafico(fig, 400), use_container_width=True)


# =========================================================
# 7. PÁGINA: GOLS
# =========================================================

elif pagina == "Gols":
    titulo_secao("Análise de gols", "Compare gols por mando, rodada e clube.")
    mostrar_indicadores(df, jogos)

    if jogos.empty:
        st.info("Não existem jogos finalizados para os filtros selecionados.")
    else:
        col1, col2 = st.columns(2, gap="large")

        with col1:
            gols_local = pd.DataFrame({
                "Local": ["Mandante", "Visitante"],
                "Gols": [
                    int(jogos["Gols mandante"].sum()),
                    int(jogos["Gols visitante"].sum()),
                ],
            })
            fig = px.bar(
                gols_local,
                x="Local",
                y="Gols",
                color="Local",
                text="Gols",
                title="Gols por mando de campo",
                color_discrete_map={
                    "Mandante": CORES["verde"],
                    "Visitante": CORES["azul"],
                },
            )
            fig.update_traces(
                textposition="outside",
                textfont=dict(color=CORES["texto"]),
                marker_line_width=0,
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(estilizar_grafico(fig), use_container_width=True)

        with col2:
            por_rodada = (
                jogos.dropna(subset=["Rodada"])
                .groupby("Rodada")
                .agg(Gols=("Total de gols", "sum"), Jogos=("ID", "count"))
                .reset_index()
                .sort_values("Rodada")
            )
            if not por_rodada.empty:
                por_rodada["Média por jogo"] = por_rodada["Gols"] / por_rodada["Jogos"]
                fig = go.Figure()
                fig.add_bar(
                    x=por_rodada["Rodada"],
                    y=por_rodada["Gols"],
                    name="Total de gols",
                    marker_color=CORES["azul"],
                    hovertemplate="Rodada %{x}<br>Gols: %{y}<extra></extra>",
                )
                fig.add_scatter(
                    x=por_rodada["Rodada"],
                    y=por_rodada["Média por jogo"],
                    name="Média por jogo",
                    mode="lines+markers",
                    line=dict(color=CORES["amarelo"], width=3),
                    marker=dict(size=6),
                    yaxis="y2",
                    hovertemplate="Rodada %{x}<br>Média: %{y:.2f}<extra></extra>",
                )
                fig.update_layout(
                    title="Gols por rodada",
                    xaxis_title="Rodada",
                    yaxis=dict(title="Total de gols"),
                    yaxis2=dict(
                        title="Média por jogo",
                        overlaying="y",
                        side="right",
                        showgrid=False,
                        tickfont=dict(color=CORES["texto_secundario"]),
                        title_font=dict(color=CORES["texto_secundario"]),
                    ),
                )
                st.plotly_chart(estilizar_grafico(fig), use_container_width=True)

        ranking = criar_ranking_gols(jogos).sort_values("Gols", ascending=True)
        fig = px.bar(
            ranking,
            x="Gols",
            y="Time",
            orientation="h",
            text="Gols",
            title="Gols por clube",
            color="Gols",
            color_continuous_scale=["#1B6658", CORES["verde"]],
        )
        fig.update_traces(
            textposition="outside",
            textfont=dict(color=CORES["texto"]),
            marker_line_width=0,
        )
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(
            estilizar_grafico(fig, max(380, len(ranking) * 28)),
            use_container_width=True,
        )


# =========================================================
# 8. PÁGINA: CLASSIFICAÇÃO
# =========================================================

elif pagina == "Classificação":
    titulo_secao(
        "Classificação calculada",
        "Pontos, vitórias e saldo calculados a partir dos jogos retornados pela API.",
    )
    tabela = criar_classificacao(jogos)

    if tabela.empty:
        st.info("Ainda não existem resultados suficientes para montar a classificação.")
    else:
        if time_selecionado != "Todos os times":
            tabela = tabela[tabela["Time"] == time_selecionado]

        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Pos.": st.column_config.NumberColumn("Pos.", format="%d"),
                "Pontos": st.column_config.NumberColumn("Pontos", format="%d"),
                "GP": st.column_config.NumberColumn("Gols pró", format="%d"),
                "GC": st.column_config.NumberColumn("Gols contra", format="%d"),
                "SG": st.column_config.NumberColumn("Saldo", format="%d"),
            },
        )
        st.caption(
            "Esta classificação é estimada a partir dos jogos disponíveis e não substitui "
            "a tabela oficial. Se um clube estiver selecionado, somente ele será exibido."
        )


# =========================================================
# 9. PÁGINA: PARTIDAS
# =========================================================

elif pagina == "Partidas":
    titulo_secao("Lista de partidas", "Pesquise clubes e exporte os resultados em CSV.")

    busca = st.text_input(
        "Buscar por clube",
        placeholder="Ex.: Flamengo, Palmeiras...",
    )

    tabela = df.copy()
    if busca.strip():
        termo = busca.strip()
        tabela = tabela[
            tabela["Mandante"].str.contains(termo, case=False, na=False)
            | tabela["Visitante"].str.contains(termo, case=False, na=False)
        ]

    tabela = tabela.sort_values(["Rodada", "Data"], na_position="last")

    def formatar_placar(linha):
        casa = linha["Gols mandante"]
        fora = linha["Gols visitante"]
        if pd.notna(casa) and pd.notna(fora):
            return f"{int(casa)} × {int(fora)}"
        return "—"

    tabela["Placar"] = tabela.apply(formatar_placar, axis=1)
    tabela["Data e hora"] = pd.to_datetime(
        tabela["Data"], errors="coerce"
    ).dt.strftime("%d/%m/%Y %H:%M")
    tabela["Rodada"] = tabela["Rodada"].apply(
        lambda valor: str(int(valor)) if pd.notna(valor) else "—"
    )

    exibicao = tabela[
        ["Rodada", "Data e hora", "Mandante", "Placar", "Visitante", "Status"]
    ]

    st.caption(f"{len(exibicao)} partida(s) encontrada(s).")
    st.dataframe(exibicao, use_container_width=True, hide_index=True)

    csv = exibicao.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        "⬇️ Exportar partidas CSV",
        data=csv,
        file_name=f"brasileirao_{temporada}.csv",
        mime="text/csv",
    )


# =========================================================
# 10. RODAPÉ
# =========================================================

st.divider()
st.caption(
    "Fonte: football-data.org · Cache de 30 minutos. "
    "Use “Atualizar dados” para solicitar uma nova consulta."
)
