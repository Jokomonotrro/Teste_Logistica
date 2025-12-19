import streamlit as st
import pandas as pd
import plotly.express as px

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="Dashboard Gerencial - Loja de Materiais",
    layout="wide"
)

# =============================
# LOGIN FIXO (APENAS VOCÊ CADASTRA)
# =============================
USUARIOS = {
    "log2025": "material123",
    "nxjl": "testejl123"
}

def tela_login():
    st.markdown("## Bem-vindo")
    st.markdown("### Acesso ao Dashboard Gerencial")

    login = st.text_input("Login")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if login in USUARIOS and USUARIOS[login] == senha:
            st.session_state["autenticado"] = True
            st.session_state["usuario"] = login
            st.rerun()
        else:
            st.error("Login ou senha inválidos")

# =============================
# CONTROLE DE SESSÃO
# =============================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    tela_login()
    st.stop()

# =============================
# TELA PRINCIPAL
# =============================
st.success(f"Usuário autenticado: {st.session_state['usuario']}")
st.title("Dashboard Gerencial - Loja de Material de Construção")

# =============================
# UPLOAD DO ARQUIVO
# =============================
st.sidebar.header("Importação de Dados")

arquivo = st.sidebar.file_uploader(
    "Importe a base (.csv, .xlsx, .xls)",
    type=["csv", "xlsx", "xls"]
)

@st.cache_data
def carregar_dados(upload):
    if upload.name.endswith(".csv"):
        try:
            df = pd.read_csv(upload, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(upload, encoding="latin1")
    else:
        df = pd.read_excel(upload)

    # Conversões
    df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce', dayfirst=True)
    df['atualizado_em'] = pd.to_datetime(df['atualizado_em'], errors='coerce', dayfirst=True)
    df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce')
    df['preço_y'] = pd.to_numeric(df['preço_y'], errors='coerce')
    df['preço_x'] = pd.to_numeric(df['preço_x'], errors='coerce')

    df['faturamento'] = df['quantidade'] * df['preço_y']
    return df

if not arquivo:
    st.warning("Importe um arquivo para iniciar o dashboard.")
    st.stop()

df = carregar_dados(arquivo)

# =============================
# FILTROS
# =============================
st.sidebar.header("Filtros")

produto_selecionado = st.sidebar.selectbox(
    "Produto",
    df['produto'].unique()
)

data_inicio = st.sidebar.date_input(
    "Data inicial",
    df['criado_em'].min()
)

data_fim = st.sidebar.date_input(
    "Data final",
    df['criado_em'].max()
)

df_filtrado = df[
    (df['produto'] == produto_selecionado) &
    (df['criado_em'].dt.date >= data_inicio) &
    (df['criado_em'].dt.date <= data_fim)
]

# =============================
# KPIs
# =============================
col1, col2, col3, col4 = st.columns(4)

col1.metric("Quantidade Vendida", int(df_filtrado['quantidade'].sum()))
col2.metric("Faturamento (R$)", f"{df_filtrado['faturamento'].sum():,.2f}")
col3.metric("Preço Médio (R$)", f"{df_filtrado['preço_y'].mean():,.2f}")
col4.metric("Total de Vendas", df_filtrado['id_da_venda'].nunique())

# =============================
# GRÁFICO DE VENDAS NO TEMPO
# =============================
st.subheader("Evolução de Vendas")

df_tempo = (
    df_filtrado
    .groupby(df_filtrado['criado_em'].dt.strftime("%d/%m/%Y"))
    .agg({'quantidade': 'sum'})
    .reset_index()
)

fig_tempo = px.line(
    df_tempo,
    x='criado_em',
    y='quantidade',
    title="Quantidade Vendida por Dia"
)

st.plotly_chart(fig_tempo, use_container_width=True)

# =============================
# RANKING DE PRODUTOS
# =============================
st.subheader("Top 10 Produtos por Faturamento")

ranking = (
    df.groupby('pr
