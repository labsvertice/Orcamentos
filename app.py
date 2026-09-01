import base64
import os
import re
import pandas as pd
import requests
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# URL DO SEU APP WEB DO GOOGLE APPS SCRIPT (ORÇAMENTOS)
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbwxyKpNaItwSD3CvC-gKgVWnIirhuF5_eTUvN9fultN5ZvktRob9071ZHHzE333leGK/exec"

# CONFIGURAÇÕES DA EVOLUTION API
# IMPORTANTE:
# O código legado do Proposta Inteligente veio com a instância "nutribook".
# Não alteramos esse valor sem o nome correto da instância do Proposta Inteligente.
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
""",
    unsafe_allow_html=True,
)

# =============================================================================
# GOOGLE SHEETS — CONEXÃO DIRETA VIA SERVICE ACCOUNT
# =============================================================================
#
# A autenticação é lida do Streamlit Secrets:
# [connections.gsheets]
#
# A planilha do projeto é a que você configurou nos Secrets.
# Não dependemos do st-gsheets-connection para as abas auxiliares.
# =============================================================================

SPREADSHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1B0w56eDkP9kT6a4o0eDS3Ll1qA5r1VYexBxbEZT38bU/edit"
)

SPREADSHEET_ID = "1B0w56eDkP9kT6a4o0eDS3Ll1qA5r1VYexBxbEZT38bU"

# GIDs confirmados pelo usuário.
USUARIOS_GID = 1751518313
EMPRESAS_GID = 751640019


def obter_google_sheets_service():
    """Cria o cliente autenticado do Google Sheets a partir do Secrets."""
    try:
        config = st.secrets["connections"]["gsheets"]

        required = [
            "type",
            "project_id",
            "private_key",
            "client_email",
            "token_uri",
        ]

        faltantes = [chave for chave in required if chave not in config]
        if faltantes:
            raise RuntimeError(
                "Secrets incompleto em [connections.gsheets]. "
                f"Faltando: {', '.join(faltantes)}"
            )

        service_account_info = {
            "type": config["type"],
            "project_id": config["project_id"],
            "private_key_id": config.get("private_key_id", ""),
            "private_key": config["private_key"],
            "client_email": config["client_email"],
            "client_id": config.get("client_id", ""),
            "auth_uri": config.get(
                "auth_uri",
                "https://accounts.google.com/o/oauth2/auth",
            ),
            "token_uri": config["token_uri"],
            "auth_provider_x509_cert_url": config.get(
                "auth_provider_x509_cert_url",
                "https://www.googleapis.com/oauth2/v1/certs",
            ),
            "client_x509_cert_url": config.get(
                "client_x509_cert_url",
                "",
            ),
        }

        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly",
            ],
        )

        return build(
            "sheets",
            "v4",
            credentials=credentials,
            cache_discovery=False,
        )

    except Exception as e:
        raise RuntimeError(
            f"Falha ao autenticar a Service Account do Google Sheets: {e}"
        ) from e


def ler_aba_sheets(nome_aba):
    """
    Lê uma aba inteira via Google Sheets API.
    O acesso é somente leitura nesta fase.
    """
    try:
        service = obter_google_sheets_service()

        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"'{nome_aba}'!A:Z",
            )
            .execute()
        )

        values = result.get("values", [])

        if not values:
            return pd.DataFrame()

        cabecalho = values[0]

        # Garante quantidade de colunas suficiente em todas as linhas.
        largura = max(
            len(cabecalho),
            max((len(linha) for linha in values[1:]), default=0),
        )

        cabecalho = list(cabecalho) + [
            f"Coluna_{i}"
            for i in range(len(cabecalho), largura)
        ]

        dados = []
        for linha in values[1:]:
            linha = list(linha) + [""] * (largura - len(linha))
            dados.append(linha[:largura])

        df = pd.DataFrame(dados, columns=cabecalho)
        df.columns = df.columns.astype(str).str.strip()

        return df

    except Exception as e:
        raise RuntimeError(
            f"Não foi possível ler a aba '{nome_aba}' "
            f"da planilha do Proposta Inteligente: {e}"
        ) from e


def carregar_dados_planilha():
    try:
        return ler_aba_sheets("Form_Responses")
    except Exception as e:
        st.error(f"Erro ao carregar Form_Responses: {e}")
        return None


def carregar_usuarios():
    try:
        return ler_aba_sheets("Usuarios")
    except Exception as e:
        st.error(
            f"Erro ao carregar a aba Usuarios "
            f"(GID {USUARIOS_GID}): {e}"
        )
        return None


def carregar_empresas():
    try:
        return ler_aba_sheets("Empresas")
    except Exception as e:
        st.error(
            f"Erro ao carregar a aba Empresas "
            f"(GID {EMPRESAS_GID}): {e}"
        )
        return None


def localizar_coluna(df, candidatos):
    if df is None or df.empty:
        return None

    mapa = {str(c).strip().lower(): c for c in df.columns}

    for candidato in candidatos:
        chave = str(candidato).strip().lower()
        if chave in mapa:
            return mapa[chave]

    return None


def valor_ativo(valor):
    return str(valor).strip().lower() in {
        "sim",
        "true",
        "1",
        "ativo",
        "yes",
    }


@st.cache_data(ttl=15)
def checar_status_whatsapp_rapido():
    """Consulta o status da Evolution API com cache curto de 15s."""
    try:
        url_state = f"{EVOLUTION_API_URL}/instance/connectionState/{INSTANCE_NAME}"
        headers = {"apikey": API_KEY}
        res = requests.get(url_state, headers=headers, timeout=3)
        if res.status_code == 200:
            state = res.json().get("instance", {}).get("state", "disconnected")
            return state == "open"
    except Exception:
        pass
    return False


def autenticar_usuario(login, senha):
    df = carregar_usuarios()

    if df is None or df.empty:
        return None, "Não foi possível carregar a aba Usuarios."

    c_login = localizar_coluna(df, ["Login"])
    c_senha = localizar_coluna(df, ["Senha"])
    c_nome = localizar_coluna(df, ["Nome"])
    c_empresa = localizar_coluna(df, ["Empresa_ID", "Empresa"])
    c_perfil = localizar_coluna(df, ["Perfil_Acesso", "Perfil"])
    c_ativo = localizar_coluna(df, ["Ativo"])
    c_usuario = localizar_coluna(df, ["Usuario_ID", "Usuario ID"])

    obrigatorias = {
        "Login": c_login,
        "Senha": c_senha,
        "Nome": c_nome,
        "Empresa_ID": c_empresa,
        "Perfil_Acesso": c_perfil,
        "Ativo": c_ativo,
    }

    faltantes = [nome for nome, coluna in obrigatorias.items() if not coluna]

    if faltantes:
        return None, (
            "A aba Usuarios está incompleta. "
            f"Colunas ausentes: {', '.join(faltantes)}."
        )

    login_normalizado = str(login or "").strip().lower()

    df["__login"] = (
        df[c_login]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    encontrados = df[df["__login"] == login_normalizado].copy()

    if encontrados.empty:
        return None, "Login ou senha inválidos."

    if len(encontrados) > 1:
        return None, "Este login está duplicado na aba Usuarios. Procure o suporte."

    registro = encontrados.iloc[0]

    if not valor_ativo(registro[c_ativo]):
        return None, "Este usuário está inativo no Proposta Inteligente."

    if str(senha or "") != str(registro[c_senha] or ""):
        return None, "Login ou senha inválidos."

    return {
        "usuario_id": str(registro[c_usuario]).strip() if c_usuario else "",
        "nome": str(registro[c_nome]).strip(),
        "login": login_normalizado,
        "empresa_ref": str(registro[c_empresa]).strip(),
        "perfil_acesso": str(registro[c_perfil]).strip(),
    }, None


def obter_empresa(empresa_ref):
    df = carregar_empresas()

    if df is None or df.empty:
        return None, "Não foi possível carregar a aba Empresas."

    c_id = localizar_coluna(df, ["Empresa_ID", "Empresa ID"])
    c_nome = localizar_coluna(df, ["Nome_Empresa", "Nome Empresa", "Empresa"])
    c_template = localizar_coluna(df, ["Template_ID", "Template ID"])
    c_pasta = localizar_coluna(df, ["Pasta_Destino_ID", "Pasta Destino ID"])
    c_ativo = localizar_coluna(df, ["Ativo"])
    c_cota = localizar_coluna(df, ["Cota"])

    if not c_id or not c_nome or not c_ativo:
        return None, (
            "A aba Empresas está incompleta. "
            "São esperadas: Empresa_ID, Nome_Empresa e Ativo."
        )

    referencia = str(empresa_ref or "").strip().lower()

    ids = df[c_id].fillna("").astype(str).str.strip().str.lower()
    nomes = df[c_nome].fillna("").astype(str).str.strip().str.lower()

    # Aceita tanto EMP001 quanto o nome da empresa no piloto.
    encontrados = df[(ids == referencia) | (nomes == referencia)].copy()

    if encontrados.empty:
        return None, (
            f"A empresa '{empresa_ref}' não foi encontrada na aba Empresas."
        )

    if len(encontrados) > 1:
        return None, (
            f"Existem múltiplas empresas correspondentes a '{empresa_ref}'."
        )

    registro = encontrados.iloc[0]

    if not valor_ativo(registro[c_ativo]):
        return None, "A empresa vinculada ao usuário está inativa."

    return {
        "empresa_id": str(registro[c_id]).strip(),
        "nome_empresa": str(registro[c_nome]).strip(),
        "template_id": str(registro[c_template]).strip() if c_template else "",
        "pasta_destino_id": str(registro[c_pasta]).strip() if c_pasta else "",
        "cota": registro[c_cota] if c_cota else "",
    }, None


def limpar_sessao():
    for chave in [
        "autenticado",
        "usuario_id",
        "usuario_nome",
        "usuario_login",
        "empresa_id",
        "empresa_nome",
        "perfil_acesso",
        "template_id",
        "pasta_destino_id",
        "cota_empresa",
    ]:
        st.session_state.pop(chave, None)


def tela_login():
    st.markdown("<div style='height: 70px;'></div>", unsafe_allow_html=True)

    _, centro, _ = st.columns([1, 1.1, 1])

    with centro:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=160)

        st.markdown(
            "<div style='text-align:center; color:#112214; font-size:30px; "
            "font-weight:700; margin:28px 0 8px 0;'>🔐 Acesso ao Portal Comercial</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div style='text-align:center; color:#334033; font-size:16px; "
            "margin-bottom:22px;'>Entre com seu login e senha para acessar o Proposta Inteligente.</div>",
            unsafe_allow_html=True,
        )

        with st.form("form_login"):
            login = st.text_input(
                "Login",
                placeholder="Ex: joao_empresaa",
            )

            senha = st.text_input(
                "Senha",
                type="password",
                placeholder="Digite sua senha",
            )

            entrar = st.form_submit_button(
                "ENTRAR",
                use_container_width=True,
            )

        if entrar:
            if not login or not senha:
                st.error("Informe o login e a senha.")
            else:
                usuario, erro = autenticar_usuario(login, senha)

                if erro:
                    st.error(erro)
                else:
                    empresa, erro_empresa = obter_empresa(usuario["empresa_ref"])

                    if erro_empresa:
                        st.error(erro_empresa)
                    else:
                        st.session_state["autenticado"] = True
                        st.session_state["usuario_id"] = usuario["usuario_id"]
                        st.session_state["usuario_nome"] = usuario["nome"]
                        st.session_state["usuario_login"] = usuario["login"]
                        st.session_state["empresa_id"] = empresa["empresa_id"]
                        st.session_state["empresa_nome"] = empresa["nome_empresa"]
                        st.session_state["perfil_acesso"] = usuario["perfil_acesso"]
                        st.session_state["template_id"] = empresa["template_id"]
                        st.session_state["pasta_destino_id"] = empresa["pasta_destino_id"]
                        st.session_state["cota_empresa"] = empresa["cota"]
                        st.rerun()


if not st.session_state.get("autenticado", False):
    tela_login()
    st.stop()


# Identidade disponível em todas as telas durante a sessão.
NOME_USUARIO_LOGADO = st.session_state["usuario_nome"]
LOGIN_USUARIO_LOGADO = st.session_state["usuario_login"]
EMPRESA_ID_LOGADA = st.session_state["empresa_id"]
NOME_EMPRESA_LOGADA = st.session_state["empresa_nome"]
PERFIL_ACESSO_LOGADO = st.session_state["perfil_acesso"]

# =================================================================================
# 2. SIDEBAR / NAV
# =================================================================================
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=160)
    else:
        st.title("📊 Proposta Inteligente")

    st.markdown(f"#### Olá, **{NOME_USUARIO_LOGADO}**! 👋")
    st.caption(NOME_EMPRESA_LOGADA)
    st.caption(f"{LOGIN_USUARIO_LOGADO} • {PERFIL_ACESSO_LOGADO}")

    if st.button("↪️ Sair"):
        limpar_sessao()
        st.rerun()

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
            whatsapp_cliente = st.text_input(
                f"WhatsApp do Cliente (com DDD) * — {badge_wa}",
                placeholder="Ex: 5548999999999",
            )

        st.subheader("2. Detalhes do Orçamento")
        resumo_servicos = st.text_area(
            "Resumo dos Serviços *",
            placeholder="Ex: Reforma completa de um bar comercial..."
        )

        st.subheader("3. Valores e Itens")
        itens_valores = st.text_area(
            "Itens, Quantidades e Valores da Obra *",
            placeholder="Ex:\n- Demolição de paredes | 1 un | R$ 1.500,00\n- Pintura geral | 120 m² | R$ 3.500,00"
        )

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
                                "instance": INSTANCE_NAME,

                                # Fase 3: identificação automática do usuário.
                                # Esses valores vêm da sessão autenticada.
                                "empresa_id": EMPRESA_ID_LOGADA,
                                "vendedor": NOME_USUARIO_LOGADO,
                                "usuario_id": st.session_state.get("usuario_id", "")
                            }
                            response = requests.post(WEBAPP_URL, json=payload, timeout=30)
                            if response.status_code == 200 and response.json().get("status") == "success":
                                st.success(f"✅ Orçamento para **{nome_cliente}** registrado com sucesso para **{NOME_USUARIO_LOGADO}**!")
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

        # Identificação inteligente das colunas da planilha
        col_carimbo = next((c for c in df_dados.columns if "carimbo" in c.lower() or "data" in c.lower()), df_dados.columns[0])
        col_nome = next((c for c in df_dados.columns if "nome" in c.lower()), df_dados.columns[1])
        col_whats = next((c for c in df_dados.columns if "whatsapp" in c.lower() or "zap" in c.lower()), df_dados.columns[2])
        col_resumo = next((c for c in df_dados.columns if "resumo" in c.lower()), df_dados.columns[3])
        col_itens = next((c for c in df_dados.columns if "itens" in c.lower()), df_dados.columns[4])
        col_status = next((c for c in df_dados.columns if "status" in c.lower()), df_dados.columns[-1])
        col_pdf = next((c for c in df_dados.columns if "http" in c.lower() or "pdf" in c.lower() or "link" in c.lower()), None)

        df_dados["Data_Parsed"] = pd.to_datetime(df_dados[col_carimbo], dayfirst=True, errors="coerce")
        
        status_clean = df_dados[col_status].astype(str).str.strip().str.lower()
        df_concluidos = df_dados[status_clean.isin(["concluído", "concluido"])]

        # Função para calcular o valor total extraído do campo de itens/valores
        def calcular_total(texto):
            if not isinstance(texto, str): 
                return 0.0
            total = 0.0
            linhas = texto.split('\n')
            for linha in linhas:
                parts = re.split(r'[-–:|]', linha)
                if len(parts) > 1:
                    parte_valor = parts[-1].strip()
                    parte_limpa = re.sub(r'[^\d,\.]', '', parte_valor)
                    if parte_limpa:
                        if ',' in parte_limpa and '.' in parte_limpa:
                            parte_limpa = parte_limpa.replace('.', '').replace(',', '.')
                        elif ',' in parte_limpa:
                            parte_limpa = parte_limpa.replace(',', '.')
                        try:
                            total += float(parte_limpa)
                        except:
                            pass
            return total

        df_concluidos = df_concluidos.copy()
        df_concluidos["Valor Total"] = df_concluidos[col_itens].apply(calcular_total)

        total_historico = len(df_concluidos)
        agora = pd.Timestamp.now()
        df_mes_atual = df_concluidos[
            (df_concluidos["Data_Parsed"].dt.month == agora.month) & 
            (df_concluidos["Data_Parsed"].dt.year == agora.year)
        ]
        total_mes = len(df_mes_atual)
        faturamento_mes = df_mes_atual["Valor Total"].sum()
        faturamento_total = df_concluidos["Valor Total"].sum()

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1: 
            st.metric("Total Concluídos", f"{total_historico}")
        with kpi2: 
            st.metric("Concluídos no Mês", f"{total_mes}")
        with kpi3: 
            st.metric("Volume no Mês", f"R$ {faturamento_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        with kpi4: 
            st.metric("Volume Acumulado", f"R$ {faturamento_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        st.markdown("---")
        st.subheader("📋 Histórico de Orçamentos Emitidos")

        df_exibir = pd.DataFrame()
        df_exibir["Data do Envio"] = df_concluidos["Data_Parsed"].dt.strftime("%d/%m/%Y %H:%M")
        df_exibir["Cliente"] = df_concluidos[col_nome]
        df_exibir["WhatsApp"] = df_concluidos[col_whats]
        df_exibir["Resumo do Serviço"] = df_concluidos[col_resumo]
        df_exibir["Valor Total"] = df_concluidos["Valor Total"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        config_colunas = {
            "Data do Envio": st.column_config.TextColumn("Data do Envio"),
            "Cliente": st.column_config.TextColumn("Cliente"),
            "WhatsApp": st.column_config.TextColumn("WhatsApp"),
            "Resumo do Serviço": st.column_config.TextColumn("Resumo do Serviço"),
            "Valor Total": st.column_config.TextColumn("Valor Total")
        }

        if col_pdf:
            df_exibir["Proposta (PDF)"] = df_concluidos[col_pdf]
            config_colunas["Proposta (PDF)"] = st.column_config.LinkColumn(
                "Proposta (PDF)",
                help="Clique para baixar ou abrir o PDF do orçamento",
                display_text="📥 Abrir PDF"
            )
        else:
            df_exibir["Proposta (PDF)"] = "Aguardando Link"
            config_colunas["Proposta (PDF)"] = st.column_config.TextColumn("Proposta (PDF)")

        # Limpeza final de strings para evitar erros na tabela
        for col in df_exibir.columns:
            if col != "Proposta (PDF)":
                df_exibir[col] = df_exibir[col].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()

        st.dataframe(
            df_exibir,
            use_container_width=True,
            hide_index=True,
            column_config=config_colunas
        )
    else:
        st.info("Nenhum dado encontrado na planilha.")

elif menu == "📱 Conectar WhatsApp":
    st.title("📱 Status da Conexão WhatsApp")
    st.write("Gerencie a conexão da Evolution API para disparos automáticos de propostas.")
    st.divider()

    col_btn, col_status = st.columns([1, 2])
    with col_btn:
        st.button("🔄 Verificar Status / Gerar QR Code")

    try:
        url_state = f"{EVOLUTION_API_URL}/instance/connectionState/{INSTANCE_NAME}"
        headers = {"apikey": API_KEY}
        res_state = requests.get(url_state, headers=headers, timeout=5)

        if res_state.status_code == 200:
            state_data = res_state.json()
            status_atual = state_data.get("instance", {}).get("state", "disconnected")

            if status_atual == "open":
                st.success("🟢 **WhatsApp Conectado e Operacional!**")
                st.info("Sua instância está pronta para enviar as propostas automaticamente aos clientes.")
            else:
                st.error("🔴 **WhatsApp Desconectado**")
                st.warning("Abra o WhatsApp no seu celular, vá em 'Aparelhos Conectados' e escaneie o QR Code abaixo:")

                url_qr = f"{EVOLUTION_API_URL}/instance/connect/{INSTANCE_NAME}"
                res_qr = requests.get(url_qr, headers=headers, timeout=5)
                if res_qr.status_code == 200:
                    qr_data = res_qr.json()
                    base64_qr = qr_data.get("base64") or qr_data.get("code")

                    if base64_qr:
                        if "," in base64_qr:
                            base64_qr = base64_qr.split(",")[1]
                        st.image(base64.b64decode(base64_qr), width=280)
                    else:
                        st.info("Aguardando geração do QR Code...")
        else:
            st.error(f"Erro ao consultar a Evolution API. Status Code: {res_state.status_code}")

    except Exception as e:
        st.error(f"Falha de conexão com a Evolution API: {e}")
