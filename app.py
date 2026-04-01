import io
import re
from pathlib import Path
from PIL import Image

import pandas as pd
import pdfplumber
import streamlit as st
import os

BASE_DIR = Path(__file__).resolve().parent
INFOS_DIR = BASE_DIR / "infos"
CONFIG_PATH = INFOS_DIR / "regras_fabricas.xlsx"
LOGO_PATH = INFOS_DIR / "logo.png"

# =========================
# CONFIG DA PÁGINA
# =========================
st.set_page_config(
    page_title="Leitor de Pedidos Tramontina",
    page_icon="📄",
    layout="wide"
)

# =========================
# UTILITÁRIOS
# =========================
def extrair_texto_pdf_bytes(pdf_bytes: bytes) -> str:
    texto = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for pagina in pdf.pages:
            texto_pagina = pagina.extract_text()
            if texto_pagina:
                texto += texto_pagina + "\n"
    return texto

def limpar_cnpj(valor):
    numeros = re.sub(r"\D", "", str(valor))
    return numeros.zfill(14)

def extrair_todos_cnpjs(texto):
    texto_limpo = texto.replace("\n", " ")
    padrao_mask = r"\d{2}\s*\.?\s*\d{3}\s*\.?\s*\d{3}\s*/?\s*\d{4}\s*-?\s*\d{2}"
    encontrados_mask = re.findall(padrao_mask, texto_limpo)
    encontrados_puros = re.findall(r"(?:\d\s*){14}", texto_limpo)
    todos = encontrados_mask + encontrados_puros
    todos = [limpar_cnpj(c) for c in todos if limpar_cnpj(c)]
    todos = [c for c in todos if len(c) == 14]
    vistos = set()
    resultado = []
    for c in todos:
        if c not in vistos:
            vistos.add(c)
            resultado.append(c)
    return resultado

def extrair_numero_pedido(texto):
    padroes = [
        r"PEDIDO DE COMPRA\s+L?(\d+)",
        r"Número do Pedido:\s*(\d+)",
        r"Pedido\s*[:\-]?\s*(\d+)",
    ]
    for padrao in padroes:
        m = re.search(padrao, texto, re.IGNORECASE)
        if m:
            return m.group(1)
    return "sem_numero"

def dataframe_para_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="saida")
    output.seek(0)
    return output.getvalue()

# =========================
# CARREGAMENTO DE DADOS
# =========================
@st.cache_data
def carregar_fabricas():
    df = pd.read_excel(CONFIG_PATH, sheet_name="fabricas", dtype=str)
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.dropna(subset=["cnpj", "fabrica", "operacao", "desconto"])
    df["cnpj"] = df["cnpj"].astype(str).apply(limpar_cnpj)
    df["fabrica"] = df["fabrica"].astype(str).str.strip().str.lower()
    df["operacao"] = df["operacao"].astype(str).str.strip()
    df["desconto"] = pd.to_numeric(df["desconto"], errors="coerce")
    return df

@st.cache_data
def carregar_clientes():
    df = pd.read_excel(CONFIG_PATH, sheet_name="clientes", dtype=str)
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.dropna(subset=["cliente", "layout", "regra_embalagem"])
    df["cnpj_cliente"] = df["cnpj_cliente"].fillna("").astype(str).apply(limpar_cnpj)
    df["cliente"] = df["cliente"].astype(str).str.strip().str.lower()
    df["layout"] = df["layout"].astype(str).str.strip().str.lower()
    df["regra_embalagem"] = df["regra_embalagem"].astype(str).str.strip().str.lower()
    return df

@st.cache_data
def carregar_embalagem():
    df = pd.read_excel(CONFIG_PATH, sheet_name="embalagem", dtype=str)
    df.columns = [str(c).strip().lower() for c in df.columns]
    df["sku"] = df["sku"].astype(str).str.replace(r"\D", "", regex=True)
    df["embalagem"] = pd.to_numeric(df["embalagem"], errors="coerce")
    return df[["sku", "embalagem"]].drop_duplicates()

# =========================
# IDENTIFICAÇÃO
# =========================
def listar_clientes_para_tela():
    df_clientes = carregar_clientes()
    clientes_originais = df_clientes["cliente"].dropna().unique().tolist()
    return sorted([" ".join(p.capitalize() for p in c.replace("_", " ").split()) for c in clientes_originais])

