import io
import re
import base64
from pathlib import Path
import pandas as pd
import pdfplumber
import streamlit as st

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Processador de Pedidos", page_icon="📄", layout="centered")

BASE_DIR = Path(__file__).resolve().parent
INFOS_DIR = BASE_DIR / "infos"
CONFIG_PATH = INFOS_DIR / "regras_fabricas.xlsx"
LOGO_PATH = INFOS_DIR / "logo_light.png"

# --- 2. FUNÇÕES ---
def get_image_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

@st.cache_data
def carregar_aba(aba):
    try:
        return pd.read_excel(CONFIG_PATH, sheet_name=aba, dtype=str)
    except:
        return pd.DataFrame()

def extrair_numero_pedido(nome_arquivo):
    numeros = re.findall(r"\d+", Path(nome_arquivo).stem)
    return max(numeros, key=len) if numeros else "SEM_NUMERO"

# --- 3. CSS: LOGO DINÂMICA ---
st.markdown(
    """
    <style>
    .logo-custom { width: 200px; display: block; margin: 0 auto; }
    @media (prefers-color-scheme: light) { .logo-custom { filter: invert(1) brightness(0.2); } }
    @media (prefers-color-scheme: dark) { .logo-custom { filter: none; } }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 4. INTERFACE ---
if LOGO_PATH.exists():
    img_b64 = get_image_base64(str(LOGO_PATH))
    st.markdown(f'<img src="data:image/png;base64,{img_b64}" class="logo-custom">', unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>Processador de Pedidos</h1>", unsafe_allow_html=True)
st.write("---")

# --- 5. LÓGICA DE PROCESSAMENTO ---
try:
    df_clientes = carregar_aba("clientes")
    if not df_clientes.empty:
        opcoes = {c.replace("_", " ").title(): c for c in df_clientes['cliente'].unique()}
        sel_display = st.selectbox("1. Selecione o Cliente", options=list(opcoes.keys()), index=None)
        arquivos = st.file_uploader("2. Envie os PDFs", type=["pdf"], accept_multiple_files=True)

        if st.button("🚀 Processar Pedidos", use_container_width=True, type="primary") and arquivos and sel_display:
            cliente_id = opcoes[sel_display]
            todos_itens_consolidados = []
            
            for arquivo in arquivos:
                num_pedido = extrair_numero_pedido(arquivo.name)
                dados_do_pdf = []
                
                with pdfplumber.open(io.BytesIO(arquivo.read())) as pdf:
                    for page in pdf.pages:
                        tabela = page.extract_table()
                        if tabela:
                            # Converte e já limpa colunas vazias ou duplicadas
                            df_temp = pd.DataFrame(tabela[1:], columns=tabela[0])
                            # RESOLUÇÃO DO ERRO: Resetando índice e garantindo colunas únicas
                            df_temp = df_temp.loc[:, ~df_temp.columns.duplicated()].copy()
                            df_temp = df_temp.reset_index(drop=True)
                            
                            df_temp['Pedido'] = num_pedido
                            df_temp['Cliente'] = sel_display
                            dados_do_pdf.append(df_temp)
                
                if dados_do_pdf:
                    # Junta as páginas do PDF ignorando os índices antigos para evitar o erro de Reindexing
                    df_final_pedido = pd.concat(dados_do_pdf, ignore_index=True)
                    todos_itens_consolidados.append(df_final_pedido)
                    
                    with st.expander(f"📄 Itens Extraídos: Pedido {num_pedido}", expanded=True):
                        st.dataframe(df_final_pedido, use_container_width=True)
                        st.download_button(
                            label=f"⬇️ Baixar CSV Pedido {num_pedido}",
                            data=df_final_pedido.to_csv(index=False).encode('utf-8'),
                            file_name=f"PEDIDO_{num_pedido}.csv",
                            mime="text/csv",
                            key=f"btn_{num_pedido}"
                        )

            if todos_itens_consolidados:
                st.write("---")
                # Consolidação final sem conflito de índices
                df_total = pd.concat(todos_itens_consolidados, ignore_index=True)
                st.subheader("📦 Arquivo Consolidado")
                st.dataframe(df_total, use_container_width=True)
                st.download_button(
                    label="💾 BAIXAR TODOS OS ITENS CONSOLIDADOS",
                    data=df_total.to_csv(index=False).encode('utf-8'),
                    file_name=f"CONSOLIDADO_{cliente_id.upper()}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    else:
        st.error("Configure os clientes no arquivo Excel para continuar.")

except Exception as e:
    st.error(f"Erro no processamento: {e}")
