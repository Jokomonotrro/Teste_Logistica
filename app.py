import streamlit as st
import pandas as pd
import plotly.express as px
import os

# =============================
# CONFIGURAÇÃO
# =============================
st.set_page_config(page_title="Dashboard Gerencial", layout="wide")

# =============================
# USUÁRIOS
# =============================
USUARIOS = {
    "log2025": {"senha": "material123", "perfil": "admin"},
    "nxjl": {"senha": "testejl123", "perfil": "leitura"}
}

# =============================
# LOGIN
# =============================
def tela_login():
    st.markdown("## Bem-vindo")
    login = st.text_input("Login")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if login in USUARIOS and USUARIOS[login]["senha"] == senha:
            st.session_state["auth"] = True
            st.session_state["usuario"] = login
            st.session_state["perfil"] = USUARIOS[login]["perfil"]
            st.rerun()
        else:
            st.error("Login ou senha inválidos")

if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    tela_login()
    st.stop()

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# =============================
# ESCOLHA DA FONTE DE DADOS
# =============================
st.sidebar.header("Fonte de Dados")

opcao = st.sidebar.radio(
    "Como deseja carregar os dados?",
    ["Usar arquivo do repositório", "Enviar novo arquivo"]
)

arquivo = None

if opcao == "Usar arquivo do repositório":
    arquivos_repo = [
        f for f in os.listdir(".")
        if f.lower().endswith((".csv", ".xlsx", ".xls"))
    ]

    if not arquivos_repo:
        st.error("Nenhum arquivo compatível encontrado no repositório.")
        st.stop()

    nome_arquivo = st.sidebar.selectbox(
        "Arquivos disponíveis",
        arquivos_repo
    )

    arquivo = nome_arquivo

else:
    arquivo = st.sidebar.file_uploader(
        "Upload (.csv, .xls, .xlsx)",
        type=["csv", "xls", "xlsx"]
    )

if not arquivo:
    st.warning("Selecione ou envie um arquivo para continuar.")
    st.stop()

# =============================
# LEITURA ROBUSTA
# =============================
@st.cache_data
def carregar_dados(fonte):
    if isinstance(fonte, str):
        if fonte.endswith(".csv"):
            try:
                df = pd.read_csv(fonte, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(fonte, encoding="latin1")
        else:
            df = pd.read_excel(fonte)
    else:
        if fonte.name.endswith(".csv"):
            try:
                df = pd.read_csv(fonte, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(fonte, encoding="latin1")
        else:
            df = pd.read_excel(fonte)

    # Normalização de colunas
    df.columns = (
        df.columns.str.strip().str.lower()
        .str.replace(" ", "_").str.replace("-", "_")
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
    )

    mapa = {
        "criado_em": ["criado_em", "data", "data_criacao"],
        "produto": ["produto", "item", "descricao"],
        "quantidade": ["quantidade", "qtd", "qtde"],
        "preco_y": ["preco_y", "preco_venda", "valor_venda"],
        "preco_x": ["preco_x", "preco_custo", "valor_custo"]
    }

    for padrao, opcoes in mapa.items():
        for o in opcoes:
            if o in df.columns:
                df.rename(columns={o: padrao}, inplace=True)
                break

    obrigatorias = ["criado_em", "produto", "quantidade", "preco_y"]
    faltando = [c for c in obrigatorias if c not in df.columns]

    if faltando:
        st.error(f"Colunas obrigatórias ausentes: {faltando}")
        st.stop()

    df["criado_em"] = pd.to_datetime(df["criado_em"], dayfirst=True, errors="coerce")
    df["quantidade"] = pd.to_numeric(df["quantidade"], errors="coerce")
    df["preco_y"] = pd.to_numeric(df["preco_y"], errors="coerce")

    if "preco_x" in df.columns:
        df["preco_x"] = pd.to_numeric(df["preco_x"], errors="coerce")
        df["margem"] = (df["preco_y"] - df["preco_x"]) * df["quantidade"]
    else:
        df["margem"] = 0

    df["faturamento"] = df["quantidade"] * df["preco_y"]
    return df

df = carregar_dados(arquivo)

# =============================
# FILTRO DE PRODUTO
# =============================
produto = st.sidebar.selectbox("Produto", df["produto"].unique())
df_f = df[df["produto"] == produto]

# =============================
# KPIs
# =============================
c1, c2, c3 = st.columns(3)
c1.metric("Quantidade", int(df_f["quantidade"].sum()))
c2.metric("Faturamento", f"R$ {df_f['faturamento'].sum():,.2f}")
c3.metric("Preço Médio", f"R$ {df_f['preco_y'].mean():,.2f}")

if st.session_state["perfil"] == "admin":
    st.metric("Margem Total", f"R$ {df_f['margem'].sum():,.2f}")

# =============================
# SÉRIE TEMPORAL
# =============================
df_tempo = (
    df_f.groupby(df_f["criado_em"].dt.date)
    .agg({"quantidade": "sum"})
    .reset_index()
)

st.plotly_chart(
    px.line(df_tempo, x="criado_em", y="quantidade"),
    use_container_width=True
)

# =============================
# PREVISÃO – MÉDIA MÓVEL
# =============================
st.subheader("Previsão por Média Móvel")
n = st.selectbox("Período n", [2, 3, 4, 5, 7])
df_tempo["media_movel"] = df_tempo["quantidade"].rolling(n).mean()

st.plotly_chart(
    px.line(df_tempo, x="criado_em", y=["quantidade", "media_movel"]),
    use_container_width=True
)

# =============================
# CURVA ABC (ADMIN)
# =============================
if st.session_state["perfil"] == "admin":
    st.subheader("Curva ABC")

    abc = (
        df.groupby("produto")["faturamento"]
        .sum().sort_values(ascending=False)
        .reset_index()
    )

    abc["acumulado"] = abc["faturamento"].cumsum() / abc["faturamento"].sum()

    abc["classe"] = abc["acumulado"].apply(
        lambda x: "A" if x <= 0.8 else ("B" if x <= 0.95 else "C")
    )

    st.plotly_chart(
        px.bar(abc, x="produto", y="faturamento", color="classe"),
        use_container_width=True
    )

# =============================
# TABELA FINAL
# =============================
df_f["criado_em"] = df_f["criado_em"].dt.strftime("%d/%m/%Y")

st.dataframe(
    df_f[["produto", "quantidade", "preco_y", "faturamento", "criado_em"]],
    use_container_width=True
)
