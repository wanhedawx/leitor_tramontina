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

def extrair_numero_pedido(nome_arquivo):
    """Pega o número do pedido direto do nome do arquivo (ex: L75969 -> 75969)."""
    nome_sem_ext = Path(nome_arquivo).stem
    numeros = re.findall(r"\d+", nome_sem_ext)
    if numeros_validos := [n for n in numeros if len(n) >= 4]:
        return max(numeros_validos, key=len)
    return "SEM_NUMERO"

# --- 3. CSS PARA LOGO BRANCA (CORRIGIDO PARA MODO CLARO/ESCURO) ---
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
        .logo-custom { filter: invert(1) brightness(0.2); }
    }
    /* MODO ESCURO: Mantém a logo BRANCA original */
    @media (prefers-color-scheme: dark) {
        .logo-custom { filter: none; }
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

# --- 5. LÓGICA DE PROCESSAMENTO ---
try:
    df_clientes = carregar_aba("clientes")
    opcoes = {c.replace("_", " ").title(): c for c in df_clientes['cliente'].unique()}
    
    sel_display = st.selectbox("1. Selecione o Cliente", options=list(opcoes.keys()), index=None)
    arquivos = st.file_uploader("2. Envie os PDFs", type=["pdf"], accept_multiple_files=True)

    if st.button("🚀 Processar Pedidos", use_container_width=True, type="primary") and arquivos and sel_display:
        cliente_id = opcoes[sel_display]
        
        for arquivo in arquivos:
            # 1. Extrai o número do pedido do nome do arquivo
            num_pedido = extrair_numero_pedido(arquivo.name)
            
            # 2. Simulação de processamento (Aqui você mantém sua lógica de extração de itens)
            # Vamos supor que 'df_final' seja o resultado da sua extração:
            df_final = pd.DataFrame({"Item": ["Exemplo"], "Qtd": [1]}) 
            
            st.success(f"Pedido {num_pedido} processado!")
            st.dataframe(df_final)

            # 3. BOTÃO DE BAIXAR O ARQUIVO (O QUE FALTAVA!)
            csv = df_final.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 Baixar CSV Pedido {num_pedido}",
                data=csv,
                file_name=f"PEDIDO_{cliente_id.upper()}_{num_pedido}.csv",
                mime="text/csv",
                key=f"btn_{num_pedido}" # Key única para não dar erro no loop
            )

except Exception as e:
    st.error(f"Erro no sistema: {e}")
