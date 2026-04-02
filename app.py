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
LOGO_BRANCA = INFOS_DIR / "logo_light.png"
LOGO_PRETA = INFOS_DIR / "logo_dark.png"

st.set_page_config(page_title="Processador de Pedidos", page_icon="📄", layout="centered")

# --- CSS PARA A LOGO NÃO SUMIR (MODO BRANCO E ESCURO) ---
st.markdown(
    """
    <style>
    .logo-container {
        display: flex;
        justify-content: center;
        padding: 20px;
    }
    /* No modo claro, a logo preta fica normal. No modo escuro, o filtro inverte para branco */
    @media (prefers-color-scheme: dark) {
        .logo-img { filter: invert(1) brightness(2); }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Exibe a logo (usando a logo_dark como base, o CSS inverte se precisar)
if LOGO_PRETA.exists():
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    st.image(str(LOGO_PRETA), width=200, output_format="PNG")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>Processador de Pedidos</h1>", unsafe_allow_html=True)
st.write("---")

@st.cache_data
def carregar_aba(aba):
    try:
        return pd.read_excel(CONFIG_PATH, sheet_name=aba, dtype=str)
    except Exception as e:
        st.error(f"Erro ao carregar aba {aba}: {e}")
        return pd.DataFrame()

def extrair_numero_pedido(texto, nome_arquivo):
    # 1. Prioridade absoluta: Números no nome do arquivo (Ex: L75969.pdf -> 75969)
    numeros_nome = re.findall(r"\d+", Path(nome_arquivo).stem)
    if numeros_nome:
        return max(numeros_nome, key=len)
    
    # 2. Busca no texto por OC ou Pedido
    resultado = re.search(r"(?:OC|PEDIDO|ORDEM)\s*[:.\-]?\s*(\d{4,})", texto, re.IGNORECASE)
    if resultado:
        return resultado.group(1)
    
    return "SEM_NUMERO"

# --- LÓGICA DE IDENTIFICAÇÃO E PROCESSAMENTO ---
def identificar_fabrica(texto):
    df_f = carregar_aba("fabricas")
    if df_f.empty: return None
    texto_limpo = re.sub(r"\D", "", texto)
    for _, row in df_f.iterrows():
        cnpj_limpo = re.sub(r"\D", "", str(row['cnpj'])).zfill(14)
        if cnpj_limpo in texto_limpo:
            return row
    return None

def processar_pedido(texto, layout, f_info):
    itens = []
    if layout == "carajas":
        for linha in texto.splitlines():
            # Regex ajustada para capturar SKU e QTD
            m = re.match(r"^\d+\s+\d+\s+\d{13}\s+(\d[\d ]+)\s+.+?\-\s+(\d+)", linha.strip())
            if m: 
                itens.append({"sku": re.sub(r"\D", "", m.group(1)), "quantidade": int(m.group(2))})
    df = pd.DataFrame(itens)
    if not df.empty:
        df["origem"] = f_info["operacao"]
        df["desconto"] = f_info["desconto"]
    return df

# --- INTERFACE DE UPLOAD ---
clientes_df = carregar_aba("clientes")
if not clientes_df.empty:
    opcoes_clientes = {c.replace("_", " ").title(): c for c in clientes_df['cliente'].unique()}
    sel_display = st.selectbox("1. Selecione o Cliente", options=list(opcoes_clientes.keys()), index=None)
    arquivos = st.file_uploader("2. Envie os PDFs", type=["pdf"], accept_multiple_files=True)

    if st.button("🚀 Processar Pedidos", use_container_width=True, type="primary") and arquivos and sel_display:
        cliente_original = opcoes_clientes[sel_display]
        c_info = clientes_df[clientes_df['cliente'] == cliente_original].iloc[0]
        
        lista_dfs = []
        arquivos_csv_zip = {}
        
        for arquivo in arquivos:
            with pdfplumber.open(io.BytesIO(arquivo.read())) as pdf:
                texto_pdf = "\n".join([p.extract_text() or "" for p in pdf.pages])
            
            f_info = identificar_fabrica(texto_pdf)
            num_pedido = extrair_numero_pedido(texto_pdf, arquivo.name)
            
            if f_info is not None:
                df_ped = processar_pedido(texto_pdf, c_info['layout'], f_info)
                if not df_ped.empty:
                    df_ped["pedido"] = num_pedido
                    lista_dfs.append(df_ped)
                    
                    csv = df_ped.to_csv(index=False).encode('utf-8')
                    arquivos_csv_zip[f"{sel_display.upper()} {num_pedido}.csv"] = csv
            else:
                st.error(f"Fábrica não identificada em {arquivo.name}")

        if lista_dfs:
            df_final = pd.concat(lista_dfs, ignore_index=True)
            st.dataframe(df_final, use_container_width=True)
            
            # Botão de Download do Consolidado
            st.download_button("⬇️ Baixar Planilha Consolidada", df_final.to_csv(index=False).encode('utf-8'), "pedidos_processados.csv", "text/csv", use_container_width=True)
