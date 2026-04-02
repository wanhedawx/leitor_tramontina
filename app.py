import io
import re
import base64
from pathlib import Path
import pandas as pd
import pdfplumber
import streamlit as st

# --- 1. CONFIGURAÇÃO E CAMINHOS ---
st.set_page_config(page_title="Processador de Pedidos", page_icon="📄", layout="centered")

BASE_DIR = Path(__file__).resolve().parent
INFOS_DIR = BASE_DIR / "infos"
CONFIG_PATH = INFOS_DIR / "regras_fabricas.xlsx"

# Caminhos das logos
LOGO_DARK = INFOS_DIR / "logo_dark.png"   # Para fundo claro (escrita escura)
LOGO_LIGHT = INFOS_DIR / "logo_light.png" # Para fundo escuro (escrita branca)

# --- 2. CSS PARA TROCA AUTOMÁTICA DE LOGO ---
st.markdown(
    """
    <style>
    /* Esconde a logo errada dependendo do tema do navegador */
    @media (prefers-color-scheme: dark) {
        .logo-light { display: block !important; margin: 0 auto; }
        .logo-dark { display: none !important; }
    }
    @media (prefers-color-scheme: light) {
        .logo-light { display: none !important; }
        .logo-dark { display: block !important; margin: 0 auto; }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 3. EXIBIÇÃO DA LOGO ---
col_esq, col_logo, col_dir = st.columns([1, 2, 1])
with col_logo:
    if LOGO_LIGHT.exists():
        # A classe 'logo-light' será controlada pelo CSS acima
        st.image(str(LOGO_LIGHT), width=200, output_format="PNG")
    if LOGO_DARK.exists():
        # A classe 'logo-dark' será controlada pelo CSS acima
        st.image(str(LOGO_DARK), width=200, output_format="PNG")

st.markdown("<h1 style='text-align: center;'>Processador de Pedidos</h1>", unsafe_allow_html=True)
st.write("---")

# --- 4. FUNÇÃO DE EXTRAÇÃO (CORREÇÃO DO NÚMERO L75969) ---
def extrair_numero_pedido(texto, nome_arquivo):
    """Prioriza o número no nome do arquivo para evitar o erro '000634'."""
    nome_sem_ext = Path(nome_arquivo).stem
    numeros_no_nome = re.findall(r"\d+", nome_sem_ext)
    
    if numeros_validos := [n for n in numeros_no_nome if len(n) >= 4]:
        return max(numeros_validos, key=len)
    
    padrao = r"(?:OC|PEDIDO|ORDEM)\s*[:.\-]?\s*(\d{4,})"
    resultado = re.search(padrao, texto, re.IGNORECASE)
    return resultado.group(1) if resultado else "SEM_NUMERO"

# --- 5. LÓGICA DE PROCESSAMENTO ---
try:
    clientes_df = carregar_aba("clientes")
    opcoes_clientes = {c.replace("_", " ").title(): c for c in clientes_df['cliente'].unique()}

    sel_display = st.selectbox("1. Selecione o Cliente", options=list(opcoes_clientes.keys()), index=None)
    arquivos = st.file_uploader("2. Envie os PDFs", type=["pdf"], accept_multiple_files=True)

    if st.button("🚀 Processar Pedidos", use_container_width=True, type="primary") and arquivos and sel_display:
        cliente_original = opcoes_clientes[sel_display]
        c_info = clientes_df[clientes_df['cliente'] == cliente_original].iloc[0]
        lista_dfs = []
        
        for arquivo in arquivos:
            texto_pdf = ""
            with pdfplumber.open(io.BytesIO(arquivo.read())) as pdf:
                for p in pdf.pages:
                    texto_pdf += (p.extract_text() or "") + "\n"
            
            num_pedido = extrair_numero_pedido(texto_pdf, arquivo.name)
            
            # Aqui você deve inserir suas funções de identificar_fabrica 
            # e processar_pedido para gerar o DataFrame 'df_ped'
            # st.write(f"Pedido: {num_pedido} processado.")
            
except Exception as e:
    st.error(f"Erro no sistema: {e}")
