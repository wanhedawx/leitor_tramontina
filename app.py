import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import pdfplumber
import re
import io
from PIL import Image
from pathlib import Path

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Tramontina - Gestor de Pedidos", layout="centered")

# URL da sua Planilha do Google (deve estar com acesso 'Qualquer pessoa com o link')
# Dica: Na planilha, crie as abas: 'clientes', 'fabricas', 'embalagem'
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/15WpiV3mW0dE9PjXiZ6imU1kJcG3fqu2RMxiFPlb0RBY/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- CARREGAMENTO DE DADOS (Lê do Google) ---
@st.cache_data(ttl=15)
def carregar_base(aba):
    return conn.read(spreadsheet=URL_PLANILHA, worksheet=aba)

# --- FUNÇÃO PARA SALVAR (Grava no Google) ---
def salvar_item_google(aba, novo_df):
    df_atual = conn.read(spreadsheet=URL_PLANILHA, worksheet=aba)
    df_final = pd.concat([df_atual, novo_df], ignore_index=True)
    conn.update(spreadsheet=URL_PLANILHA, worksheet=aba, data=df_final)
    st.cache_data.clear()

# --- INTERFACE ---
# Logo centralizada
BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "infos" / "logo.png"
if LOGO_PATH.exists():
    _, col_img, _ = st.columns([1, 1, 1])
    col_img.image(Image.open(str(LOGO_PATH)), width=150)

st.markdown("<h1 style='text-align: center;'>Leitor de Pedidos Automático</h1>", unsafe_allow_html=True)

# Menu principal
menu = st.tabs(["📄 Processar Pedido", "📦 Gerenciar SKUs/Clientes", "🏭 Fábricas & Descontos"])

with menu[0]:
    # Lógica de processamento (Igual à anterior, mas usando carregar_base)
    st.subheader("Processamento")
    df_clientes = carregar_base("clientes")
    sel_cliente = st.selectbox("Selecione o Cliente", df_clientes["cliente"].unique())
    arquivo = st.file_uploader("Suba o pedido em PDF", type="pdf")
    
    if st.button("🚀 Iniciar Leitura", use_container_width=True):
        # ... (Sua lógica de extração aqui usando os dfs do Google)
        st.success("Pedido lido com sucesso!")

with menu[1]:
    st.subheader("Atualizar Base de Itens")
    
    # Opção 1: Adicionar um por um
    with st.expander("➕ Adicionar único item"):
        with st.form("add_individual"):
            n_sku = st.text_input("SKU")
            n_emb = st.number_input("Embalagem", min_value=1)
            if st.form_submit_button("Salvar no Banco"):
                novo = pd.DataFrame([{"sku": n_sku, "embalagem": n_emb}])
                salvar_item_google("embalagem", novo)
                st.success("Item gravado no Google Sheets!")

    # Opção 2: Importar arquivo (Substituir base)
    with st.expander("📤 Importar lista completa (Excel)"):
        up_file = st.file_uploader("Suba o novo Excel de itens", type="xlsx")
        if st.button("Substituir Base de SKUs"):
            if up_file:
                df_novo = pd.read_excel(up_file)
                conn.update(spreadsheet=URL_PLANILHA, worksheet="embalagem", data=df_novo)
                st.success("Base de SKUs atualizada com sucesso!")

with menu[2]:
    st.subheader("Fábricas e Regras de Desconto")
    df_fab = carregar_base("fabricas")
    st.write("Configuração atual no Google Sheets:")
    st.dataframe(df_fab, use_container_width=True)
    
    st.info("💡 Para alterar descontos ou fábricas em massa, você também pode editar direto no seu Google Sheets.")
