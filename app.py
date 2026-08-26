import base64
import os
import pandas as pd
import requests
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# COLE A URL DO SEU WEB APP DO APPS SCRIPT AQUI
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbwxyKpNaItwSD3CvC-gKgVWnIirhuF5_eTUvN9fultN5ZvktRob9071ZHHzE333leGK/exec"

# CONFIGURAÇÕES DA EVOLUTION API
EVOLUTION_API_URL = "http://163.176.133.204:8080"
API_KEY = "nutribook_secret_key_2026"
INSTANCE_NAME = "nutribook"

# =================================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E CSS
# =================================================================================
st.set_page_config(
    page_title="Portal Comercial — Orçamentos",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #E2E8E2 !important; }
    header[data-testid="stHeader"], [data-testid="stHeader"], header { display: none !important; height: 0px !important; }
    .main .block-container, [data-testid="stMainBlockContainer"] { padding-top: 2rem !important; margin-top: -1.5rem !important; padding-bottom: 2rem !important; }
    [data-testid="stSidebarContent"] { padding-top: 2rem !important; }

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
        box-shadow: 0 4px 12px rgba(42, 92, 54, 0.25) !important;
    }
    h1, h2, h3 { color: #112214 !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] { background-color: #D3DDD3 !important; border-right: 1px solid #C1CDC1; }
    </style>
""",
    unsafe_allow_html=True,
)

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados_planilha():
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df.columns = df.columns.astype(str).str.strip()
        return df
    except Exception:
        return None

@st.cache_data(ttl=15)
def checar_status_whatsapp_rapido():
    try:
        res = requests.get(f"{EVOLUTION_API_URL}/instance/connectionState/{INSTANCE_NAME}", headers={"apikey": API_KEY}, timeout=3)
        if res.status_code == 200:
            return res.json().get("instance", {}).get("state", "disconnected") == "open"
    except Exception:
        pass
    return False

# =================================================================================
# 2. SIDEBAR / NAV
# =================================================================================
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=160)
    else:
        st.title("📊 Setor Reformas")

    st.markdown("#### Olá, **Jean Victor**! 👋")
    st.caption("Painel de Controle Comercial")
    st.divider()

    menu = st.radio(
        "Navegação Comercial:",
        ["➕ Novo Orçamento", "📋 Painel de Orçamentos", "📱 Conectar WhatsApp"],
        index=0,
    )

# =================================================================================
# 3. CONTEÚDO PRINCIPAL
# =================================================================================

if menu == "➕ Novo Orçamento":
    st.title("📊 Novo Orçamento")
    st.write("Preencha as informações abaixo para estruturar e disparar a proposta comercial.")

    wa_conectado = checar_status_whatsapp_rapido()
    badge_wa = "🟢 Conectado" if wa_conectado else "🔴 Desconectado"

    with st.form("form_orcamento", clear_on_submit=True):
        st.subheader("1. Dados do Cliente")
        col_nome, col_whatsapp = st.columns(2)
        with col_nome:
            nome_cliente = st.text_input("Nome do Cliente / Contratante *")
        with col_whatsapp:
            whatsapp_cliente = st.text_input(f"WhatsApp do Cliente (com DDD) * — {badge_wa}", placeholder="Ex: 5548999999999")

        st.subheader("2. Detalhes do Orçamento")
        resumo_servicos = st.text_area("Resumo dos Serviços *", placeholder="Ex: Reforma completa de um bar...")

        st.subheader("3. Valores e Itens")
        itens_valores = st.text_area("Itens, Quantidades e Valores da Obra *", placeholder="Ex:\n- Demolição | 1 un | R$ 1.500,00\n- Pintura | 120 m² | R$ 3.500,00")

        submitted = st.form_submit_button("CRIAR ORÇAMENTO")

        if submitted:
            if nome_cliente and whatsapp_cliente and resumo_servicos and itens_valores:
                if not WEBAPP_URL:
                    st.error("Por favor, configure a URL do seu Apps Script Web App no código.")
                else:
                    with st.spinner("Registrando e processando proposta..."):
                        try:
                            payload = {
                                "nome": nome_cliente,
                                "whatsapp": whatsapp_cliente,
                                "resumo": resumo_servicos,
                                "itens": itens_valores,
                                "instance": INSTANCE_NAME
                            }
                            response = requests.post(WEBAPP_URL, json=payload, timeout=30)
                            if response.status_code == 200 and response.json().get("status") == "success":
                                st.success(f"✅ Orçamento para **{nome_cliente}** registrado com sucesso!")
                            else:
                                st.error(f"Erro ao registrar: {response.text}")
                        except Exception as e:
                            st.error(f"Falha na comunicação: {e}")
            else:
                st.error("Por favor, preencha todos os campos obrigatórios (*).")

elif menu == "📋 Painel de Orçamentos":
    st.title("📋 Painel de Orçamentos")
    st.write("Acompanhe os indicadores de emissão e o histórico completo.")
    st.divider()

    df_dados = carregar_dados_planilha()

    if df_dados is not None and not df_dados.empty:
        df_dados = df_dados.copy()
        df_dados.columns = df_dados.columns.astype(str).str.strip()

        # Identificação dinâmica das colunas
        col_carimbo = next((c for c in df_dados.columns if "carimbo" in c.lower() or "data" in c.lower()), df_dados.columns[0])
        col_nome = next((c for c in df_dados.columns if "nome" in c.lower()), df_dados.columns[1])
        col_whats = next((c for c in df_dados.columns if "whatsapp" in c.lower() or "zap" in c.lower()), df_dados.columns[2])
        col_resumo = next((c for c in df_dados.columns if "resumo" in c.lower()), df_dados.columns[3])
        col_itens = next((c for c in df_dados.columns if "itens" in c.lower()), df_dados.columns[4])
        col_status = next((c for c in df_dados.columns if "status" in c.lower()), df_dados.columns[-2])
        
        # Procura coluna de link do PDF (se houver)
        col_pdf = next((c for c in df_dados.columns if "http" in c.lower() or "pdf" in c.lower() or "link" in c.lower()), None)

        df_dados["Data_Parsed"] = pd.to_datetime(df_dados[col_carimbo], dayfirst=True, errors="coerce")
        df_concluidos = df_dados[df_dados[col_status].astype(str).str.strip().str.lower().isin(["concluído", "concluido"])].copy()

        # Cálculo automático do Valor Total extraindo os preços dos itens (ex: R$ 1.500,00)
        import re
        def calcular_total(texto):
            if not isinstance(texto, str): return 0.0
            # Procura por padrões como R$ 1.500,00 ou 1500.00
            valores = re.findall(r'R\$\s*([\d\.]+,\d{2})', texto)
            total = 0.0
            for v in valores:
                v_limpo = v.replace('.', '').replace(',', '.')
                try:
                    total += float(v_limpo)
                except:
                    pass
            return total

        df_concluidos["Valor Total"] = df_concluidos[col_itens].apply(calcular_total)

        total_historico = len(df_concluidos)
        agora = pd.Timestamp.now()
        df_mes_atual = df_concluidos[(df_concluidos["Data_Parsed"].dt.month == agora.month) & (df_concluidos["Data_Parsed"].dt.year == agora.year)]
        total_mes = len(df_mes_atual)
        faturamento_mes = df_mes_atual["Valor Total"].sum()

        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1: st.metric("Total Concluídos", f"{total_historico}")
        with kpi2: st.metric("Concluídos no Mês", f"{total_mes}")
        with kpi3: st.metric("Volume no Mês", f"R$ {faturamento_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        st.markdown("---")
        st.subheader("📋 Histórico de Orçamentos Emitidos")

        # Monta DataFrame limpo para exibição
        df_exibir = pd.DataFrame()
        df_exibir["Data do Envio"] = df_concluidos["Data_Parsed"].dt.strftime("%d/%m/%Y %H:%M")
        df_exibir["Cliente"] = df_concluidos[col_nome]
        df_exibir["WhatsApp"] = df_concluidos[col_whats]
        df_exibir["Resumo do Serviço"] = df_concluidos[col_resumo]
        df_exibir["Valor Total"] = df_concluidos["Valor Total"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        if col_pdf:
            df_exibir["Proposta (PDF)"] = df_concluidos[col_pdf]
        else:
            df_exibir["Proposta (PDF)"] = "📄 Ver PDF"

        st.dataframe(
            df_exibir,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Proposta (PDF)": st.column_config.LinkColumn(
                    "Proposta (PDF)",
                    help="Clique para baixar ou abrir o PDF do orçamento",
                    display_text="📥 Abrir PDF"
                )
            }
        )
    else:
        st.info("Nenhum dado encontrado na planilha.")
        
elif menu == "📱 Conectar WhatsApp":
    st.title("📱 Status da Conexão WhatsApp")
    st.write("Gerencie a conexão da Evolution API para disparos automáticos de propostas[cite: 4].")
    st.divider()

    if st.button("🔄 Verificar Status / Gerar QR Code"):
        pass

    try:
        res_state = requests.get(f"{EVOLUTION_API_URL}/instance/connectionState/{INSTANCE_NAME}", headers={"apikey": API_KEY}, timeout=5)
        if res_state.status_code == 200:
            if res_state.json().get("instance", {}).get("state") == "open":
                st.success("🟢 **WhatsApp Conectado e Operacional!**")
            else:
                st.error("🔴 **WhatsApp Desconectado**")
                res_qr = requests.get(f"{EVOLUTION_API_URL}/instance/connect/{INSTANCE_NAME}", headers={"apikey": API_KEY}, timeout=5)
                if res_qr.status_code == 200:
                    base64_qr = res_qr.json().get("base64") or res_qr.json().get("code")
                    if base64_qr:
                        if "," in base64_qr: base64_qr = base64_qr.split(",")[1]
                        st.image(base64.b64decode(base64_qr), width=280)
    except Exception as e:
        st.error(f"Falha de conexão com a Evolution API: {e}")