def identificar_cliente_por_selecao(cliente_selecionado):
    df_clientes = carregar_clientes()
    cliente_normalizado = cliente_selecionado.strip().lower().replace(" ", "_")
    linha = df_clientes[df_clientes["cliente"].str.strip().str.lower() == cliente_normalizado]
    return linha.iloc[0]

def identificar_fabrica_por_base(texto):
    cnpjs_pdf = extrair_todos_cnpjs(texto)
    df_fabricas = carregar_fabricas()
    for cnpj in cnpjs_pdf:
        linha = df_fabricas[df_fabricas["cnpj"] == cnpj]
        if not linha.empty:
            return linha.iloc[0]
    return None

# =========================
# MÓDULOS DE EXTRAÇÃO
# =========================
def montar_saida_palato(texto, regra_fabrica):
    linhas = texto.splitlines()
    itens = []
    for linha in linhas:
        if "Tramontina" not in linha: continue
        sku = re.search(r"\b\d{7,8}\b", linha)
        qtd = re.search(r"\s(\d+)\s+(CX|UN)/", linha)
        if sku and qtd:
            itens.append({"sku": sku.group(), "quantidade": int(qtd.group(1))})
    df = pd.DataFrame(itens)
    if not df.empty:
        df["origem"] = regra_fabrica["operacao"]
        df["desconto"] = regra_fabrica["desconto"]
    return df

def montar_saida_carajas(texto, regra_fabrica):
    linhas = texto.splitlines()
    itens = []
    for i, linha in enumerate(linhas):
        m = re.match(r"^\d+\s+\d+\s+\d{13}\s+(\d[\d ]+)\s+.+?\-\s+(\d+)", linha.strip())
        if m:
            itens.append({"sku": re.sub(r"\D", "", m.group(1)), "quantidade": int(m.group(2))})
    df = pd.DataFrame(itens)
    if not df.empty:
        df["origem"] = regra_fabrica["operacao"]
        df["desconto"] = regra_fabrica["desconto"]
    return df

def montar_saida_casa_vieira(texto, regra_fabrica):
    linhas = texto.splitlines()
    itens = []
    padrao = re.compile(r"^(\d{13})\s+(\d{5,8})\s+(\d+)\s+(.+?)\s+(\d+)\s+0,00\s+([\d\.,]+)\s+([\d\.,]+)$")
    for linha in linhas:
        m = padrao.match(linha.strip())
        if m:
            itens.append({"sku": m.group(2), "quantidade": int(m.group(5))})
    df = pd.DataFrame(itens)
    if not df.empty:
        df["origem"] = regra_fabrica["operacao"]
        df["desconto"] = regra_fabrica["desconto"]
    return df

# =========================
# INTERFACE WEB
# =========================
if not CONFIG_PATH.exists():
    st.error(f"❌ Configuração não encontrada em: {CONFIG_PATH}")
    st.stop()

col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    if LOGO_PATH.exists():
        st.image(Image.open(str(LOGO_PATH)), width=150)
with col_titulo:
    st.title("Sistema de Processamento de Pedidos")
    st.write("---")

st.subheader("⚙️ Configuração")
c1, c2 = st.columns(2)
with c1:
    clientes = listar_clientes_para_tela()
    sel_cliente = st.selectbox("Cliente destino", clientes, index=None, placeholder="Selecione...")
with c2:
    arquivo = st.file_uploader("Pedido em PDF", type=["pdf"], disabled=(sel_cliente is None))

st.write("---")
_, col_btn, _ = st.columns([2, 1, 2])
with col_btn:
    if st.button("🚀 Processar Pedido", use_container_width=True, disabled=(not arquivo)):
        with st.spinner("Processando..."):
            texto = extrair_texto_pdf_bytes(arquivo.read())
            c_info = identificar_cliente_por_selecao(sel_cliente)
            f_info = identificar_fabrica_por_base(texto)
            
            if f_info is None:
                st.error("❌ Fábrica não identificada.")
                st.stop()

            layout = c_info["layout"]
            if layout == "palato": df = montar_saida_palato(texto, f_info)
            elif layout == "carajas": df = montar_saida_carajas(texto, f_info)
            elif layout == "casa_vieira": df = montar_saida_casa_vieira(texto, f_info)
            
            if df.empty:
                st.error("❌ Nenhum item encontrado.")
            else:
                st.success("✅ Sucesso!")
                st.dataframe(df, use_container_width=True)
                st.download_button("⬇️ Baixar Excel", dataframe_para_excel_bytes(df), f"pedido_{sel_cliente}.xlsx", use_container_width=True)
