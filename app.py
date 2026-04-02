import io
import re
import pandas as pd
import pdfplumber
import streamlit as st
from pathlib import Path

# Configurações de Caminho
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "infos" / "regras_fabricas.xlsx"

# --- FUNÇÕES DE PERSISTÊNCIA (O coração da sua dúvida) ---
def atualizar_excel(aba, novo_df):
    """Sobrescreve a aba do Excel com os novos dados sem deletar as outras"""
    with pd.ExcelWriter(CONFIG_PATH, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        novo_df.to_excel(writer, sheet_name=aba, index=False)

@st.cache_data
def carregar_dados(aba):
    return pd.read_excel(CONFIG_PATH, sheet_name=aba)

# --- MOTOR DE LEITURA UNIVERSAL ---
def extrair_dados_padrao(texto, f_info, embalagem_df):
    """
    Procura SKUs (7-8 dígitos) e tenta capturar a quantidade próxima.
    Cruza com a base de embalagens e fábricas automaticamente.
    """
    itens = []
    # Expressão regular para achar SKU Tramontina (ex: 96589068)
    padrao_sku = re.compile(r"(\d{7,8})")
    
    linhas = texto.splitlines()
    for linha in linhas:
        sku_match = padrao_sku.search(linha)
        if sku_match:
            sku = sku_match.group(1)
            # Tenta achar um número de quantidade na mesma linha (geralmente após o SKU)
            qtd_match = re.search(r"(?<=\s)(\d{1,4})(?=\s|CX|UN)", linha)
            qtd = int(qtd_match.group(1)) if qtd_match else 1
            
            itens.append({"sku": sku, "quantidade": qtd})
    
    df = pd.DataFrame(itens)
    if not df.empty:
        # Cruzamento automático com as regras da fábrica
        df["origem"] = f_info["operacao"]
        df["desconto"] = f_info["desconto"]
        
        # Cruzamento opcional com base de embalagem
        df = df.merge(embalagem_df, on="sku", how="left")
        df["embalagem"] = df["embalagem"].fillna(1) # Padrão 1 se não existir
    
    return df

# --- INTERFACE VERTICAL ---
st.title("Sistema Automatizado de Pedidos")

# Carregamento inicial
clientes_df = carregar_dados("clientes")
fabricas_df = carregar_dados("fabricas")
embalagem_df = carregar_dados("embalagem")

cliente_nome = st.selectbox("Selecione o Cliente", clientes_df["cliente"].unique())
arquivo = st.file_uploader("Suba o PDF do Pedido", type="pdf")

if st.button("Processar Agora", type="primary"):
    if arquivo:
        with pdfplumber.open(arquivo) as pdf:
            texto_completo = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        
        # Identifica fábrica pelo CNPJ no texto
        f_info = None
        for _, fab in fabricas_df.iterrows():
            if str(fab["cnpj"]) in texto_completo.replace(".", "").replace("/", "").replace("-", ""):
                f_info = fab
                break
        
        if f_info is not None:
            resultado = extrair_dados_padrao(texto_completo, f_info, embalagem_df)
            st.dataframe(resultado)
            st.success(f"Pedido processado usando regras da {f_info['fabrica']}")
        else:
            st.error("Não achei o CNPJ da fábrica no PDF. Verifique se a fábrica está cadastrada.")

# --- ÁREA DE CADASTRO (Para não precisar mexer no GitHub) ---
with st.expander("➕ Cadastrar Novo Cliente ou Item"):
    aba_alvo = st.radio("O que deseja adicionar?", ["Cliente", "Item/Embalagem"])
    
    if aba_alvo == "Cliente":
        with st.form("form_cliente"):
            novo_n = st.text_input("Nome do Cliente")
            if st.form_submit_button("Salvar na Base"):
                nova_linha = pd.DataFrame([{"cliente": novo_n, "layout": "padrao"}])
                atualizar_excel("clientes", pd.concat([clientes_df, nova_linha]))
                st.success("Cliente salvo! Atualize a página.")
                st.cache_data.clear()
    
    else:
        with st.form("form_item"):
            n_sku = st.text_input("SKU")
            n_emb = st.number_input("Qtd Embalagem", min_value=1)
            if st.form_submit_button("Salvar Item"):
                nova_linha = pd.DataFrame([{"sku": n_sku, "embalagem": n_emb}])
                atualizar_excel("embalagem", pd.concat([embalagem_df, nova_linha]))
                st.success("Item salvo!")
                st.cache_data.clear()
