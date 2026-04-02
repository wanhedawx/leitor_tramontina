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

# --- FUNÇÕES DE BANCO DE DADOS (EXCEL) ---
def salvar_na_planilha(aba, novo_dado_dict):
    try:
        df_atual = pd.read_excel(CONFIG_PATH, sheet_name=aba)
        df_novo = pd.concat([df_atual, pd.DataFrame([novo_dado_dict])], ignore_index=True)
        with pd.ExcelWriter(CONFIG_PATH, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df_novo.to_excel(writer, sheet_name=aba, index=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def excluir_da_planilha(aba, coluna_id, valor_id):
    try:
        df_atual = pd.read_excel(CONFIG_PATH, sheet_name=aba)
        # Filtra mantendo apenas quem NÃO é o valor selecionado
        df_novo = df_atual[df_atual[coluna_id].astype(str) != str(valor_id)]
        with pd.ExcelWriter(CONFIG_PATH, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df_novo.to_excel(writer, sheet_name=aba, index=False)
        return True
    except Exception as e:
        st.error(f"Erro ao excluir: {e}")
        return False

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

# --- PROCESSAMENTO ---
def processar_pedido(texto, layout, f_info):
    itens = []
    # Lógica de extração simplificada
    if layout == "palato":
        for linha in texto.splitlines():
            if "Tramontina" in linha:
                sku = re.search(r"\b\d{7,8}\b", linha)
                qtd = re.search(r"\s(\d+)\s+(CX|UN)/", linha)
                if sku and qtd: itens.append({"sku": sku.group(), "quantidade": int(qtd.group(1))})
    elif layout == "carajas":
        for linha in texto.splitlines():
            m = re.match(r"^\d+\s+\d+\s+\d{13}\s+(\d[\d ]+)\s+.+?\-\s+(\d+)", linha.strip())
            if m: itens.append({"sku": re.sub(r"\D", "", m.group(1)), "quantidade": int(m.group(2))})
    
    df = pd.DataFrame(itens)
    if not df.empty:
        df["origem"] = f_info["operacao"]
        df["desconto"] = f_info["desconto"]
    return df

# --- INTERFACE ---
if LOGO_PATH.exists():
    _, col_img, _ = st.columns([1, 1, 1])
    col_img.image(Image.open(str(LOGO_PATH)), width=150)

st.markdown("<h1 style='text-align: center;'>Processador de Pedidos</h1>", unsafe_allow_html=True)
st.write("---")

# INPUTS
clientes_df = carregar_aba("clientes")
lista_clientes = sorted(clientes_df['cliente'].unique().tolist())
sel_cliente = st.selectbox("1. Selecione o Cliente", lista_clientes, index=None, placeholder="Escolha um cliente...")
arquivo = st.file_uploader("2. Envie o PDF do pedido", type=["pdf"])

if st.button("🚀 Processar Pedido", use_container_width=True, type="primary", disabled=not arquivo):
    texto_pdf = extrair_texto_pdf(arquivo.read())
    f_info = identificar_fabrica(texto_pdf)
    
    if f_info is None:
        st.error("❌ Fábrica não identificada no PDF.")
    else:
        c_info = clientes_df[clientes_df['cliente'] == sel_cliente].iloc[0]
        df_final = processar_pedido(texto_pdf, c_info['layout'], f_info)
        
        if df_final.empty:
            st.warning("⚠️ Nenhum item extraído.")
        else:
            st.success("✅ Processado!")
            st.dataframe(df_final, use_container_width=True)
            st.download_button("⬇️ Baixar Resultado", df_final.to_csv(index=False).encode('utf-8'), f"pedido_{sel_cliente}.csv", use_container_width=True)

# --- GERENCIAMENTO (ADICIONAR E EXCLUIR) ---
st.write("")
st.write("---")
with st.expander("📂 Gerenciar Base de Dados (Clientes/Itens)"):
    tab1, tab2, tab3 = st.tabs(["🆕 Adicionar Cliente", "🗑️ Excluir Cliente", "📦 Itens"])
    
    with tab1:
        with st.form("add_cliente"):
            n_nome = st.text_input("Nome do Cliente")
            n_layout = st.selectbox("Layout", ["carajas", "palato", "casa_vieira"])
            if st.form_submit_button("Salvar"):
                if n_nome:
                    novo = {"cnpj_cliente": "", "cliente": n_nome, "layout": n_layout, "regra_embalagem": "padrão"}
                    if salvar_na_planilha("clientes", novo):
                        st.success("Adicionado!")
                        st.cache_data.clear()
                        st.rerun()

    with tab2:
        st.warning("Cuidado: A exclusão é permanente.")
        cliente_para_excluir = st.selectbox("Selecione o cliente para remover", lista_clientes, key="del_sel")
        if st.button("❌ Confirmar Exclusão", use_container_width=True):
            if excluir_da_planilha("clientes", "cliente", cliente_para_excluir):
                st.success(f"{cliente_para_excluir} removido!")
                st.cache_data.clear()
                st.rerun()

    with tab3:
        st.info("Aqui você pode cadastrar SKUs novos na base de embalagem.")
        # ... (mesmo formulário de itens da versão anterior)
