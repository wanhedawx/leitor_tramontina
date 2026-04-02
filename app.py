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
        return pd.read_excel(CONFIG_PATH, sheet_name=aba, dtype=str)
    except:
        return pd.DataFrame()

# --- 3. CSS: LOGO E BOTÕES LADO A LADO ---
st.markdown(
    """
    <style>
    .logo-custom { width: 200px; display: block; margin: 0 auto; }
    @media (prefers-color-scheme: light) { .logo-custom { filter: invert(1) brightness(0.2); } }
    @media (prefers-color-scheme: dark) { .logo-custom { filter: none; } }
    
    /* Estilo para os botões finais ficarem lado a lado */
    div.stDownloadButton { display: inline-block; width: 49%; }
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

# --- 5. ENTRADAS (VERTICAL) ---
try:
    df_clientes = carregar_aba("clientes")
    if not df_clientes.empty:
        opcoes = {c.replace("_", " ").title(): c for c in df_clientes['cliente'].unique()}
        sel_display = st.selectbox("1. Selecione o Cliente", options=list(opcoes.keys()), index=None)
        arquivos = st.file_uploader("2. Envie os PDFs dos pedidos", type=["pdf"], accept_multiple_files=True)

        if st.button("🚀 Processar Pedidos", use_container_width=True, type="primary") and arquivos and sel_display:
            lista_dfs = []
            arquivos_csv = {} # Para o ZIP
            
            for arquivo in arquivos:
                dados_ped = []
                with pdfplumber.open(io.BytesIO(arquivo.read())) as pdf:
                    for page in pdf.pages:
                        tabela = page.extract_table()
                        if tabela:
                            # Converte para DF usando a lógica de itens reais
                            df_temp = pd.DataFrame(tabela[1:], columns=tabela[0])
                            df_temp = df_temp.loc[:, ~df_temp.columns.duplicated()].copy()
                            
                            # Adiciona a coluna de arquivo_origem
                            df_temp['arquivo_origem'] = arquivo.name
                            dados_ped.append(df_temp)
                
                if dados_ped:
                    df_individual = pd.concat(dados_ped, ignore_index=True)
                    lista_dfs.append(df_individual)
                    arquivos_csv[arquivo.name] = df_individual.to_csv(index=False).encode('utf-8')

            if lista_dfs:
                df_consolidado = pd.concat(lista_dfs, ignore_index=True)
                
                st.success(f"✅ {len(arquivos)} pedido(s) processado(s)!")
                
                # Exibe a prévia com as colunas solicitadas
                st.dataframe(df_consolidado, use_container_width=True)
                
                st.write("---")
                
                # --- BOTÕES FINAIS LADO A LADO ---
                col_baixar1, col_baixar2 = st.columns(2)
                
                with col_baixar1:
                    st.download_button(
                        label="📥 Baixar Tudo (Único CSV)",
                        data=df_consolidado.to_csv(index=False).encode('utf-8'),
                        file_name=f"CONSOLIDADO_{opcoes[sel_display].upper()}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col_baixar2:
                    # Gera o arquivo ZIP na memória
                    buf = io.BytesIO()
                    with zipfile.ZipFile(buf, "x", zipfile.ZIP_DEFLATED) as zf:
                        for nome, conteudo in arquivos_csv.items():
                            zf.writestr(nome.replace(".pdf", ".csv"), conteudo)
                    
                    st.download_button(
                        label="📦 Baixar Separados (ZIP)",
                        data=buf.getvalue(),
                        file_name="PEDIDOS_SEPARADOS.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
    else:
        st.error("Erro: Cadastre os clientes no Excel.")

except Exception as e:
    st.error(f"Erro: {e}")
