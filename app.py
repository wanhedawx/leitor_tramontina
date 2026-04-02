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
# ... (mantenha o código anterior da logo e selectbox)

# 2. Alteração para aceitar múltiplos PDFs
arquivos = st.file_uploader("2. Envie os PDFs dos pedidos", type=["pdf"], accept_multiple_files=True)

if st.button("🚀 Processar Pedidos", use_container_width=True, type="primary", disabled=not arquivos or not sel_display):
    cliente_original = opcoes_clientes[sel_display]
    c_info = clientes_df[clientes_df['cliente'] == cliente_original].iloc[0]
    
    lista_dfs = [] # Lista para guardar os resultados de cada PDF
    
    for arquivo in arquivos:
        texto_pdf = extrair_texto_pdf(arquivo.read())
        f_info = identificar_fabrica(texto_pdf)
        
        if f_info is not None:
            df_individual = processar_pedido(texto_pdf, c_info['layout'], f_info)
            if not df_individual.empty:
                # Adiciona o nome do arquivo para você saber de qual pedido veio
                df_individual["arquivo_origem"] = arquivo.name
                lista_dfs.append(df_individual)
        else:
            st.error(f"❌ Fábrica não identificada no arquivo: {arquivo.name}")

    # Junta todos os PDFs processados em um único DataFrame
    if lista_dfs:
        df_final = pd.concat(lista_dfs, ignore_index=True)
        
        st.success(f"✅ {len(lista_dfs)} pedido(s) processado(s) com sucesso!")
        st.dataframe(df_final, use_container_width=True)
        
        # Download do consolidado
        csv = df_final.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Baixar Tudo em CSV (Consolidado)",
            data=csv,
            file_name=f"pedidos_consolidados_{cliente_original}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning("⚠️ Nenhum item foi extraído dos arquivos enviados.")
