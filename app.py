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

# NOVA FUNÇÃO: Extrai o número do pedido do texto
def extrair_numero_pedido(texto):
    # Procura padrões como "Pedido: 12345", "Nº Pedido 12345" ou números isolados após palavras-chave
    padroes = [
        r"(?:PEDIDO|NÚMERO|Nº)\s*[:.\-]?\s*(\d+)",
        r"ORDEM\s*VENDAS?\s*[:.\-]?\s*(\d+)"
    ]
    for padrao in padroes:
        resultado = re.search(padrao, texto, re.IGNORECASE)
        if resultado:
            return resultado.group(1)
    return "SEM_NUMERO"

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
    # ... (outros layouts permanecem iguais)
    
    df = pd.DataFrame(itens)
    if not df.empty:
        df["origem"] = f_info["operacao"]
        df["desconto"] = f_info["desconto"]
    return df

# --- INTERFACE ---
if LOGO_PATH.exists():
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

    for arquivo in arquivos:
        conteudo = arquivo.read()
        texto_pdf = extrair_texto_pdf(conteudo)
        f_info = identificar_fabrica(texto_pdf)
        
        # Extração de dados para o nome do arquivo
        num_pedido = extrair_numero_pedido(texto_pdf)
        # Se houver uma coluna 'codigo_cliente' na sua planilha, use ela, senão usamos o nome
        id_cliente = c_info.get('cnpj_cliente', cliente_original) 

        if f_info is not None:
            df_individual = processar_pedido(texto_pdf, c_info['layout'], f_info)
            if not df_individual.empty:
                # Nome do arquivo solicitado: Cliente_Pedido
                nome_formatado = f"{sel_display.replace(' ', '_')}_{num_pedido}"
                
                df_consolidado = df_individual.copy()
                df_consolidado["pedido"] = num_pedido
                df_consolidado["arquivo_origem"] = arquivo.name
                lista_dfs.append(df_consolidado)
                
                csv_buffer = io.StringIO()
                df_individual.to_csv(csv_buffer, index=False)
                arquivos_csv_zip[f"{nome_formatado}.csv"] = csv_buffer.getvalue()
        else:
            st.error(f"❌ Fábrica não identificada: {arquivo.name}")

    if lista_dfs:
        df_final = pd.concat(lista_dfs, ignore_index=True)
        st.success(f"✅ {len(lista_dfs)} pedido(s) processado(s)!")
        st.dataframe(df_final, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            csv_total = df_final.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Baixar Tudo (Consolidado)", csv_total, f"Consolidado_{sel_display}.csv", use_container_width=True)
        
        with col2:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for nome, conteudo_csv in arquivos_csv_zip.items():
                    zf.writestr(nome, conteudo_csv)
            st.download_button("📦 Baixar Separados (ZIP)", zip_buffer.getvalue(), f"Pedidos_{sel_display}.zip", use_container_width=True)
