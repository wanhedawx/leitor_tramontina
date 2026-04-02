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

# --- 2. FUNÇÕES (DEFINIDAS ANTES DO USO) ---
def get_image_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

@st.cache_data
def carregar_aba(aba):
    """Carrega as abas do Excel de configuração."""
    try:
        return pd.read_excel(CONFIG_PATH, sheet_name=aba, dtype=str)
    except Exception as e:
        st.error(f"Erro ao carregar '{aba}': {e}")
        return pd.DataFrame()

def extrair_numero_pedido(nome_arquivo):
    """Extrai o número (ex: 75969) do nome do arquivo."""
    numeros = re.findall(r"\d+", Path(nome_arquivo).stem)
    return max(numeros, key=len) if numeros else "SEM_NUMERO"

# --- 3. CSS: LOGO DINÂMICA (BRANCA NO ESCURO / PRETA NO CLARO) ---
st.markdown(
    """
    <style>
    .logo-custom { width: 200px; display: block; margin: 0 auto; }
    @media (prefers-color-scheme: light) { .logo-custom { filter: invert(1) brightness(0.2); } }
    @media (prefers-color-scheme: dark) { .logo-custom { filter: none; } }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 4. INTERFACE: LOGO ---
if LOGO_PATH.exists():
    img_b64 = get_image_base64(str(LOGO_PATH))
    st.markdown(f'<img src="data:image/png;base64,{img_b64}" class="logo-custom">', unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>Processador de Pedidos</h1>", unsafe_allow_html=True)
st.write("---")

# --- 5. ENTRADA DE DADOS E OPÇÕES ---
try:
    df_clientes = carregar_aba("clientes")
    
    if not df_clientes.empty:
        # Monta o dicionário de opções baseado na coluna 'cliente' do seu Excel
        opcoes = {c.replace("_", " ").title(): c for c in df_clientes['cliente'].unique()}
        
        # O selectbox agora exibe as opções vindas do seu arquivo
        sel_display = st.selectbox("1. Selecione o Cliente", options=list(opcoes.keys()), index=None)
        arquivos = st.file_uploader("2. Envie os PDFs", type=["pdf"], accept_multiple_files=True)

        if st.button("🚀 Processar Pedidos", use_container_width=True, type="primary") and arquivos and sel_display:
            cliente_id = opcoes[sel_display]
            todos_pedidos = []
            
            for arquivo in arquivos:
                num_pedido = extrair_numero_pedido(arquivo.name)
                
                # --- LÓGICA DE EXTRAÇÃO ---
                df_pedido = pd.DataFrame({"Pedido": [num_pedido], "Cliente": [sel_display], "Status": ["OK"]})
                todos_pedidos.append(df_pedido)
                
                with st.expander(f"📄 Prévia: Pedido {num_pedido}", expanded=True):
                    st.dataframe(df_pedido, use_container_width=True)
                    st.download_button(
                        label=f"⬇️ Baixar Pedido {num_pedido}",
                        data=df_pedido.to_csv(index=False).encode('utf-8'),
                        file_name=f"PEDIDO_{num_pedido}.csv",
                        mime="text/csv",
                        key=f"btn_{num_pedido}"
                    )

            if todos_pedidos:
                st.write("---")
                df_consolidado = pd.concat(todos_pedidos, ignore_index=True)
                st.download_button(
                    label="💾 BAIXAR TODOS OS PEDIDOS CONSOLIDADOS",
                    data=df_consolidado.to_csv(index=False).encode('utf-8'),
                    file_name=f"CONSOLIDADO_{cliente_id.upper()}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    else:
        st.warning("Nenhum cliente encontrado no arquivo regras_fabricas.xlsx.")

except Exception as e:
    st.error(f"Erro ao processar as opções: {e}")
