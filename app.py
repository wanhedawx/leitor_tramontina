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

# Caminhos das logos como strings (evita o erro do st.logo)
LOGO_BRANCA = str(INFOS_DIR / "logo_light.png")
LOGO_PRETA = str(INFOS_DIR / "logo_dark.png")

st.set_page_config(page_title="Processador de Pedidos", page_icon="📄", layout="centered")

# --- O JEITO CERTO DO STREAMLIT ---
# Usamos try/except para o caso da versão do Streamlit ser antiga
try:
    st.logo(
        image=LOGO_PRETA,      # Aparece no modo claro (fundo branco)
        dark_theme=LOGO_BRANCA, # Aparece no modo escuro
        size="large"
    )
except Exception:
    pass

@st.cache_data
def carregar_aba(aba):
    return pd.read_excel(CONFIG_PATH, sheet_name=aba, dtype=str)

def extrair_texto_pdf(pdf_bytes):
    texto = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for p in pdf.pages:
                texto += (p.extract_text() or "") + "\n"
    except Exception:
        pass
    return texto

def extrair_numero_pedido(texto, nome_arquivo):
    """
    Prioridade total ao nome do arquivo (ex: L75969.pdf) para evitar o erro do '000634'.
    """
    # 1. Tenta pegar os números do nome do arquivo primeiro
    nome_limpo = Path(nome_arquivo).stem
    numeros_nome = re.findall(r"\d+", nome_limpo)
    if numeros_nome:
        return max(numeros_nome, key=len)
    
    # 2. Se não tiver no nome, busca no texto
    resultado = re.search(r"(?:OC|PEDIDO|ORDEM)\s*[:.\-]?\s*(\d{4,})", texto, re.IGNORECASE)
    return resultado.group(1) if resultado else "0000"

# ... (Funções identificar_fabrica e processar_pedido continuam as mesmas) ...

# --- INTERFACE CENTRAL ---
# Para a logo central não sumir, vamos usar a versão PRETA que você quer que destaque
if Path(LOGO_PRETA).exists():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Mostra a logo escura no centro para garantir visibilidade no modo branco
        st.image(LOGO_PRETA, width=200)

st.markdown("<h1 style='text-align: center;'>Processador de Pedidos</h1>", unsafe_allow_html=True)
st.write("---")

# O restante do seu código de upload e processamento vem aqui...
