import streamlit as st
import pandas as pd
import requests
import base64
from streamlit_gsheets import GSheetsConnection

# COLE AQUI A URL DO SEU APP WEB DO GOOGLE APPS SCRIPT
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbz7Pnyk2eCsURm-9-WKlluYJAFK_jj_Zd2FqM3KAJVe5zdNrAoI5ak8nmf_XOC2qxY/exec"

# =================================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E CSS
# =================================================================================
st.set_page_config(
    page_title="Orçamento — Portal Comercial",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stApp { background-color: #E2E8E2 !important; }
    
    /* Oculta o cabeçalho padrão mantendo o espaço do topo equilibrado */
    header[data-testid="stHeader"], [data-testid="stHeader"], header {
        display: none !important;
        height: 0px !important;
    }
    
    .main .block-container, [data-testid="stMainBlockContainer"] {
        padding-top: 2rem !important;
        margin-top: -1.5rem !important;
        padding-bottom: 2rem !important;
    }
    
    [data-testid="stSidebarContent"] {
        padding-top: 2rem !important;
    }

    div.stButton > button, div.stFormSubmitButton > button {
        background-color: #2A5C36 !important;
        color: #FFFFFF !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 10px 24px !important;
        transition: all 0.3s ease !important;
        width: 100%;
    }
    
    div.stButton > button:hover, div.stFormSubmitButton > button:hover {
        background-color: #1E4327 !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(42, 92, 54, 0.25) !important;
    }

    h1, h2, h3 { color: #112214 !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] { background-color: #D3DDD3 !important; border-right: 1px solid #C1CDC1; }
    </style>
""", unsafe_allow_html=True)

# Conexão GSheets para leitura do Painel
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados_planilha():
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = df.columns.astype(str).str.strip()
        return df
    except Exception:
        return None

# =================================================================================
# 2. SIDEBAR / NAV
# =================================================================================
with st.sidebar:
    st.image("logo.png", width=160)
    st.markdown("#### Olá, **Jean Victor**! 👋")
    st.caption("Vamos emitir o próximo orçamento?")
    st.divider()
    
    menu = st.radio(
        "Navegação Comercial:",
        ["➕ Novo Orçamento", "📋 Painel de Orçamentos"],
        index=0
    )

# =================================================================================
# 3. CONTEÚDO PRINCIPAL
# =================================================================================

if menu == "➕ Novo Orçamento":
    st.title("📊 Novo Orçamento")
    st.write("Preencha as informações do cliente e anexe a proposta em PDF para disparar a geração.")
    
    with st.form("form_orcamento", clear_on_submit=True):
        st.subheader("Dados do Cliente")
        col_nome, col_email = st.columns(2)
        with col_nome:
            nome_cliente = st.text_input("Nome do Cliente *")
        with col_email:
            email_cliente = st.text_input("E-mail do Cliente")
        
        st.subheader("Escopo / Detalhes da Proposta")
        lista_opcoes = [
            "Projeto Executivo Completo",
            "Consultoria e Gestão",
            "Reforma Comercial",
            "Reforma Residencial",
            "Planejamento de Etapas",
            "Laudo Técnico & Vistoria",
            "Assessoria de Instalações",
            "Gestão de Insumos & Materiais",
            "Escopo Personalizado"
        ]
        
        opcoes_selecionadas = []
        col_opt1, col_opt2 = st.columns(2)
        metade = (len(lista_opcoes) + 1) // 2
        
        with col_opt1:
            for o in lista_opcoes[:metade]:
                if st.checkbox(o, key=o):
                    opcoes_selecionadas.append(o)
                    
        with col_opt2:
            for o in lista_opcoes[metade:]:
                if st.checkbox(o, key=o):
                    opcoes_selecionadas.append(o)
        
        st.subheader("Documento Base da Proposta")
        pdf_file = st.file_uploader("Upload do Orçamento / Escopo Base (PDF):", type=["pdf"])
        
        submitted = st.form_submit_button("CRIAR ORÇAMENTO")
        
        if submitted:
            if nome_cliente and pdf_file:
                if WEBAPP_URL == "SUA_URL_DO_WEB_APP_AQUI":
                    st.error("Por favor, configure a URL do seu Apps Script Web App no código.")
                else:
                    with st.spinner("Enviando arquivo e registrando pedido..."):
                        file_bytes = base64.b64encode(pdf_file.getvalue()).decode('utf-8')
                        detalhes_str = ", ".join(opcoes_selecionadas) if opcoes_selecionadas else "Padrão"
                        
                        payload = {
                            "nome": nome_cliente,
                            "email": email_cliente,
                            "protocolos": detalhes_str,
                            "fileName": pdf_file.name,
                            "fileBytes": file_bytes
                        }
                        
                        response = requests.post(WEBAPP_URL, json=payload)
                        
                        if response.status_code == 200 and response.json().get("status") == "success":
                            st.success(f"✅ Orçamento para **{nome_cliente}** registrado com sucesso!")
                        else:
                            st.error(f"Erro ao registrar: {response.text}")
            else:
                st.error("Por favor, preencha o Nome do Cliente e selecione um arquivo PDF.")

elif menu == "📋 Painel de Orçamentos":
    st.title("📋 Painel de Orçamentos")
    st.write("Acompanhe os indicadores de emissão, faturamento e histórico completo.")
    st.divider()
    
    df_dados = carregar_dados_planilha()
    
    if df_dados is not None and not df_dados.empty:
        col_status = "Status" if "Status" in df_dados.columns else df_dados.columns[-1]
        col_data = "Carimbo de data/hora" if "Carimbo de data/hora" in df_dados.columns else df_dados.columns[0]
        
        df_dados['Data_Parsed'] = pd.to_datetime(df_dados[col_data], dayfirst=True, errors='coerce')
        df_concluidos = df_dados[df_dados[col_status].astype(str).str.strip().str.lower() == 'concluído']
        
        VALOR_UNIDADE = 200.00  # Exemplo de valor por lote/mensalidade de orçamento
        total_historico = len(df_concluidos)
        agora = pd.Timestamp.now()
        
        df_mes_atual = df_concluidos[
            (df_concluidos['Data_Parsed'].dt.month == agora.month) & 
            (df_concluidos['Data_Parsed'].dt.year == agora.year)
        ]
        total_mes = len(df_mes_atual)
        
        faturamento_mes = total_mes * VALOR_UNIDADE
        faturamento_total = total_historico * VALOR_UNIDADE

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1: st.metric("Total Concluídos (Geral)", f"{total_historico}")
        with kpi2: st.metric("Concluídos no Mês", f"{total_mes}")
        with kpi3: st.metric("Faturamento Mês Atual", f"R$ {faturamento_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        with kpi4: st.metric("Faturamento Acumulado", f"R$ {faturamento_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        st.markdown("---")
        st.subheader("📈 Evolução Mensal (Orçamentos Concluídos)")
        
        if not df_concluidos.empty and df_concluidos['Data_Parsed'].notna().any():
            df_grafico = (
                df_concluidos.dropna(subset=['Data_Parsed'])
                .groupby(df_concluidos['Data_Parsed'].dt.to_period('M'))
                .size()
                .reset_index(name='Quantidade')
            )
            df_grafico['Mês/Ano'] = df_grafico['Data_Parsed'].astype(str)
            st.bar_chart(df_grafico.set_index('Mês/Ano')[['Quantidade']], height=260)

        st.markdown("---")
        st.subheader("📋 Histórico de Orçamentos")
        
        status_unicos = list(df_dados[col_status].dropna().unique())
        status_filtro = st.selectbox("Filtrar por Status:", ["Todos"] + status_unicos)
        
        df_exibicao = df_dados.copy()
        if status_filtro != "Todos":
            df_exibicao = df_exibicao[df_exibicao[col_status] == status_filtro]

        c_data = next((c for c in df_exibicao.columns if 'carimbo' in c.lower() or 'data' in c.lower()), None)
        c_nome = next((c for c in df_exibicao.columns if 'nome' in c.lower()), None)
        c_email = next((c for c in df_exibicao.columns if 'email' in c.lower() or 'e-mail' in c.lower()), None)
        c_perfil = next((c for c in df_exibicao.columns if 'perfil' in c.lower() or 'protocolo' in c.lower()), None)
        c_link = next((c for c in df_exibicao.columns if 'link' in c.lower()), None)
        if not c_link:
            c_link = next((c for c in df_exibicao.columns if 'upload' in c.lower()), None)
        c_status = next((c for c in df_exibicao.columns if 'status' in c.lower()), None)

        mapa_colunas = {}
        if c_data: mapa_colunas[c_data] = "Carimbo de data/hora"
        if c_nome: mapa_colunas[c_nome] = "Nome do Cliente"
        if c_email: mapa_colunas[c_email] = "E-mail do Cliente"
        if c_perfil: mapa_colunas[c_perfil] = "Escopo / Detalhes"
        if c_link: mapa_colunas[c_link] = "Link do Orçamento"
        if c_status: mapa_colunas[c_status] = "Status"

        cols_origem = list(mapa_colunas.keys())
        df_final = df_exibicao[cols_origem].rename(columns=mapa_colunas)

        for col in df_final.columns:
            if col != "Link do Orçamento":
                df_final[col] = df_final[col].fillna("").astype(str).replace({'None': '', 'nan': '', '<NA>': ''})

        config_colunas = {}
        if "Link do Orçamento" in df_final.columns:
            config_colunas["Link do Orçamento"] = st.column_config.LinkColumn(
                "Link do Orçamento",
                display_text="🔗"
            )

        st.dataframe(
            df_final,
            use_container_width=True,
            hide_index=True,
            column_config=config_colunas
        )
    else:
        st.info("Nenhum dado encontrado na planilha do Google Sheets.")
