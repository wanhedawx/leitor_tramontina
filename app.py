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
# Sua logo com escrita branca
LOGO_PATH = INFOS_DIR / "logo_light.png" 

# --- 2. FUNÇÕES DE SUPORTE (ORDEM IMPORTA!) ---
def get_image_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

@st.cache_data
def carregar_aba(aba):
    """Carrega as abas do Excel de configuração."""
    try:
        return pd.read_excel(CONFIG_PATH, sheet_name=aba, dtype=str)
    except Exception as e:
        st.error(f"Erro ao carregar a aba '{aba}': {e}")
        return pd.DataFrame()

def extrair_numero_pedido(texto, nome_arquivo):
    """Prioriza o número no nome do arquivo (ex: L75969) para não pegar o '000634'."""
    nome_sem_ext = Path(nome_arquivo).stem
    numeros_no_nome = re.findall(r"\d+", nome_sem_ext)
    if numeros_validos := [n for n in numeros_no_nome if len(n) >= 4]:
        return max(numeros_validos, key=len)
    
    padrao = r"(?:OC|PEDIDO|ORDEM)\s*[:.\-]?\s*(\d{4,})"
    resultado = re.search(padrao, texto, re.IGNORECASE)
    return resultado.group(1) if resultado else "SEM_NUMERO"

# --- 3. CSS PARA A LOGO NÃO SUMIR NO MODO CLARO ---
st.markdown(
    """
    <style>
    .logo-custom {
        width: 200px;
        display: block;
        margin: 0 auto;
    }
    /* Se o fundo for branco, inverte a logo branca para preto */
    @media (prefers-color-scheme: light) {
        .logo-custom {
            filter: invert(1) brightness(0.2); 
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 4. INTERFACE: LOGO ---
if LOGO_PATH.exists():
    img_b64 = get_image_base64(str(LOGO_PATH))
    col_esq, col_logo, col_dir = st.columns([1, 2, 1])
    with col_logo:
        st.markdown(
            f'<img src="data:image/png;base64,{img_b64}" class="logo-custom">',
            unsafe_allow_html=True
        )

st.markdown("<h1 style='text-align: center;'>Processador de Pedidos</h1>", unsafe_allow_html=True)
st.write("---")

# --- 5. LÓGICA DO APP ---
try:
    df_clientes = carregar_aba("clientes")
    if not df_clientes.empty:
        opcoes = {c.replace("_", " ").title(): c for c in df_clientes['cliente'].unique()}
        sel_display = st.selectbox("1. Selecione o Cliente", options=list(opcoes.keys()), index=None)
        arquivos = st.file_uploader("2. Envie os PDFs", type=["pdf"], accept_multiple_files=True)

        if st.button("🚀 Processar Pedidos", use_container_width=True, type="primary") and arquivos and sel_display:
            # Aqui entra sua lógica de processamento dos PDFs...
            st.success("Arquivos carregados. Adicione sua lógica de leitura de PDF aqui!")
except Exception as e:
    st.error(f"Erro no sistema: {e}")
