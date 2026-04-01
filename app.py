import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import pdfplumber
import re
from PIL import Image
from pathlib import Path

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Tramontina - Gestor de Pedidos", layout="centered")

# Inicializa a conexão
conn = st.connection("gsheets", type=GSheetsConnection)

# Função de carregamento sem cache para testar a conexão limpa
def carregar_aba(nome_da_aba):
    # IMPORTANTE: Não passamos a URL aqui, ele pega dos Secrets automaticamente
    return conn.read(worksheet=nome_da_aba)

# --- INTERFACE ---
BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "logo.png" # Ajuste se estiver em /infos/logo.png
if LOGO_PATH.exists():
    _, col_img, _ = st.columns([1, 1, 1])
    col_img.image(Image.open(str(LOGO_PATH)), width=150)

st.markdown("<h1 style='text-align: center;'>Leitor de Pedidos Automático</h1>", unsafe_allow_html=True)

# Teste de Conexão Imediato
try:
    # Tenta ler apenas a primeira aba para validar
    df_teste = carregar_aba("fabricas")
    
    menu = st.tabs(["📄 Processar Pedido", "⚙️ Gerenciar Base"])

    with menu[0]:
        st.subheader("Processamento")
        df_cli = carregar_aba("clientes")
        sel_cliente = st.selectbox("Selecione o Cliente", df_cli["cliente"].unique())
        arquivo = st.file_uploader("Suba o pedido em PDF", type="pdf")
        
        if st.button("🚀 Iniciar Leitura", use_container_width=True, type="primary"):
            if arquivo:
                # Sua lógica de extração aqui
                st.success("Conectado e pronto para leitura!")

    with menu[1]:
        st.subheader("Atualizar Dados")
        escolha = st.radio("Escolha a base:", ["fabricas", "clientes", "embalagem"], horizontal=True)
        df_atual = carregar_aba(escolha)
        st.dataframe(df_atual, use_container_width=True)
        
        with st.expander("➕ Adicionar Novo Registro"):
            with st.form("form_add"):
                novos_dados = {col: st.text_input(col) for col in df_atual.columns}
                if st.form_submit_button("Salvar no Google Sheets"):
                    df_final = pd.concat([df_atual, pd.DataFrame([novos_dados])], ignore_index=True)
                    conn.update(worksheet=escolha, data=df_final)
                    st.cache_data.clear()
                    st.rerun()

except Exception as e:
    st.error("⚠️ Erro Crítico de Acesso")
    st.info("Verifique se o link nos Secrets termina exatamente em 'edit?usp=sharing' e se não há espaços antes ou depois das aspas.")
    st.warning(f"Detalhe técnico: {e}")
