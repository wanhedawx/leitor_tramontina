import io
import re
import base64
import zipfile
from pathlib import Path
import pandas as pd
import pdfplumber
import streamlit as st

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Processador de Pedidos", page_icon="📄", layout="centered")

BASE_DIR = Path(__file__).resolve().parent
INFOS_DIR = BASE_DIR / "infos"
CONFIG_PATH = INFOS_DIR / "regras_fabricas.xlsx"
LOGO_PATH = INFOS_DIR / "logo_light.png"

# --- 2. FUNÇÕES ---
def get_image_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

@st.cache_data
def carregar_aba(aba):
    try:
        if CONFIG_PATH.exists():
            return pd.read_excel(CONFIG_PATH, sheet_name=aba, dtype=str)
    except:
        pass
    return pd.DataFrame()

# --- 3. CSS: LOGO E ESTABILIDADE DA TELA ---
st.markdown(
    """
    <style>
    .logo-custom { width: 200px; display: block; margin: 0 auto; }
    @media (prefers-color-scheme: light) { .logo-custom { filter: invert(1) brightness(0.2); } }
    @media (prefers-color-scheme: dark) { .logo-custom { filter: none; } }
    
    /* Ajuste para evitar tela branca nos botões */
    .stDownloadButton { text-align: center; }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 4. INTERFACE ---
if LOGO_PATH.exists():
    try:
        img_b64 = get_image_base64(str(LOGO_PATH))
        st.markdown(f'<img src="data:image/png;base64,{img_b64}" class="logo-custom">', unsafe_allow_html=True)
    except:
        pass

st.markdown("<h1 style='text-align: center;'>Processador de Pedidos</h1>", unsafe_allow_html=True)
st.write("---")

# --- 5. ENTRADAS ---
df_clientes = carregar_aba("clientes")
if not df_clientes.empty:
    opcoes = {c.replace("_", " ").title(): c for c in df_clientes['cliente'].unique()}
    sel_display = st.selectbox("1. Selecione o Cliente", options=list(opcoes.keys()), index=None)
    arquivos = st.file_uploader("2. Envie os PDFs dos pedidos", type=["pdf"], accept_multiple_files=True)

    if st.button("🚀 Processar Pedidos", use_container_width=True, type="primary") and arquivos and sel_display:
        lista_dfs = []
        arquivos_para_zip = {}
        
        try:
            for arquivo in arquivos:
                dados_pdf = []
                # Abre o PDF com gerenciador de contexto para não travar memória
                with pdfplumber.open(io.BytesIO(arquivo.read())) as pdf:
                    for page in pdf.pages:
                        tabela = page.extract_table()
                        if tabela:
                            df_temp = pd.DataFrame(tabela[1:], columns=tabela[0])
                            # Remove colunas duplicadas para evitar erro de reindex
                            df_temp = df_temp.loc[:, ~df_temp.columns.duplicated()].copy()
                            df_temp['arquivo_origem'] = arquivo.name
                            dados_pdf.append(df_temp)
                
                if dados_pdf:
                    df_individual = pd.concat(dados_pdf, ignore_index=True)
                    lista_dfs.append(df_individual)
                    arquivos_csv[arquivo.name] = df_individual.to_csv(index=False).encode('utf-8')

            if lista_dfs:
                df_consolidado = pd.concat(lista_dfs, ignore_index=True)
                
                st.success(f"✅ {len(arquivos)} pedido(s) processado(s)!")
                st.dataframe(df_consolidado, use_container_width=True)
                
                st.write("---")
                # Botões lado a lado sem quebrar o layout
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("📥 Baixar Tudo (Único CSV)", 
                                       df_consolidado.to_csv(index=False).encode('utf-8'),
                                       f"CONSOLIDADO.csv", "text/csv", use_container_width=True)
                with c2:
                    buf = io.BytesIO()
                    with zipfile.ZipFile(buf, "w") as zf:
                        for nome, dados in arquivos_csv.items():
                            zf.writestr(nome.replace(".pdf", ".csv"), dados)
                    st.download_button("📦 Baixar Separados (ZIP)", 
                                       buf.getvalue(), "PEDIDOS.zip", "application/zip", use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao processar: {e}")
else:
    st.warning("Aguardando configuração de clientes...")
