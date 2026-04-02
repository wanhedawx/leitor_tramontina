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
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for p in pdf.pages:
                texto += (p.extract_text() or "") + "\n"
    except:
        pass
    return texto

def extrair_numero_pedido(texto, nome_arquivo):
    """
    Tenta extrair o número do pedido/OC do texto do PDF.
    Se falhar, tenta pegar do nome do próprio arquivo PDF.
    """
    # 1. Limpa ruídos comuns de leitura de PDF
    texto_limpo = texto.replace('\xa0', ' ')
    
    # 2. Padrões específicos (OC, Pedido, Compra)
    padroes_oc = [
        r"(?:OC|ORDEM|PEDIDO|COMPRA)\s*[:.\-]?\s*([a-zA-Z0-9]+)",
        r"N[º°º].?\s*([a-zA-Z0-9]+)"
    ]
    
    for padrao in padroes_oc:
        resultado = re.search(padrao, texto_limpo, re.IGNORECASE)
        if resultado:
            valor = resultado.group(1).strip()
            # Filtra se o resultado for muito curto ou apenas letras
            if len(valor) >= 3:
                return valor

    # 3. Se não achou no texto, tenta extrair apenas números do NOME DO ARQUIVO
    # (Ex: L75969.pdf -> 75969)
    numeros_nome = re.findall(r"\d+", nome_arquivo)
    if numeros_nome:
        return numeros_nome[0]
        
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
    col_esq, col_logo, col_dir = st.columns([1, 2, 1])
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
    ultimo_num_pedido = "0000"

    for arquivo in arquivos:
        conteudo = arquivo.read()
        texto_pdf = extrair_texto_pdf(conteudo)
        f_info = identificar_fabrica(texto_pdf)
        
        # PASSO CRÍTICO: Tenta pegar o número do texto OU do nome do arquivo
        num_pedido = extrair_numero_pedido(texto_pdf, arquivo.name)
        ultimo_num_pedido = num_pedido 

        if f_info is not None:
            df_individual = processar_pedido(texto_pdf, c_info['layout'], f_info)
            if not df_individual.empty:
                # NOME DO ARQUIVO: CARAJAS 75969
                nome_formatado = f"{sel_display.upper()} {num_pedido}"
                
                df_temp = df_individual.copy()
                df_temp["pedido"] = num_pedido
                df_temp["arquivo_origem"] = arquivo.name
                lista_dfs.append(df_temp)
                
                csv_buffer = io.StringIO()
                df_individual.to_csv(csv_buffer, index=False)
                arquivos_csv_zip[f"{nome_formatado}.csv"] = csv_buffer.getvalue()
        else:
            st.error(f"❌ Fábrica não identificada: {arquivo.name}")

    if lista_dfs:
        df_final = pd.concat(lista_dfs, ignore_index=True)
        st.success(f"✅ {len(lista_dfs)} pedido(s) processado(s)!")
        st.dataframe(df_final, use_container_width=True)
        
        cliente_venda = sel_display.upper()
        
        # Define o nome para o botão de download único
        if len(arquivos) == 1:
            nome_arquivo_final = f"{cliente_venda} {ultimo_num_pedido}"
        else:
            nome_arquivo_final = f"{cliente_venda} MULTIPLOS"

        st.write("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label=f"⬇️ Baixar {nome_arquivo_final}",
                data=df_final.to_csv(index=False).encode('utf-8'),
                file_name=f"{nome_arquivo_final}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            zip_io = io.BytesIO()
            with zipfile.ZipFile(zip_io, "w") as zf:
                for nome, conteudo_csv in arquivos_csv_zip.items():
                    zf.writestr(nome.upper(), conteudo_csv)
            
            st.download_button(
                label="📦 Baixar Separados (ZIP)",
                data=zip_io.getvalue(),
                file_name=f"PEDIDOS_{cliente_venda}.zip",
                mime="application/zip",
                use_container_width=True
            )
