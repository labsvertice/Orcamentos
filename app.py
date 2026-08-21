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
    page_title="Nutribook — Portal do Consultório",
    page_icon="🍎",
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
    st.caption("Vamos iniciar o próximo Nutribook?")
    st.divider()
    
    menu = st.radio(
        "Navegação do Consultório:",
        ["➕ Novo Nutribook", "📋 Painel Nutribook"],
        index=0
    )

# =================================================================================
# 3. CONTEÚDO PRINCIPAL
# =================================================================================

if menu == "➕ Novo Nutribook":
    st.title("🍎 Novo Nutribook")
    st.write("Preencha as informações do paciente e anexe o plano em PDF para disparar a geração.")
    
    with st.form("form_nutribook", clear_on_submit=True):
        st.subheader("Dados do Paciente")
        col_nome, col_email = st.columns(2)
        with col_nome:
            nome_paciente = st.text_input("Nome do Paciente *")
        with col_email:
            email_paciente = st.text_input("E-mail do Paciente")
        
        st.subheader("Perfis / Protocolos do Paciente")
        lista_protocolos = [
            "Fertilidade Feminina",
            "Emagrecimento & Definição",
            "Hipertrofia & Ganho de Massa",
            "Reeducação Alimentar & Saúde Geral",
            "Saúde Intestinal (Disbiose / FODMAPs)",
            "Saúde da Mulher (SOP / Endometriose)",
            "Controle Metabólico (Diabetes / Colesterol)",
            "Performance Esportiva",
            "Alimentação Plant-Based (Veg/Vegano)",
            "Gestante & Lactante",
            "Longevidade & Saúde Sênior",
            "Guia Prático & Orientações Gerais"
        ]
        
        protocolos_selecionados = []
        col_proto1, col_proto2 = st.columns(2)
        metade = (len(lista_protocolos) + 1) // 2
        
        with col_proto1:
            for p in lista_protocolos[:metade]:
                if st.checkbox(p, key=p):
                    protocolos_selecionados.append(p)
                    
        with col_proto2:
            for p in lista_protocolos[metade:]:
                if st.checkbox(p, key=p):
                    protocolos_selecionados.append(p)
        
        st.subheader("Plano Alimentar Base")
        pdf_file = st.file_uploader("Upload do Plano Alimentar Base (PDF):", type=["pdf"])
        
        submitted = st.form_submit_button("CRIAR NUTRIBOOK")
        
        if submitted:
            if nome_paciente and pdf_file:
                if WEBAPP_URL == "SUA_URL_DO_WEB_APP_AQUI":
                    st.error("Por favor, configure a URL do seu Apps Script Web App no código.")
                else:
                    with st.spinner("Enviando arquivo e registrando pedido..."):
                        file_bytes = base64.b64encode(pdf_file.getvalue()).decode('utf-8')
                        protocolos_str = ", ".join(protocolos_selecionados) if protocolos_selecionados else "Padrão"
                        
                        payload = {
                            "nome": nome_paciente,
                            "email": email_paciente,
                            "protocolos": protocolos_str,
                            "fileName": pdf_file.name,
                            "fileBytes": file_bytes
                        }
                        
                        response = requests.post(WEBAPP_URL, json=payload)
                        
                        if response.status_code == 200 and response.json().get("status") == "success":
                            st.success(f"✅ Nutribook para **{nome_paciente}** registrado com sucesso!")
                        else:
                            st.error(f"Erro ao registrar: {response.text}")
            else:
                st.error("Por favor, preencha o Nome do Paciente e selecione um arquivo PDF.")

elif menu == "📋 Painel Nutribook":
    st.title("📄 Painel Nutribook")
    st.write("Acompanhe os indicadores de geração, faturamento e histórico completo.")
    st.divider()
    
    df_dados = carregar_dados_planilha()
    
    if df_dados is not None and not df_dados.empty:
        col_status = "Status" if "Status" in df_dados.columns else df_dados.columns[-1]
        col_data = "Carimbo de data/hora" if "Carimbo de data/hora" in df_dados.columns else df_dados.columns[0]
        
        df_dados['Data_Parsed'] = pd.to_datetime(df_dados[col_data], dayfirst=True, errors='coerce')
        df_concluidos = df_dados[df_dados[col_status].astype(str).str.strip().str.lower() == 'concluído']
        
        VALOR_NUTRIBOOK = 5.00
        total_historico = len(df_concluidos)
        agora = pd.Timestamp.now()
        
        df_mes_atual = df_concluidos[
            (df_concluidos['Data_Parsed'].dt.month == agora.month) & 
            (df_concluidos['Data_Parsed'].dt.year == agora.year)
        ]
        total_mes = len(df_mes_atual)
        
        faturamento_mes = total_mes * VALOR_NUTRIBOOK
        faturamento_total = total_historico * VALOR_NUTRIBOOK

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1: st.metric("Total Concluídos (Geral)", f"{total_historico}")
        with kpi2: st.metric("Concluídos no Mês", f"{total_mes}")
        with kpi3: st.metric("Faturamento Mês Atual", f"R$ {faturamento_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        with kpi4: st.metric("Faturamento Acumulado", f"R$ {faturamento_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        st.markdown("---")
        st.subheader("📈 Evolução Mensal (Nutribooks Concluídos)")
        
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
        st.subheader("📋 Histórico de Pedidos")
        
        status_unicos = list(df_dados[col_status].dropna().unique())
        status_filtro = st.selectbox("Filtrar por Status:", ["Todos"] + status_unicos)
        
        df_exibicao = df_dados.copy()
        if status_filtro != "Todos":
            df_exibicao = df_exibicao[df_exibicao[col_status] == status_filtro]

        # Busca dinâmica das colunas sem duplicatas
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
        if c_nome: mapa_colunas[c_nome] = "Nome do Paciente"
        if c_email: mapa_colunas[c_email] = "E-mail do Paciente"
        if c_perfil: mapa_colunas[c_perfil] = "Perfil / Protocolo"
        if c_link: mapa_colunas[c_link] = "Link Nutribook"
        if c_status: mapa_colunas[c_status] = "Status"

        cols_origem = list(mapa_colunas.keys())
        df_final = df_exibicao[cols_origem].rename(columns=mapa_colunas)

        for col in df_final.columns:
            if col != "Link Nutribook":
                df_final[col] = df_final[col].fillna("").astype(str).replace({'None': '', 'nan': '', '<NA>': ''})

        config_colunas = {}
        if "Link Nutribook" in df_final.columns:
            config_colunas["Link Nutribook"] = st.column_config.LinkColumn(
                "Link Nutribook",
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
