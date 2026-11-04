import pandas as pd
import streamlit as st

st.set_page_config(page_title="Painel de Incidentes", layout="wide")

ARQUIVO_DADOS = "dados_incidentes.csv"


@st.cache_data
def carregar_dados():
    df = pd.read_csv(ARQUIVO_DADOS)

    # Todas as colunas de data voltam como texto do CSV
    for coluna in ["opened_at", "resolved_at", "sla_due"]:
        df[coluna] = pd.to_datetime(df[coluna], errors="coerce")

    # Colunas derivadas calculadas uma única vez
    df["data_abertura"] = df["opened_at"].dt.date
    df["hora_abertura"] = df["opened_at"].dt.hour
    df["sla_cumprido"] = df["resolved_at"] <= df["sla_due"]
    return df


def mostrar_tabela(df):
    try:
        st.dataframe(df, width="stretch")
    except TypeError:  # versões antigas do Streamlit
        st.dataframe(df, use_container_width=True)


try:
    df = carregar_dados()
except FileNotFoundError:
    st.error(
        f"Arquivo '{ARQUIVO_DADOS}' não encontrado. "
        "Rode `python gerar_dados.py` (ou `--sintetico`) primeiro."
    )
    st.stop()

st.title("📊 Painel de Incidentes — ServiceNow")
st.markdown("Visão geral das métricas de suporte e SLA.")

if "sintetico" in df.columns and df["sintetico"].any():
    st.info(
        "ℹ️ Tempos de resolução e SLA (48h) **simulados**: o PDI possui poucos "
        "incidentes resolvidos. Veja a seção 'Decisões e limitações' no README."
    )

# ---------- Filtros ----------
st.sidebar.header("Filtros")

categorias = ["Todas"] + sorted(df["category"].dropna().unique().tolist())
categoria = st.sidebar.selectbox("Categoria:", categorias)

prioridades = ["Todas"] + sorted(df["priority"].dropna().unique().tolist())
prioridade = st.sidebar.selectbox("Prioridade:", prioridades)

data_min, data_max = df["data_abertura"].min(), df["data_abertura"].max()
periodo = st.sidebar.date_input(
    "Período de abertura:",
    value=(data_min, data_max),
    min_value=data_min,
    max_value=data_max,
)
if not isinstance(periodo, (tuple, list)) or len(periodo) != 2:
    st.sidebar.info("Selecione a data inicial e a final.")
    st.stop()
inicio, fim = periodo

filtro = (df["data_abertura"] >= inicio) & (df["data_abertura"] <= fim)
if categoria != "Todas":
    filtro &= df["category"] == categoria
if prioridade != "Todas":
    filtro &= df["priority"] == prioridade

df_filtrado = df[filtro].copy()

if df_filtrado.empty:
    st.warning("Nenhum incidente encontrado com esses filtros.")
    st.stop()

# ---------- Métricas ----------
df_resolvidos = df_filtrado.dropna(subset=["tempo_resolucao_horas"])
df_sla = df_resolvidos.dropna(subset=["sla_due", "resolved_at"])

mttr = df_resolvidos["tempo_resolucao_horas"].mean() if not df_resolvidos.empty else 0
taxa_sla = df_sla["sla_cumprido"].mean() * 100 if not df_sla.empty else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total de Incidentes", len(df_filtrado))
col2.metric("MTTR Médio", f"{mttr:.1f} horas")
col3.metric("Cumprimento de SLA", f"{taxa_sla:.1f}%")

st.divider()

# ---------- Gráficos ----------
col_esq, col_dir = st.columns(2)

with col_esq:
    st.subheader("Incidentes por Categoria")
    st.bar_chart(df_filtrado["category"].value_counts())

with col_dir:
    st.subheader("Incidentes ao Longo do Tempo")
    por_dia = (
        df_filtrado.set_index("opened_at").resample("D").size()  # dias sem incidente = 0
    )
    st.line_chart(por_dia)

col_esq2, col_dir2 = st.columns(2)

with col_esq2:
    st.subheader("Horários de Pico (abertura)")
    por_hora = df_filtrado["hora_abertura"].value_counts().reindex(range(24), fill_value=0)
    st.bar_chart(por_hora)

with col_dir2:
    st.subheader("Cumprimento de SLA por Categoria (%)")
    if df_sla.empty:
        st.caption("Sem incidentes resolvidos com SLA para este filtro.")
    else:
        sla_categoria = df_sla.groupby("category")["sla_cumprido"].mean() * 100
        st.bar_chart(sla_categoria)

# ---------- Tabela ----------
st.subheader("Detalhamento dos Incidentes")
mostrar_tabela(
    df_filtrado[
        [
            "number",
            "category",
            "priority",
            "opened_at",
            "resolved_at",
            "tempo_resolucao_horas",
        ]
    ]
)