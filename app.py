import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import pdfplumber
import re
import io
from PIL import Image
from pathlib import Path

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Tramontina - Gestor de Pedidos", layout="centered")

# Conexão com Google Sheets (Puxa os segredos do painel do Streamlit)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10) # Atualiza rápido para o cliente ver as mudanças
def carregar_aba(nome_aba):
    return conn.read(worksheet=nome_aba)

# --- LOGO E INTERFACE ---
BASE_DIR = Path(__file__).resolve().parent
# Tenta carregar a logo tanto na raiz quanto em /infos
LOGO_PATH = BASE_DIR / "logo.png" if (BASE_DIR / "logo.png").exists() else BASE_DIR / "infos" / "logo.png"

if LOGO_PATH.exists():
    _, col_img, _ = st.columns([1, 1, 1])
    col_img.image(Image.open(str(LOGO_PATH)), width=150)

st.markdown("<h1 style='text-align: center;'>Leitor de Pedidos Automático</h1>", unsafe_allow_html=True)

# --- CARREGAMENTO DAS BASES ---
try:
    df_clientes = carregar_aba("clientes")
    df_fabricas = carregar_aba("fabricas")
    df_embalagem = carregar_aba("embalagem")
except Exception as e:
    st.error("Erro ao conectar com o Google Sheets. Verifique os 'Secrets' no painel do Streamlit.")
    st.stop()

# --- ABAS DE NAVEGAÇÃO ---
menu = st.tabs(["📄 Processar Pedido", "📦 Gerenciar SKUs/Itens", "🏭 Fábricas & Descontos"])

with menu[0]:
    st.subheader("Processamento")
    sel_cliente = st.selectbox("Selecione o Cliente", df_clientes["cliente"].unique())
    arquivo_pdf = st.file_uploader("Suba o pedido em PDF", type="pdf")
    
    if st.button("🚀 Iniciar Leitura", use_container_width=True, type="primary"):
        if arquivo_pdf:
            with pdfplumber.open(arquivo_pdf) as pdf:
                texto = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            
            # 1. Identificar Fábrica pelo CNPJ no PDF
            f_info = None
            for _, fab in df_fabricas.iterrows():
                cnpj_limpo = re.sub(r"\D", "", str(fab['cnpj']))
                if cnpj_limpo in re.sub(r"\D", "", texto):
                    f_info = fab
                    break
            
            if not f_info:
                st.error("❌ Fábrica não identificada no PDF. Verifique o CNPJ na aba Fábricas.")
            else:
                # 2. Extrair SKUs (7-8 dígitos) e Quantidades
                # Procura o SKU e o primeiro número que aparece depois dele na linha
                dados_ped = []
                for linha in texto.splitlines():
                    sku_match = re.search(r"(\d{7,8})", linha)
                    if sku_match:
                        sku = sku_match.group(1)
                        # Busca quantidade (número isolado após o SKU)
                        qtd_match = re.search(r"\s(\d{1,4})\s", linha)
                        qtd = int(qtd_match.group(1)) if qtd_match else 1
                        dados_ped.append({"sku": sku, "quantidade": qtd})
                
                df_res = pd.DataFrame(dados_ped)
                if not df_res.empty:
                    # 3. Cruzamento de ORIGEM e DESCONTO (Vem da Fábrica identificada)
                    df_res["origem"] = f_info["operacao"]
                    df_res["desconto"] = f_info["desconto"]
                    
                    # 4. Cruzamento de EMBALAGEM (Vem da aba Embalagem)
                    df_res = df_res.merge(df_embalagem[['sku', 'embalagem']], on='sku', how='left')
                    df_res['embalagem'] = df_res['embalagem'].fillna("Não Cadastrado")
                    
                    st.success(f"✅ Lido com sucesso! Fábrica: {f_info['fabrica']}")
                    st.dataframe(df_res, use_container_width=True)
                    st.download_button("⬇️ Baixar Excel", df_res.to_csv(index=False).encode('utf-8'), "pedido_processado.csv")
                else:
                    st.warning("Nenhum SKU encontrado no formato Tramontina.")

with menu[1]:
    st.subheader("Gerenciar Banco de Dados")
    # Formulário para o cliente adicionar SKUs novos sem precisar de você
    with st.form("novo_sku"):
        st.write("Adicionar novo SKU ou Alterar Embalagem")
        c1, c2 = st.columns(2)
        in_sku = c1.text_input("SKU (Ex: 96589068)")
        in_emb = c2.number_input("Qtd Embalagem", min_value=1)
        if st.form_submit_button("Salvar no Google Sheets"):
            novo_item = pd.DataFrame([{"sku": str(in_sku), "embalagem": in_emb}])
            # Atualiza concatenando com o que já existe
            df_final = pd.concat([df_embalagem, novo_item], ignore_index=True).drop_duplicates(subset=['sku'], keep='last')
            conn.update(worksheet="embalagem", data=df_final)
            st.success("Base atualizada!")
            st.rerun()

with menu[2]:
    st.subheader("Regras de Fábrica")
    st.dataframe(df_fabricas, use_container_width=True)
    st.info("Para alterar descontos, o cliente pode editar diretamente a Planilha do Google.")
