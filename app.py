import io
import re
import base64
from pathlib import Path
import pandas as pd
import pdfplumber
import streamlit as st

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Processador de Pedidos", page_icon="📄", layout="centered")

BASE_DIR = Path(__file__).resolve().parent
INFOS_DIR = BASE_DIR / "infos"
CONFIG_PATH = INFOS_DIR / "regras_fabricas.xlsx"
LOGO_PATH = INFOS_DIR / "logo_light.png" # Sua logo de escrita BRANCA

# --- 2. FUNÇÕES ---
def get_image_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

@st.cache_data
def carregar_aba(aba):
    return pd.read_excel(CONFIG_PATH, sheet_name=aba, dtype=str)

def extrair_numero_pedido(texto, nome_arquivo):
    """Garante que pegue o L75969 do nome e ignore o 000634 interno."""
    nome_sem_ext = Path(nome_arquivo).stem
    numeros = re.findall(r"\d+", nome_sem_ext)
    if numeros_validos := [n for n in numeros if len(n) >= 4]:
        return max(numeros_validos, key=len)
    return "SEM_NUMERO"

# --- 3. CSS PARA LOGO BRANCA (CORRIGIDO) ---
st.markdown(
    """
    <style>
    .logo-custom {
        width: 200px;
        display: block;
        margin: 0 auto;
    }
    /* MODO CLARO: Inverte o BRANCO da logo para PRETO */
    @media (prefers-color-scheme: light) {
        .logo-custom {
            filter: invert(1) contrast(2); 
        }
    }
    /* MODO ESCURO: Mantém a logo BRANCA original */
    @media (prefers-color-scheme: dark) {
        .logo-custom {
            filter: none;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 4. INTERFACE ---
if LOGO_PATH.exists():
    img_b64 = get_image_base64(str(LOGO_PATH))
    st.markdown(f'<img src="data:image/png;base64,{img_b64}" class="logo-custom">', unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>Processador de Pedidos</h1>", unsafe_allow_html=True)
st.write("---")

# --- 5. PROCESSAMENTO REAL ---
try:
    df_clientes = carregar_aba("clientes")
    opcoes = {c.replace("_", " ").title(): c for c in df_clientes['cliente'].unique()}
    
    sel_display = st.selectbox("1. Selecione o Cliente", options=list(opcoes.keys()), index=None)
    arquivos = st.file_uploader("2. Envie os PDFs", type=["pdf"], accept_multiple_files=True)

    if st.button("🚀 Processar Pedidos", use_container_width=True, type="primary") and arquivos and sel_display:
        cliente_id = opcoes[sel_display]
        resultados = []

        for arquivo in arquivos:
            texto_pdf = ""
            with pdfplumber.open(io.BytesIO(arquivo.read())) as pdf:
                for p in pdf.pages:
                    texto_pdf += (p.extract_text() or "") + "\n"
            
            num_pedido = extrair_numero_pedido(texto_pdf, arquivo.name)
            
            # --- INSIRA SUA LÓGICA DE EXTRAÇÃO DE ITENS AQUI ---
            # Exemplo genérico para não dar erro:
            dado_ficticio = {"Pedido": num_pedido, "Status": "Processado"}
            resultados.append(dado_ficticio)
            
        st.success(f"{len(arquivos)} pedido(s) lido(s) com sucesso!")
        st.dataframe(pd.DataFrame(resultados))

except Exception as e:
    st.error(f"Erro no sistema: {e}")
