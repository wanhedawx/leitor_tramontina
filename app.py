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

# Definindo os caminhos das logos que você já tem na pasta
LOGO_BRANCA = str(INFOS_DIR / "logo_light.png") # Para fundo escuro
LOGO_PRETA = str(INFOS_DIR / "logo_dark.png")   # Para fundo branco (Modo Claro)

st.set_page_config(page_title="Processador de Pedidos Tramontina", page_icon="📄", layout="centered")

# --- AQUI ESTÁ O JEITO NATIVO DO STREAMLIT ---
# Ele mostra a 'icon_image' no modo claro e a 'dark_theme' no modo escuro
st.logo(
    image=LOGO_PRETA,      # Esta fica escura quando o fundo for branco
    dark_theme=LOGO_BRANCA, # Esta fica clara quando o fundo for escuro
    size="large"
)

@st.cache_data
def carregar_aba(aba):
    return pd.read_excel(CONFIG_PATH, sheet_name=aba, dtype=str)

# ... (restante das suas funções de extração permanecem iguais) ...

def extrair_numero_pedido(texto, nome_arquivo):
    # Prioridade ao nome do arquivo para garantir o número correto
    nome_sem_extensao = Path(nome_arquivo).stem
    numeros_no_nome = re.findall(r"\d+", nome_sem_extensao)
    if numeros_no_nome:
        return max(numeros_no_nome, key=len)
    
    padrao_rigido = r"(?:OC|PEDIDO|ORDEM|COMPRA)\s*[:.\-]?\s*(\d{4,})"
    resultado = re.search(padrao_rigido, texto, re.IGNORECASE)
    return resultado.group(1) if resultado else "SEM_NUMERO"

# --- INTERFACE CENTRAL ---
# Se você ainda quiser a logo no centro da página (além da barra lateral)
# e quer que ela mude, o Streamlit não faz isso 100% automático no st.image,
# por isso a recomendação é usar apenas o st.logo acima. 

# Mas se fizer questão da logo central, o código abaixo ajuda:
col_esq, col_logo, col_dir = st.columns([1, 2, 1])
with col_logo:
    # Mostramos a logo preta aqui, que é a que você quer que apareça bem no modo claro
    st.image(LOGO_PRETA, width=200)

st.markdown("<h1 style='text-align: center;'>Processador de Pedidos</h1>", unsafe_allow_html=True)
st.write("---")

# ... (resto do código do uploader e botões) ...
