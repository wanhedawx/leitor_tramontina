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
# CONFIG DA PÁGINA (Atualizado para Wide)
# =========================
st.set_page_config(
    page_title="Leitor de Pedidos Tramontina",
    page_icon="📄",
    layout="wide" # Ocupa toda a largura da tela
)


# =========================
# UTIL
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
# LEITURA DAS ABAS
# =========================
@st.cache_data
def carregar_fabricas():
    df = pd.read_excel(CONFIG_PATH, sheet_name="fabricas", dtype=str)
    df.columns = [str(c).strip().lower() for c in df.columns]

    colunas_necessarias = {"cnpj", "fabrica", "operacao", "desconto"}
    faltando = colunas_necessarias - set(df.columns)
    if faltando:
        raise ValueError(f"Na aba 'fabricas' faltam colunas: {', '.join(faltando)}")

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

    colunas_necessarias = {"cnpj_cliente", "cliente", "layout", "regra_embalagem"}
    faltando = colunas_necessarias - set(df.columns)
    if faltando:
        raise ValueError(f"Na aba 'clientes' faltam colunas: {', '.join(faltando)}")

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

    colunas_necessarias = {"sku", "embalagem"}
    faltando = colunas_necessarias - set(df.columns)
    if faltando:
        raise ValueError(f"Na aba 'embalagem' faltam colunas: {', '.join(faltando)}")

    df["sku"] = df["sku"].astype(str).str.replace(r"\D", "", regex=True)
    df["embalagem"] = pd.to_numeric(df["embalagem"], errors="coerce")

    return df[["sku", "embalagem"]].drop_duplicates()


# =========================
# IDENTIFICAÇÃO
# =========================
def listar_clientes_para_tela():
    df_clientes = carregar_clientes()

    clientes_originais = (
        df_clientes["cliente"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    clientes_formatados = []

    for cliente in clientes_originais:
        nome = cliente.replace("_", " ")
        nome = " ".join(p.capitalize() for p in nome.split())
        clientes_formatados.append(nome)

    return sorted(clientes_formatados)


def identificar_cliente_por_selecao(cliente_selecionado):
    df_clientes = carregar_clientes()

    cliente_normalizado = (
        cliente_selecionado
        .strip()
        .lower()
        .replace(" ", "_")
    )

    linha = df_clientes[
        df_clientes["cliente"].str.strip().str.lower() == cliente_normalizado
    ]

    if linha.empty:
        raise ValueError(f"Cliente '{cliente_selecionado}' não encontrado na aba 'clientes'.")

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
# PALATO
# =========================
def extrair_itens_palato(texto):
    linhas = texto.splitlines()
    itens = []

    for linha in linhas:
        if "Tramontina" not in linha:
            continue

        sku = re.search(r"\b\d{7,8}\b", linha)
        emb = re.search(r"(CX|UN)/(\d+)", linha)
        qtd = re.search(r"\s(\d+)\s+(CX|UN)/", linha)

        if sku:
            itens.append({
                "sku": sku.group(),
                "embalagem": emb.group(2) if emb else None,
                "quantidade": qtd.group(1) if qtd else None
            })

    df = pd.DataFrame(itens)

    if not df.empty:
        df["embalagem"] = pd.to_numeric(df["embalagem"], errors="coerce")
        df["quantidade"] = pd.to_numeric(df["quantidade"], errors="coerce")

    return df


def montar_saida_palato(texto, regra_fabrica):
    df = extrair_itens_palato(texto)

    if df.empty:
        return df

    df["origem"] = regra_fabrica["operacao"]
    df["desconto"] = regra_fabrica["desconto"]

    return df[["sku", "quantidade", "origem", "desconto"]]


# =========================
# CARAJÁS
# =========================
def normalizar_sku(valor):
    return re.sub(r"\D", "", str(valor))


def extrair_itens_carajas(texto):
    linhas = texto.splitlines()
    itens = []

    for i, linha in enumerate(linhas):
        linha = linha.strip()

        m = re.match(
            r"^\d+\s+\d+\s+\d{13}\s+(\d[\d ]+)\s+.+?\-\s+(\d+)",
            linha
        )

        if m:
            itens.append({
                "sku": normalizar_sku(m.group(1)),
                "quantidade": m.group(2)
            })
            continue

        sku = re.search(r"\b\d{8}\b", linha)
        if sku:
            bloco = "\n".join(linhas[i:i+5])
            qtd = re.search(r"Qtd:\s*(\d+)", bloco)

            if qtd:
                itens.append({
                    "sku": normalizar_sku(sku.group()),
                    "quantidade": qtd.group(1)
                })

    df = pd.DataFrame(itens)

    if not df.empty:
        df["sku"] = df["sku"].astype(str).str.replace(r"\D", "", regex=True)
        df["quantidade"] = pd.to_numeric(df["quantidade"], errors="coerce")
        df = df.drop_duplicates()

    return df


def montar_saida_carajas(texto, regra_fabrica):
    df = extrair_itens_carajas(texto)

    if df.empty:
        return df

    df_emb = carregar_embalagem()
    df = df.merge(df_emb, on="sku", how="left")

    df["origem"] = regra_fabrica["operacao"]
    df["desconto"] = regra_fabrica["desconto"]

    return df[["sku", "quantidade", "origem", "desconto"]]


# =========================
# CASA VIEIRA
# =========================
def montar_saida_casa_vieira(texto, regra_fabrica):
    linhas = texto.splitlines()
    itens = []

    padrao = re.compile(
        r"^(\d{13})\s+"
        r"(\d{5,8})\s+"
        r"(\d+)\s+"
