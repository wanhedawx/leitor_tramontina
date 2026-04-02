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

def extrair_numero_pedido(texto):
    # Procura especificamente por termos de Ordem de Compra ou Pedido
    padroes_oc = [
        r"OC\s*[:.\-]?\s*(\d+)",
        r"ORDEM\s*DE?\s*COMPRA\s*[:.\-]?\s*(\d+)",
        r"PEDIDO\s*DO?\s*CLIENTE\s*[:.\-]?\s*(\d+)",
        r"PEDIDO\s*[:.\-]?\s*(\d+)"
    ]
    
    for padrao in padroes_oc:
        resultado = re.search(padrao, texto, re.IGNORECASE)
        if resultado:
            return resultado.group(1)
    
    # Caso não ache com nomes, busca o primeiro número de 5 a 8 dígitos no topo
    numeros_topo = re.findall(r"\b\d{5,8}\b", texto[:600])
    if numeros_topo:
        return numeros_topo[0]
        
    return "0000"

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
    if layout == "carajas":
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
if LOGO_PATH.exists():
    # Centralização corrigida para [1, 2, 1]
    col_esq, col_logo, col_dir = st.columns([2, 2, 1])
    with col_logo:
        st.image(Image.open(str(LOGO_PATH)), width=180)

st.markdown("<h1 style='text-align: center;'>Processador de Pedidos</h1>", unsafe_allow_html=True)
st.write("---")

clientes_df = carregar_aba("clientes")
opcoes_clientes = {c.replace("_", " ").title(): c for c in clientes_df['cliente'].unique()}

sel_display = st.selectbox("1. Selecione o Cliente", options=list(opcoes_clientes.keys()), index=None)
arquivos = st.file_uploader("2. Envie os PDFs", type=["pdf"], accept_multiple_files=True)

if st.button("🚀 Processar Pedidos", use_container_width=True, type="primary", disabled=not arquivos or not sel_display):
    cliente_original = opcoes_clientes[sel_display]
    c_info = clientes_df[clientes_df['cliente'] == cliente_original].iloc[0]
    
    lista_dfs = []
    arquivos_csv_zip = {}
    ultimo_num_pedido = "SEM_NUMERO"

    for arquivo in arquivos:
        conteudo = arquivo.read()
        texto_pdf = extrair_texto_pdf(conteudo)
        f_info = identificar_fabrica(texto_pdf)
        
        num_pedido = extrair_numero_pedido(texto_pdf)
        ultimo_num_pedido = num_pedido # Guarda para o nome do arquivo individual

       # ... dentro do loop for arquivo in arquivos:
    num_pedido = extrair_numero_pedido(texto_pdf)
    
    if f_info is not None:
        df_individual = processar_pedido(texto_pdf, c_info['layout'], f_info)
        if not df_individual.empty:
            # FORMATO: CLIENTE NUMERO_OC (Ex: CARAJAS 75969)
            nome_final_individual = f"{sel_display.upper()} {num_pedido}"
            
            # Guarda para o ZIP
            arquivos_csv_zip[f"{nome_final_individual}.csv"] = csv_buffer.getvalue()
        else:
            st.error(f"❌ Fábrica não identificada: {arquivo.name}")

    # --- BLOCO DE EXPORTAÇÃO CORRIGIDO ---
    if lista_dfs:
        df_final = pd.concat(lista_dfs, ignore_index=True)
        st.success(f"✅ {len(lista_dfs)} pedido(s) processado(s)!")
        st.dataframe(df_final, use_container_width=True)
        
        cliente_venda = sel_display.upper()
        
        # Define o nome do arquivo consolidado
        if len(arquivos) == 1:
            nome_arquivo_final = f"{cliente_venda} {ultimo_num_pedido}"
        else:
            nome_arquivo_final = f"{cliente_venda} MULTIPLOS"

        st.write("---")
        col1, col2 = st.columns(2)
        
        with col1:
            csv_total = df_final.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"⬇️ Baixar {nome_arquivo_final}", 
                data=csv_total,
                file_name=f"{nome_arquivo_final}.csv", 
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for nome, conteudo_csv in arquivos_csv_zip.items():
                    zf.writestr(nome.upper(), conteudo_csv)
            
            st.download_button(
                label="📦 Baixar Separados (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"PEDIDOS_{cliente_venda}.zip",
                mime="application/zip",
                use_container_width=True
            )
    else:
        st.warning("⚠️ Nenhum dado extraído.")
