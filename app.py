import io
import re
import zipfile
from pathlib import Path

import pandas as pd
import pdfplumber
import streamlit as st
from PIL import Image


# --- CONFIGURAÇÃO E CAMINHOS ---
BASE_DIR = Path(__file__).resolve().parent
INFOS_DIR = BASE_DIR / "infos"
CONFIG_PATH = INFOS_DIR / "regras_fabricas.xlsx"
LOGO_PATH = INFOS_DIR / "logo.png"


st.set_page_config(
    page_title="Processador de Pedidos Tramontina",
    page_icon="📄",
    layout="centered"
)


# --- FUNÇÕES ---
@st.cache_data
def carregar_aba(aba):
    if not CONFIG_PATH.exists():
        st.error(f"❌ Arquivo de configuração não encontrado: {CONFIG_PATH}")
        st.stop()

    return pd.read_excel(CONFIG_PATH, sheet_name=aba, dtype=str)


def extrair_texto_pdf(pdf_bytes):
    texto = ""

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for pagina in pdf.pages:
                texto += (pagina.extract_text() or "") + "\n"

    except Exception as e:
        st.error(f"❌ Erro ao ler PDF: {e}")

    return texto


def identificar_fabrica(texto):
    df_fabricas = carregar_aba("fabricas")

    texto_limpo = re.sub(r"\D", "", texto)

    for _, row in df_fabricas.iterrows():
        cnpj_limpo = re.sub(r"\D", "", str(row["cnpj"])).zfill(14)

        if cnpj_limpo in texto_limpo:
            return row

    return None


def processar_pedido(texto, layout, f_info):
    itens = []
    layout = str(layout).strip().lower()

    if layout == "palato":
        for linha in texto.splitlines():
            if "Tramontina" in linha:
                sku = re.search(r"\b\d{7,8}\b", linha)
                qtd = re.search(r"\s(\d+)\s+(CX|UN)/", linha)

                if sku and qtd:
                    itens.append({
                        "sku": sku.group(),
                        "quantidade": int(qtd.group(1))
                    })

    elif layout == "carajas":
        for linha in texto.splitlines():
            linha = linha.strip()

            m = re.match(
                r"^\d+\s+\d+\s+\d{13}\s+(\d[\d ]+)\s+.+?\-\s+(\d+)",
                linha
            )

            if m:
                sku = re.sub(r"\D", "", m.group(1))
                quantidade = int(m.group(2))

                itens.append({
                    "sku": sku,
                    "quantidade": quantidade
                })

    df = pd.DataFrame(itens)

    if not df.empty:
        df["origem"] = f_info["operacao"]
        df["desconto"] = f_info["desconto"]

    return df


def gerar_csv(df):
    return df.to_csv(index=False).encode("utf-8-sig")


def gerar_zip(arquivos_csv_zip):
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for nome_arquivo, conteudo_csv in arquivos_csv_zip.items():
            zf.writestr(nome_arquivo, conteudo_csv)

    return zip_buffer.getvalue()


# --- INTERFACE ---
if LOGO_PATH.exists():
    _, col_img, _ = st.columns([1, 1, 1])
    col_img.image(Image.open(str(LOGO_PATH)), width=150)

st.markdown(
    "<h1 style='text-align: center;'>Processador de Pedidos</h1>",
    unsafe_allow_html=True
)

st.write("---")


# --- CARREGAMENTO DE CLIENTES ---
try:
    clientes_df = carregar_aba("clientes")
except Exception as e:
    st.error(f"❌ Erro ao carregar aba clientes: {e}")
    st.stop()


if "cliente" not in clientes_df.columns:
    st.error("❌ A aba 'clientes' precisa ter a coluna 'cliente'.")
    st.stop()

if "layout" not in clientes_df.columns:
    st.error("❌ A aba 'clientes' precisa ter a coluna 'layout'.")
    st.stop()


opcoes_clientes = {
    str(c).replace("_", " ").title(): c
    for c in clientes_df["cliente"].dropna().unique()
}


sel_display = st.selectbox(
    "1. Selecione o Cliente",
    options=list(opcoes_clientes.keys()),
    index=None,
    placeholder="Escolha um cliente..."
)

arquivos = st.file_uploader(
    "2. Envie os PDFs dos pedidos",
    type=["pdf"],
    accept_multiple_files=True
)


# --- BOTÃO DE PROCESSAMENTO ---
processar = st.button(
    "🚀 Processar Pedidos",
    use_container_width=True,
    type="primary",
    disabled=not arquivos or not sel_display
)


if processar:
    cliente_original = opcoes_clientes[sel_display]

    c_info = clientes_df[clientes_df["cliente"] == cliente_original].iloc[0]

    lista_dfs = []
    arquivos_csv_zip = {}

    for arquivo in arquivos:
        st.write(f"📄 Processando: **{arquivo.name}**")

        conteudo = arquivo.read()
        texto_pdf = extrair_texto_pdf(conteudo)

        if not texto_pdf.strip():
            st.warning(f"⚠️ Não consegui extrair texto do PDF: {arquivo.name}")
            continue

        f_info = identificar_fabrica(texto_pdf)

        if f_info is None:
            st.error(f"❌ Fábrica não identificada: {arquivo.name}")
            continue

        df_individual = processar_pedido(
            texto=texto_pdf,
            layout=c_info["layout"],
            f_info=f_info
        )

        if df_individual.empty:
            st.warning(f"⚠️ Nenhum item extraído do arquivo: {arquivo.name}")
            continue

        nome_limpo = Path(arquivo.name).stem

        df_consolidado_parte = df_individual.copy()
        df_consolidado_parte["arquivo_origem"] = nome_limpo

        lista_dfs.append(df_consolidado_parte)

        csv_buffer = io.StringIO()
        df_individual.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
        arquivos_csv_zip[f"{nome_limpo}.csv"] = csv_buffer.getvalue()

        st.success(f"✅ Extraído com sucesso: {arquivo.name}")

    if lista_dfs:
        df_final = pd.concat(lista_dfs, ignore_index=True)

        st.write("---")
        st.success(f"✅ {len(lista_dfs)} pedido(s) processado(s)!")

        st.dataframe(df_final, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            csv_total = gerar_csv(df_final)

            st.download_button(
                label="⬇️ Baixar Tudo em CSV",
                data=csv_total,
                file_name=f"consolidado_{cliente_original}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col2:
            zip_bytes = gerar_zip(arquivos_csv_zip)

            st.download_button(
                label="📦 Baixar Separados em ZIP",
                data=zip_bytes,
                file_name=f"pedidos_separados_{cliente_original}.zip",
                mime="application/zip",
                use_container_width=True
            )

    else:
        st.warning("⚠️ Nenhum dado extraído dos PDFs enviados.")
