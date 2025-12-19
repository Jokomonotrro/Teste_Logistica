import streamlit as st
import pandas as pd
import plotly.express as px

# =============================
# CONFIGURAÇÃO
# =============================
st.set_page_config(page_title="Dashboard Gerencial", layout="wide")

# =============================
# USUÁRIOS E PERFIS
# =============================
USUARIOS = {
    "log2025": {"senha": "material123", "perfil": "admin"},
    "nxjl": {"senha": "testejl123", "perfil": "admin"}
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

# =============================
# LOGOUT
# =============================
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# =============================
# UPLOAD
# =============================
arquivo = st.sidebar.file_uploader(
    "Importar base (.csv, .xls, .xlsx)",
    type=["csv", "xls", "xlsx"]
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

    df['criado_em'] = pd.to_datetime(df['criado_em'], dayfirst=True, errors="coerce")
    df['quantidade'] = pd.to_numeric(df['quantidade'], errors="coerce")
    df['preço_y'] = pd.to_numeric(df['preço_y'], errors="coerce")
    df['preço_x'] = pd.to_numeric(df['preço_x'], errors="coerce")

    df['faturamento'] = df['quantidade'] * df['preço_y']
    df['margem'] = (df['preço_y'] - df['preço_x']) * df['quantidade']
    return df

if not arquivo:
    st.warning("Importe um arquivo para continuar")
    st.stop()

df = carregar_dados(arquivo)

# =============================
# FILTROS
# =============================
produto = st.sidebar.selectbox("Produto", df['produto'].unique())

df_f = df[df['produto'] == produto]

# =============================
# KPIs
# =============================
c1, c2, c3 = st.columns(3)
c1.metric("Quantidade", int(df_f['quantidade'].sum()))
c2.metric("Faturamento", f"R$ {df_f['faturamento'].sum():,.2f}")
c3.metric("Preço Médio", f"R$ {df_f['preço_y'].mean():,.2f}")

# =============================
# MARGEM (SÓ ADMIN)
# =============================
if st.session_state["perfil"] == "admin":
    st.metric("Margem Total", f"R$ {df_f['margem'].sum():,.2f}")

# =============================
# VENDAS NO TEMPO
# =============================
df_tempo = (
    df_f.groupby(df_f['criado_em'].dt.date)
    .agg({'quantidade': 'sum'})
    .reset_index()
)

fig_vendas = px.line(df_tempo, x='criado_em', y='quantidade')
st.plotly_chart(fig_vendas, use_container_width=True)

# =============================
# PREVISÃO – MÉDIA MÓVEL
# =============================
st.subheader("Previsão de Vendas (Média Móvel)")

n = st.selectbox("Escolha o período da média móvel (n)", [2, 3, 4, 5, 7])

df_tempo['media_movel'] = df_tempo['quantidade'].rolling(n).mean()

fig_prev = px.line(
    df_tempo,
    x='criado_em',
    y=['quantidade', 'media_movel'],
    labels={"value": "Quantidade"}
)

st.plotly_chart(fig_prev, use_container_width=True)

# =============================
# CURVA ABC (SÓ ADMIN)
# =============================
if st.session_state["perfil"] == "admin":
    st.subheader("Curva ABC")

    abc = (
        df.groupby('produto')['faturamento']
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    abc['perc'] = abc['faturamento'].cumsum() / abc['faturamento'].sum()

    def classe(p):
        if p <= 0.8:
            return 'A'
        elif p <= 0.95:
            return 'B'
        else:
            return 'C'

    abc['classe'] = abc['perc'].apply(classe)

    fig_abc = px.bar(abc, x='produto', y='faturamento', color='classe')
    st.plotly_chart(fig_abc, use_container_width=True)

# =============================
# TABELA FINAL
# =============================
df_f['criado_em'] = df_f['criado_em'].dt.strftime("%d/%m/%Y")

st.dataframe(
    df_f[['nome', 'produto', 'quantidade', 'preço_y', 'faturamento', 'criado_em']],
    use_container_width=True
)
