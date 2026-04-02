import io
import re
import zipfile
from pathlib import Path
from PIL import Image
import pandas as pd
import pdfplumber
import streamlit as st

# --- CONFIGURAÇÃO E CAMINHOS ---
BASE_DIR = Path(__file__).resolve().parent
INFOS_DIR = BASE_DIR / "infos"
CONFIG_PATH = INFOS_DIR / "regras_fabricas.xlsx"
# Ajuste o nome abaixo para o nome real do seu arquivo único (ex: logo_dark.png)
LOGO_PATH = INFOS_DIR / "logo_dark.png" 

st.set_page_config(page_title="Processador de Pedidos", page_icon="📄", layout="centered")

# --- CSS PARA LOGO ÚNICA (MODO CLARO E ESCURO) ---
st.markdown(
    """
    <style>
    /* Cria um fundo branco fixo para a logo preta não sumir no modo escuro */
    .logo-container {
        background-color: white;
        padding: 10px;
        border-radius: 10px;
        display: inline-block;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- INTERFACE: LOGO ---
if LOGO_PATH.exists():
    col_esq, col_logo, col_dir = st.columns([1, 2, 1])
    with col_logo:
        # Coloca a logo dentro do container branco definido no CSS
        st.markdown('<div style="text-align: center;"><div class="logo-container">', unsafe_allow_html=True)
        st.image(Image.open(str(LOGO_PATH)), width=180)
        st.markdown('</div></div>', unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>Processador de Pedidos</h1>", unsafe_allow_html=True)
st.write("---")

# --- FUNÇÕES DE EXTRAÇÃO ---
@st.cache_data
def carregar_aba(aba):
    return pd.read_excel(CONFIG_PATH, sheet_name=aba, dtype=str)

def extrair_numero_pedido(texto, nome_arquivo):
    """Prioriza o número no nome do arquivo (ex: L75969) para evitar erros."""
    nome_sem_ext = Path(nome_arquivo).stem
    numeros_no_nome = re.findall(r"\d+", nome_sem_ext)
    if numeros_nome := [n for n in numeros_no_nome if len(n) >= 4]:
        return max(numeros_nome, key=len)
    
    padrao = r"(?:OC|PEDIDO|ORDEM)\s*[:.\-]?\s*(\d{4,})"
    resultado = re.search(padrao, texto, re.IGNORECASE)
    return resultado.group(1) if resultado else "SEM_NUMERO"

# --- PROCESSAMENTO ---
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
        # ... (restante da lógica de identificar_fabrica e processar_pedido)
        
        # Exemplo de como montar o nome do arquivo final sem erro de sintaxe
        nome_final = f"PEDIDOS_{sel_display.upper()}_{num_pedido}.csv"
        # st.write(f"Processando: {nome_final}")
