import io
import re
from pathlib import Path
from PIL import Image
import pandas as pd
import pdfplumber
import streamlit as st

# --- CONFIGURAÇÃO E CAMINHOS ---
BASE_DIR = Path(__file__).resolve().parent
INFOS_DIR = BASE_DIR / "infos"
CONFIG_PATH = INFOS_DIR / "regras_fabricas.xlsx"
LOGO_PATH = INFOS_DIR / "logo.png"

st.set_page_config(page_title="Processador de Pedidos Tramontina", page_icon="📄", layout="centered")

# --- CARREGAMENTO DE DADOS ---
@st.cache_data
def carregar_aba(aba):
    # Carrega os dados da planilha Excel (Fábricas, Clientes, etc)
    return pd.read_excel(CONFIG_PATH, sheet_name=aba, dtype=str)

# --- UTILITÁRIOS DE PDF ---
def extrair_texto_pdf(pdf_bytes):
    texto = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for p in pdf.pages:
            texto += (p.extract_text() or "") + "\n"
    return texto

def identificar_fabrica(texto):
    df_f = carregar_aba("fabricas")
    texto_limpo = re.sub(r"\D", "", texto)
    for _, row in df_f.iterrows():
        cnpj_limpo = re.sub(r"\D", "", str(row['cnpj'])).zfill(14)
        if cnpj_limpo in texto_limpo:
            return row
    return None

# --- MOTOR DE PROCESSAMENTO ---
def processar_pedido(texto, layout, f_info):
    itens = []
    
    # Lógica para Cliente Palato
    if layout == "palato":
        for linha in texto.splitlines():
            if "Tramontina" in linha:
                sku = re.search(r"\b\d{7,8}\b", linha)
                qtd = re.search(r"\s(\d+)\s+(CX|UN)/", linha)
                if sku and qtd: 
                    itens.append({"sku": sku.group(), "quantidade": int(qtd.group(1))})
    
    # Lógica para Cliente Carajás
    elif layout == "carajas":
        for linha in texto.splitlines():
            m = re.match(r"^\d+\s+\d+\s+\d{13}\s+(\d[\d ]+)\s+.+?\-\s+(\d+)", linha.strip())
            if m: 
                itens.append({"sku": re.sub(r"\D", "", m.group(1)), "quantidade": int(m.group(2))})
    
    df = pd.DataFrame(itens)
    if not df.empty:
        # Cruza as informações da fábrica identificada (Origem e Desconto)
        df["origem"] = f_info["operacao"]
        df["desconto"] = f_info["desconto"]
    return df

# --- INTERFACE ---
if LOGO_PATH.exists():
    _, col_img, _ = st.columns([1, 1, 1])
    col_img.image(Image.open(str(LOGO_PATH)), width=150)

st.markdown("<h1 style='text-align: center;'>Processador de Pedidos</h1>", unsafe_allow_html=True)
st.write("---")

# Seleção de Cliente e Upload do Arquivo
clientes_df = carregar_aba("clientes")
lista_clientes = sorted(clientes_df['cliente'].unique().tolist())

sel_cliente = st.selectbox("1. Selecione o Cliente", lista_clientes, index=None, placeholder="Escolha um cliente...")
arquivo = st.file_uploader("2. Envie o PDF do pedido", type=["pdf"])

st.write("") # Espaçador

# Botão de Ação
if st.button("🚀 Processar Pedido", use_container_width=True, type="primary", disabled=not arquivo):
    texto_pdf = extrair_texto_pdf(arquivo.read())
    f_info = identificar_fabrica(texto_pdf)
    
    if f_info is None:
        st.error("❌ Fábrica não identificada no PDF (CNPJ não encontrado na base).")
    else:
        c_info = clientes_df[clientes_df['cliente'] == sel_cliente].iloc[0]
        df_final = processar_pedido(texto_pdf, c_info['layout'], f_info)
        
        if df_final.empty:
            st.warning("⚠️ Nenhum item extraído. Verifique se o layout do PDF condiz com o cliente selecionado.")
        else:
            st.success(f"✅ Pedido processado! Fábrica: {f_info['fabrica']}")
            
            # Exibição dos resultados
            st.dataframe(df_final, use_container_width=True)
            
            # Botão para download do CSV
            csv = df_final.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Baixar Resultado (CSV)",
                data=csv,
                file_name=f"pedido_{sel_cliente}.csv",
                mime="text/csv",
                use_container_width=True
            )

# Estilização básica
st.markdown("""
    <style>
    .stButton>button {
        border-radius: 5px;
        height: 3em;
    }
    </style>
    """, unsafe_allow_html=True)
