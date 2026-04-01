import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import pdfplumber
import re
from PIL import Image
from pathlib import Path

# Configuração
st.set_page_config(page_title="Leitor de Pedidos", layout="centered")

# Conexão automática (Ele lê o link direto dos Secrets que você salvou!)
conn = st.connection("gsheets", type=GSheetsConnection)

# Função para carregar as abas
@st.cache_data(ttl=10)
def carregar_dados(aba):
    return conn.read(worksheet=aba)

# Interface: Logo e Título
BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "logo.png"
if LOGO_PATH.exists():
    _, col_img, _ = st.columns([1, 1, 1])
    col_img.image(Image.open(str(LOGO_PATH)), width=150)

st.markdown("<h1 style='text-align: center;'>Leitor de Pedidos Automático</h1>", unsafe_allow_html=True)

# Abas do App
tab_proc, tab_gerencia = st.tabs(["📄 Processar Pedido", "⚙️ Gerenciar Base"])

with tab_proc:
    try:
        df_clientes = carregar_dados("clientes")
        df_fabricas = carregar_dados("fabricas")
        df_embalagem = carregar_dados("embalagem")
        
        sel_cliente = st.selectbox("Selecione o Cliente", df_clientes["cliente"].unique())
        arquivo_pdf = st.file_uploader("Suba o pedido em PDF", type="pdf")

        if st.button("🚀 Iniciar Leitura", type="primary"):
            if arquivo_pdf:
                with pdfplumber.open(arquivo_pdf) as pdf:
                    texto = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                
                # Exemplo de lógica de cruzamento
                # 1. Acha fábrica pelo CNPJ no texto e pega o DESCONTO e ORIGEM
                # 2. Acha SKU no texto e cruza com a aba EMBALAGEM
                st.success("Dados lidos! Cruzando com Google Sheets...")
                # (Aqui entra sua lógica de RE.FINDALL conforme conversamos antes)
                
    except Exception as e:
        st.error(f"Erro de conexão: Verifique se os nomes das abas na planilha estão corretos (clientes, fabricas, embalagem).")

with tab_gerencia:
    st.subheader("Atualizar Informações")
    # Menu vertical para o cliente adicionar itens
    opcao = st.radio("Selecione a base para editar:", ["embalagem", "fabricas", "clientes"])
    df_atual = carregar_dados(opcao)
    
    st.write(f"Dados atuais em: **{opcao}**")
    st.dataframe(df_atual, use_container_width=True)

    with st.expander(f"➕ Adicionar novo registro em {opcao}"):
        with st.form("novo_dado"):
            campos = {col: st.text_input(f"Informe {col}") for col in df_atual.columns}
            if st.form_submit_button("Salvar no Google Sheets"):
                # Adiciona e faz o upload
                novo_df = pd.concat([df_atual, pd.DataFrame([campos])], ignore_index=True)
                conn.update(worksheet=opcao, data=novo_df)
                st.success("Salvo com sucesso! Atualizando...")
                st.rerun()
