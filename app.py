import io
import re
import base64
from pathlib import Path
import pandas as pd
import pdfplumber
import streamlit as st

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Processador de Pedidos", page_icon="📄", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
INFOS_DIR = BASE_DIR / "infos"
LOGO_PATH = INFOS_DIR / "logo_light.png" # Sua logo de escrita BRANCA

# --- 2. FUNÇÕES ---
def get_image_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def extrair_numero_pedido(nome_arquivo):
    """Extrai o número (ex: 75969) do nome do arquivo."""
    numeros = re.findall(r"\d+", Path(nome_arquivo).stem)
    return max(numeros, key=len) if numeros else "SEM_NUMERO"

# --- 3. CSS: LOGO CAMALEÃO ---
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

# --- 5. LÓGICA DE PROCESSAMENTO ---
col1, col2 = st.columns([1, 1])
with col1:
    sel_cliente = st.selectbox("1. Selecione o Cliente", options=["Carajas", "Outro"], index=None)
with col2:
    arquivos = st.file_uploader("2. Envie os PDFs", type=["pdf"], accept_multiple_files=True)

if st.button("🚀 Processar e Gerar Prévias", use_container_width=True, type="primary") and arquivos and sel_cliente:
    todos_pedidos = []
    
    for arquivo in arquivos:
        num_pedido = extrair_numero_pedido(arquivo.name)
        
        # --- SIMULAÇÃO DA SUA LÓGICA DE EXTRAÇÃO ---
        # Substitua este DataFrame pela sua função real de extração
        df_pedido = pd.DataFrame({
            "Pedido": [num_pedido],
            "Item": ["Exemplo SKU 123"],
            "Qtd": [10],
            "Cliente": [sel_cliente]
        })
        todos_pedidos.append(df_pedido)
        
        # Exibe Prévias Individuais
        with st.expander(f"📄 Prévia: Pedido {num_pedido}", expanded=True):
            st.dataframe(df_pedido, use_container_width=True)
            csv_ind = df_pedido.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"⬇️ Baixar Pedido {num_pedido} (Individual)",
                data=csv_ind,
                file_name=f"PEDIDO_{num_pedido}.csv",
                mime="text/csv",
                key=f"btn_{num_pedido}"
            )

    # --- BOTÃO CONSOLIDADO ---
    if todos_pedidos:
        df_consolidado = pd.concat(todos_pedidos, ignore_index=True)
        st.write("---")
        st.subheader("📦 Arquivo Consolidado (Todos os pedidos)")
        st.dataframe(df_consolidado, use_container_width=True)
        
        csv_total = df_consolidado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="💾 BAIXAR TODOS OS PEDIDOS EM UM ÚNICO ARQUIVO",
            data=csv_total,
            file_name=f"CONSOLIDADO_{sel_cliente.upper()}.csv",
            mime="text/csv",
            use_container_width=True
        )
