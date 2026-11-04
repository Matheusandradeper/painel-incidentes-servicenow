import streamlit as st
import pandas as pd


st.set_page_config(page_title="Painel de Incidentes", layout="wide")


@st.cache_data
def carregar_dados():
    df = pd.read_csv('dados_incidentes.csv')
    # Converter datas que voltaram como texto no CSV
    df['opened_at'] = pd.to_datetime(df['opened_at'])
    return df

df = carregar_dados()


st.title("📊 Painel de Incidentes — ServiceNow")
st.markdown("Visão geral das métricas de suporte e SLA.")


st.sidebar.header("Filtros")
# Cria uma lista com as categorias únicas e adiciona a opção "Todas"
lista_categorias = ["Todas"] + df['category'].dropna().unique().tolist()
categoria_selecionada = st.sidebar.selectbox("Selecione a Categoria:", lista_categorias)


if categoria_selecionada != "Todas":
    df_filtrado = df[df['category'] == categoria_selecionada]
else:
    df_filtrado = df


df_resolvidos = df_filtrado.dropna(subset=['tempo_resolucao_horas'])

if not df_resolvidos.empty:
    mttr = df_resolvidos['tempo_resolucao_horas'].mean()
    
    df_sla = df_resolvidos.dropna(subset=['sla_due'])
    df_sla['sla_cumprido'] = df_sla['resolved_at'] <= df_sla['sla_due']
    taxa_sla = (df_sla['sla_cumprido'].sum() / len(df_sla)) * 100 if len(df_sla) > 0 else 0
else:
    mttr = 0
    taxa_sla = 0


col1, col2, col3 = st.columns(3)
col1.metric("Total de Incidentes", len(df_filtrado))
col2.metric("MTTR Médio", f"{mttr:.1f} horas")
col3.metric("Cumprimento de SLA", f"{taxa_sla:.1f}%")

st.divider() # Linha divisória visual


col_esquerda, col_direita = st.columns(2)

with col_esquerda:
    st.subheader("Incidentes por Categoria")
    # Conta quantos incidentes tem em cada categoria e plota
    dados_categoria = df_filtrado['category'].value_counts()
    st.bar_chart(dados_categoria)

with col_direita:
    st.subheader("Incidentes ao Longo do Tempo")
    # Agrupa os incidentes por data de abertura (apenas o dia) e conta
    df_filtrado['data_abertura'] = df_filtrado['opened_at'].dt.date
    dados_tempo = df_filtrado.groupby('data_abertura').size()
    st.line_chart(dados_tempo)


st.subheader("Detalhamento dos Incidentes")
st.dataframe(df_filtrado[['number', 'category', 'opened_at', 'resolved_at', 'tempo_resolucao_horas']], use_container_width=True)