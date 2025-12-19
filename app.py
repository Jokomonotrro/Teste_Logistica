import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------
# CONFIGURAÇÃO INICIAL
# -----------------------------
st.set_page_config(
    page_title="Dashboard Gerencial - Loja de Materiais",
    layout="wide"
)

st.title("Dashboard Gerencial - Loja de Material de Construção")

# -----------------------------
# LEITURA DOS DADOS
# -----------------------------
@st.cache_data
def carregar_dados():
    df = pd.read_csv("tudo.csv", encoding="latin1", sep=",")
    
    df['criado_em'] = pd.to_datetime(df['criado_em'])
    df['atualizado_em'] = pd.to_datetime(df['atualizado_em'])
    df['quantidade'] = pd.to_numeric(df['quantidade'])
    df['preço_y'] = pd.to_numeric(df['preço_y'])
    df['preço_x'] = pd.to_numeric(df['preço_x'])
    
    df['faturamento'] = df['quantidade'] * df['preço_y']
    return df

df = carregar_dados()

# -----------------------------
# FILTROS LATERAIS
# -----------------------------
st.sidebar.header("Filtros")

produtos = df['produto'].unique()
produto_selecionado = st.sidebar.selectbox(
    "Selecione um produto",
    options=produtos
)

data_inicio = st.sidebar.date_input(
    "Data inicial",
    df['criado_em'].min().date()
)

data_fim = st.sidebar.date_input(
    "Data final",
    df['criado_em'].max().date()
)

df_filtrado = df[
    (df['produto'] == produto_selecionado) &
    (df['criado_em'].dt.date >= data_inicio) &
    (df['criado_em'].dt.date <= data_fim)
]

# -----------------------------
# KPIs PRINCIPAIS
# -----------------------------
col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Quantidade Vendida",
    int(df_filtrado['quantidade'].sum())
)

col2.metric(
    "Faturamento (R$)",
    f"{df_filtrado['faturamento'].sum():,.2f}"
)

col3.metric(
    "Preço Médio (R$)",
    f"{df_filtrado['preço_y'].mean():,.2f}"
)

col4.metric(
    "Total de Vendas",
    df_filtrado['id_da_venda'].nunique()
)

# -----------------------------
# GRÁFICO: EVOLUÇÃO DE VENDAS
# -----------------------------
st.subheader("Evolução de Vendas no Tempo")

df_tempo = (
    df_filtrado
    .groupby(df_filtrado['criado_em'].dt.date)
    .agg({'quantidade': 'sum', 'faturamento': 'sum'})
    .reset_index()
)

fig_tempo = px.line(
    df_tempo,
    x='criado_em',
    y='quantidade',
    title="Quantidade Vendida por Dia"
)

st.plotly_chart(fig_tempo, use_container_width=True)

# -----------------------------
# RANKING DE PRODUTOS
# -----------------------------
st.subheader("Top 10 Produtos por Faturamento")

ranking = (
    df.groupby('produto')
    .agg({
        'quantidade': 'sum',
        'faturamento': 'sum'
    })
    .sort_values('faturamento', ascending=False)
    .head(10)
    .reset_index()
)

fig_rank = px.bar(
    ranking,
    x='produto',
    y='faturamento',
    title="Top 10 Produtos"
)

st.plotly_chart(fig_rank, use_container_width=True)

# -----------------------------
# TABELA DETALHADA
# -----------------------------
st.subheader("Dados Detalhados")

st.dataframe(
    df_filtrado[['nome', 'produto', 'quantidade', 'preço_y', 'faturamento', 'criado_em']],
    use_container_width=True
)

# -----------------------------
# DOWNLOAD DOS DADOS FILTRADOS
# -----------------------------
st.download_button(
    label="Baixar dados filtrados (CSV)",
    data=df_filtrado.to_csv(index=False).encode('utf-8'),
    file_name="dados_filtrados.csv",
    mime="text/csv"
)
