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
LOGO_PATH = INFOS_DIR / "logo.png"

st.set_page_config(page_title="Processador de Pedidos Tramontina", page_icon="📄", layout="centered")

@st.cache_data
def carregar_aba(aba):
    return pd.read_excel(CONFIG_PATH, sheet_name=aba, dtype=str)

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

def processar_pedido(texto, layout, f_info):
    itens = []
    if layout == "palato":
        for linha in texto.splitlines():
            if "Tramontina" in linha:
                sku = re.search(r"\b\d{7,8}\b", linha)
                qtd = re.search(r"\s(\d+)\s+(CX|UN)/", linha)
                if sku and qtd: 
                    itens.append({"sku": sku.group(), "quantidade": int(qtd.group(1))})
    elif layout == "carajas":
        for linha in texto.splitlines():
            m = re.match(r"^\d+\s+\d+\s+\d{13}\s+(\d[\d ]+)\s+.+?\-\s+(\d+)", linha.strip())
            if m: 
                itens.append({"sku": re.sub(r"\D", "", m.group(1)), "quantidade": int(m.group(2))})
    
    df = pd.DataFrame(itens)
    if not df.empty:
        df["origem"] = f_info["operacao"]
        df["desconto"] = f_info["desconto"]
    return df

# --- INTERFACE ---
# Logo centralizada com colunas de suporte
if LOGO_PATH.exists():
    # Criamos 3 colunas: a do meio (2) é onde a logo fica. 
    # As laterais (1) servem apenas para empurrar a logo para o centro.
    col_esq, col_logo, col_dir = st.columns([2, 2, 2])
    
    with col_logo:
        # O parâmetro use_container_width=True ajuda a centralizar dentro da coluna
        st.image(Image.open(str(LOGO_PATH)), width=180)

st.markdown("<h1 style='text-align: center;'>Processador de Pedidos</h1>", unsafe_allow_html=True)
st.write("---")
clientes_df = carregar_aba("clientes")
opcoes_clientes = {c.replace("_", " ").title(): c for c in clientes_df['cliente'].unique()}

sel_display = st.selectbox("1. Selecione o Cliente", options=list(opcoes_clientes.keys()), index=None, placeholder="Escolha um cliente...")
arquivos = st.file_uploader("2. Envie os PDFs dos pedidos", type=["pdf"], accept_multiple_files=True)

if st.button("🚀 Processar Pedidos", use_container_width=True, type="primary", disabled=not arquivos or not sel_display):
    cliente_original = opcoes_clientes[sel_display]
    c_info = clientes_df[clientes_df['cliente'] == cliente_original].iloc[0]
    
    lista_dfs = []
    arquivos_csv_zip = {} # Dicionário para guardar os CSVs individuais para o ZIP

    for arquivo in arquivos:
        conteudo = arquivo.read()
        texto_pdf = extrair_texto_pdf(conteudo)
        f_info = identificar_fabrica(texto_pdf)
        
        if f_info is not None:
            df_individual = processar_pedido(texto_pdf, c_info['layout'], f_info)
            if not df_individual.empty:
                # Adiciona coluna de origem para o consolidado
                df_consolidado_parte = df_individual.copy()
                df_consolidado_parte["arquivo_origem"] = arquivo.name
                lista_dfs.append(df_consolidado_parte)
                
                # Guarda o CSV individual (sem a coluna arquivo_origem para ficar limpo)
                csv_buffer = io.StringIO()
                df_individual.to_csv(csv_buffer, index=False)
                arquivos_csv_zip[f"{arquivo.name.replace('.pdf', '')}.csv"] = csv_buffer.getvalue()
        else:
            st.error(f"❌ Fábrica não identificada: {arquivo.name}")

    if lista_dfs:
        df_final = pd.concat(lista_dfs, ignore_index=True)
        st.success(f"✅ {len(lista_dfs)} pedido(s) processado(s)!")
        st.dataframe(df_final, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        # DOWNLOAD 1: TUDO JUNTO (CSV)
        with col1:
            csv_total = df_final.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Baixar Tudo (Único CSV)", csv_total, f"consolidado_{cliente_original}.csv", "text/csv", use_container_width=True)
        
        # DOWNLOAD 2: SEPARADOS (ZIP)
        with col2:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for nome_arquivo, conteudo_csv in arquivos_csv_zip.items():
                    zf.writestr(nome_arquivo, conteudo_csv)
            
            st.download_button("📦 Baixar Separados (ZIP)", zip_buffer.getvalue(), f"pedidos_separados_{cliente_original}.zip", "application/zip", use_container_width=True)
    else:
        st.warning("⚠️ Nenhum dado extraído.")
