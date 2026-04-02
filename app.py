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

# Caminhos das duas logos
LOGO_PARA_FUNDO_BRANCO = INFOS_DIR / "logo_dark.png"  # Escrita escura
LOGO_PARA_FUNDO_ESCURO = INFOS_DIR / "logo_light.png" # Escrita branca

# --- 2. EXIBIÇÃO DA LOGO DINÂMICA ---
# O Streamlit troca automaticamente baseado no tema do usuário
if LOGO_PARA_FUNDO_BRANCO.exists() and LOGO_PARA_FUNDO_ESCURO.exists():
    st.logo(
        image=str(LOGO_PARA_FUNDO_BRANCO),       # Mostra esta no modo claro
        dark_theme=str(LOGO_PARA_FUNDO_ESCURO), # Mostra esta no modo escuro
        size="large"
    )
else:
    # Caso os arquivos tenham nomes diferentes, exibe aviso
    st.warning("Verifique se logo_dark.png e logo_light.png estão na pasta infos.")

st.markdown("<h1 style='text-align: center;'>Processador de Pedidos</h1>", unsafe_allow_html=True)
st.write("---")

# --- 3. FUNÇÃO DE EXTRAÇÃO (CORREÇÃO DO NÚMERO L75969) ---
def extrair_numero_pedido(texto, nome_arquivo):
    """Prioriza o número no nome do arquivo para ignorar o '000634' interno."""
    nome_sem_ext = Path(nome_arquivo).stem
    numeros_no_nome = re.findall(r"\d+", nome_sem_ext)
    
    # Se achar número no nome (ex: 75969), usa ele
    if numeros_validos := [n for n in numeros_no_nome if len(n) >= 4]:
        return max(numeros_validos, key=len)
    
    # Só busca no texto se o nome do arquivo estiver limpo
    padrao = r"(?:OC|PEDIDO|ORDEM)\s*[:.\-]?\s*(\d{4,})"
    resultado = re.search(padrao, texto, re.IGNORECASE)
    return resultado.group(1) if resultado else "SEM_NUMERO"

# --- CONTINUE COM O RESTANTE DO SEU CÓDIGO (PROCESSAMENTO) ---

# --- 4. INTERFACE: LOGO ---
if LOGO_PATH.exists():
    try:
        img_b64 = get_image_base64(str(LOGO_PATH))
        col_esq, col_logo, col_dir = st.columns([1, 2, 1])
        with col_logo:
            st.markdown(
                f'<img src="data:image/png;base64,{img_b64}" class="logo-custom">',
                unsafe_allow_html=True
            )
    except Exception as e:
        st.error(f"Erro ao carregar logo: {e}")

st.markdown("<h1 style='text-align: center;'>Processador de Pedidos</h1>", unsafe_allow_html=True)
st.write("---")

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
