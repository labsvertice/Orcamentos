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
                range=f"{nome_aba}!A1:Z10000",
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
                                "empresa_id": EMPRESA_ID_LOGADA,
                                "vendedor": NOME_USUARIO_LOGADO,
                                "usuario_id": st.session_state.get("usuario_id", "")
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
    st.write("Acompanhe quantidade, volume financeiro e desempenho por período e vendedor.")
    st.divider()

    df_dados = carregar_dados_planilha()

    if df_dados is not None and not df_dados.empty:
        df_dados = df_dados.copy()
        df_dados.columns = df_dados.columns.astype(str).str.strip()

        # ------------------------------------------------------------------
        # Identificação das colunas
        # ------------------------------------------------------------------
        col_carimbo = next(
            (c for c in df_dados.columns
             if "carimbo" in c.lower() or "data" in c.lower()),
            df_dados.columns[0]
        )

        col_nome = next(
            (c for c in df_dados.columns if "nome" in c.lower()),
            df_dados.columns[1]
        )

        col_whats = next(
            (c for c in df_dados.columns
             if "whatsapp" in c.lower() or "zap" in c.lower()),
            df_dados.columns[2]
        )

        col_resumo = next(
            (c for c in df_dados.columns if "resumo" in c.lower()),
            df_dados.columns[3]
        )

        col_itens = next(
            (c for c in df_dados.columns if "itens" in c.lower()),
            df_dados.columns[4]
        )

        col_status = next(
            (c for c in df_dados.columns if "status" in c.lower()),
            df_dados.columns[5]
        )

        col_empresa = next(
            (c for c in df_dados.columns if "empresa_id" in c.lower()),
            None
        )

        col_vendedor = next(
            (c for c in df_dados.columns if "vendedor" in c.lower()),
            None
        )

        col_usuario = next(
            (c for c in df_dados.columns if "usuario_id" in c.lower()),
            None
        )

        col_pdf = next(
            (c for c in df_dados.columns
             if "http" in c.lower() or "pdf" in c.lower() or "link" in c.lower()),
            None
        )

        # ------------------------------------------------------------------
        # Data
        # ------------------------------------------------------------------
        df_dados["Data_Parsed"] = pd.to_datetime(
            df_dados[col_carimbo],
            dayfirst=True,
            errors="coerce"
        )

        # ------------------------------------------------------------------
        # Empresa: segurança multiempresa
        # ------------------------------------------------------------------
        if col_empresa:
            empresa_clean = (
                df_dados[col_empresa]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
            )

            empresa_logada = str(EMPRESA_ID_LOGADA).strip().lower()

            df_dados = df_dados[
                empresa_clean == empresa_logada
            ].copy()

        else:
            # Compatibilidade enquanto a planilha ainda não tiver a coluna.
            st.warning(
                "A coluna Empresa_ID ainda não foi encontrada em Form_Responses."
            )

        # ------------------------------------------------------------------
        # Vendedor: administrador vê todos; vendedor vê apenas o próprio
        # ------------------------------------------------------------------
        perfil_normalizado = str(PERFIL_ACESSO_LOGADO).strip().lower()

        if col_vendedor:
            df_dados["Vendedor_Exibicao"] = (
                df_dados[col_vendedor]
                .fillna("")
                .astype(str)
                .str.strip()
            )
        else:
            df_dados["Vendedor_Exibicao"] = ""

        if perfil_normalizado != "administrador":
            vendedor_logado = str(NOME_USUARIO_LOGADO).strip().lower()

            df_dados = df_dados[
                df_dados["Vendedor_Exibicao"]
                .str.lower()
                .eq(vendedor_logado)
            ].copy()

        # ------------------------------------------------------------------
        # Status
        # ------------------------------------------------------------------
        df_dados["Status_Clean"] = (
            df_dados[col_status]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        # Só orçamentos efetivamente concluídos entram nos KPIs financeiros.
        df_base = df_dados[
            df_dados["Status_Clean"].isin(["concluído", "concluido"])
        ].copy()

        if df_base.empty:
            st.info("Nenhum orçamento concluído encontrado para este acesso.")
        else:

            # ------------------------------------------------------------------
            # Valor total oficial
            # ------------------------------------------------------------------
            # O Apps Script grava na coluna K o valor retornado pelo Gemini.
            col_valor = next(
                (
                    c for c in df_base.columns
                    if str(c).strip().lower() in {
                        "valor_total",
                        "valor total",
                        "valor_total_calculado",
                        "valor total calculado",
                    }
                    or "valor_total" in str(c).strip().lower()
                ),
                None
            )

            if col_valor is None:
                st.warning(
                    "A coluna Valor_Total (K) ainda não foi encontrada em Form_Responses. "
                    "Depois de atualizar o Apps Script e criar uma nova proposta, ela será utilizada pelo painel."
                )

                df_base["Valor_Total"] = 0.0

            else:
                def parse_valor_brasileiro(valor):
                    texto = str(valor or "").strip()

                    if not texto:
                        return 0.0

                    texto = re.sub(r"[^0-9,.-]", "", texto)

                    if not texto:
                        return 0.0

                    if "," in texto and "." in texto:
                        if texto.rfind(",") > texto.rfind("."):
                            texto = texto.replace(".", "").replace(",", ".")
                        else:
                            texto = texto.replace(",", "")
                    elif "," in texto:
                        texto = texto.replace(",", ".")

                    try:
                        return float(texto)
                    except (ValueError, TypeError):
                        return 0.0

                df_base["Valor_Total"] = (
                    df_base[col_valor]
                    .apply(parse_valor_brasileiro)
                )

            # ------------------------------------------------------------------
            # Filtros
            # ------------------------------------------------------------------
            st.subheader("🔎 Filtros")

            col_filtro1, col_filtro2, col_filtro3 = st.columns([1, 1, 1])

            with col_filtro1:
                periodo = st.selectbox(
                    "Período",
                    [
                        "Este mês",
                        "Hoje",
                        "Últimos 7 dias",
                        "Últimos 30 dias",
                        "Este ano",
                        "Todo o período",
                    ],
                    index=0,
                )

            with col_filtro2:
                data_min = df_base["Data_Parsed"].min()
                data_max = df_base["Data_Parsed"].max()

                if pd.isna(data_min) or pd.isna(data_max):
                    data_min = pd.Timestamp.now()
                    data_max = pd.Timestamp.now()

                intervalo_datas = st.date_input(
                    "Intervalo",
                    value=(
                        data_min.date(),
                        data_max.date(),
                    ),
                )

            with col_filtro3:
                if (
                    perfil_normalizado == "administrador"
                    and col_vendedor
                    and not df_base.empty
                ):
                    vendedores = sorted(
                        [
                            v for v in
                            df_base["Vendedor_Exibicao"]
                            .dropna()
                            .astype(str)
                            .str.strip()
                            .unique()
                            if v
                        ]
                    )

                    vendedor_filtro = st.selectbox(
                        "Vendedor",
                        ["Todos"] + vendedores,
                        index=0,
                    )
                else:
                    vendedor_filtro = "Todos"

            agora = pd.Timestamp.now()

            if len(intervalo_datas) == 2:
                inicio_custom = pd.Timestamp(intervalo_datas[0])
                fim_custom = (
                    pd.Timestamp(intervalo_datas[1])
                    + pd.Timedelta(days=1)
                    - pd.Timedelta(seconds=1)
                )
            else:
                inicio_custom = pd.Timestamp(intervalo_datas[0])
                fim_custom = (
                    inicio_custom
                    + pd.Timedelta(days=1)
                    - pd.Timedelta(seconds=1)
                )

            if periodo == "Hoje":
                inicio_periodo = agora.normalize()
                fim_periodo = (
                    inicio_periodo
                    + pd.Timedelta(days=1)
                    - pd.Timedelta(seconds=1)
                )

            elif periodo == "Últimos 7 dias":
                inicio_periodo = (
                    agora.normalize()
                    - pd.Timedelta(days=6)
                )
                fim_periodo = agora

            elif periodo == "Últimos 30 dias":
                inicio_periodo = (
                    agora.normalize()
                    - pd.Timedelta(days=29)
                )
                fim_periodo = agora

            elif periodo == "Este ano":
                inicio_periodo = pd.Timestamp(
                    year=agora.year,
                    month=1,
                    day=1
                )
                fim_periodo = agora

            elif periodo == "Todo o período":
                inicio_periodo = df_base["Data_Parsed"].min()
                fim_periodo = df_base["Data_Parsed"].max()

            else:
                # Este mês
                inicio_periodo = pd.Timestamp(
                    year=agora.year,
                    month=agora.month,
                    day=1
                )
                fim_periodo = agora

            # O intervalo manual funciona como refinamento adicional.
            inicio_final = max(
                inicio_periodo,
                inicio_custom
            )

            fim_final = min(
                fim_periodo,
                fim_custom
            )

            df_filtrado = df_base[
                (df_base["Data_Parsed"] >= inicio_final)
                & (df_base["Data_Parsed"] <= fim_final)
            ].copy()

            if (
                perfil_normalizado == "administrador"
                and vendedor_filtro != "Todos"
            ):
                df_filtrado = df_filtrado[
                    df_filtrado["Vendedor_Exibicao"].eq(vendedor_filtro)
                ].copy()

            # ------------------------------------------------------------------
            # KPIs
            # ------------------------------------------------------------------
            qtd_orcamentos = len(df_filtrado)
            valor_total = df_filtrado["Valor_Total"].sum()
            ticket_medio = (
                valor_total / qtd_orcamentos
                if qtd_orcamentos
                else 0.0
            )

            qtd_vendedores = (
                df_filtrado["Vendedor_Exibicao"]
                .replace("", pd.NA)
                .dropna()
                .nunique()
            )

            def moeda_br(valor):
                return (
                    f"R$ {valor:,.2f}"
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)

            with kpi1:
                st.metric(
                    "Orçamentos",
                    f"{qtd_orcamentos}"
                )

            with kpi2:
                st.metric(
                    "Valor Total Orçado",
                    moeda_br(valor_total)
                )

            with kpi3:
                st.metric(
                    "Ticket Médio",
                    moeda_br(ticket_medio)
                )

            with kpi4:
                if perfil_normalizado == "administrador":
                    st.metric(
                        "Vendedores",
                        f"{qtd_vendedores}"
                    )
                else:
                    st.metric(
                        "Status",
                        "Ativo"
                    )

            st.markdown("---")

            # ------------------------------------------------------------------
            # GRÁFICO 1 — evolução mensal
            # ------------------------------------------------------------------
            st.subheader("📈 Evolução dos Orçamentos")

            df_grafico = df_filtrado.dropna(
                subset=["Data_Parsed"]
            ).copy()

            if not df_grafico.empty:
                df_grafico["Mês"] = (
                    df_grafico["Data_Parsed"]
                    .dt.to_period("M")
                    .dt.to_timestamp()
                )

                mensal = (
                    df_grafico
                    .groupby("Mês")
                    .agg(
                        Orçamentos=("Valor_Total", "size"),
                        Valor=("Valor_Total", "sum")
                    )
                    .sort_index()
                )

                st.line_chart(
                    mensal[["Orçamentos"]],
                    use_container_width=True
                )
            else:
                st.info("Sem dados para o gráfico no período selecionado.")

            # ------------------------------------------------------------------
            # GRÁFICO 2 — desempenho por vendedor
            # ------------------------------------------------------------------
            if perfil_normalizado == "administrador":
                st.subheader("👥 Desempenho por Vendedor")

                if not df_filtrado.empty:
                    por_vendedor = (
                        df_filtrado
                        .groupby("Vendedor_Exibicao")
                        .agg(
                            Orçamentos=("Valor_Total", "size"),
                            Valor_Total=("Valor_Total", "sum")
                        )
                        .sort_values(
                            "Valor_Total",
                            ascending=False
                        )
                    )

                    col_chart1, col_chart2 = st.columns(2)

                    with col_chart1:
                        st.caption("Quantidade de orçamentos")
                        st.bar_chart(
                            por_vendedor["Orçamentos"],
                            use_container_width=True
                        )

                    with col_chart2:
                        st.caption("Valor total orçado")
                        st.bar_chart(
                            por_vendedor["Valor_Total"],
                            use_container_width=True
                        )
                else:
                    st.info("Sem dados por vendedor no período selecionado.")

            # ------------------------------------------------------------------
            # HISTÓRICO
            # ------------------------------------------------------------------
            st.markdown("---")
            st.subheader("📋 Histórico de Orçamentos")

            df_exibir = pd.DataFrame()

            df_exibir["Data do Envio"] = (
                df_filtrado["Data_Parsed"]
                .dt.strftime("%d/%m/%Y %H:%M")
            )

            df_exibir["Cliente"] = df_filtrado[col_nome]
            df_exibir["Vendedor"] = df_filtrado["Vendedor_Exibicao"]
            df_exibir["WhatsApp"] = df_filtrado[col_whats]
            df_exibir["Resumo do Serviço"] = df_filtrado[col_resumo]

            df_exibir["Valor Total"] = (
                df_filtrado["Valor_Total"]
                .apply(moeda_br)
            )

            df_exibir["Status"] = df_filtrado[col_status]

            config_colunas = {
                "Data do Envio": st.column_config.TextColumn(
                    "Data do Envio"
                ),
                "Cliente": st.column_config.TextColumn(
                    "Cliente"
                ),
                "Vendedor": st.column_config.TextColumn(
                    "Vendedor"
                ),
                "WhatsApp": st.column_config.TextColumn(
                    "WhatsApp"
                ),
                "Resumo do Serviço": st.column_config.TextColumn(
                    "Resumo do Serviço"
                ),
                "Valor Total": st.column_config.TextColumn(
                    "Valor Total"
                ),
                "Status": st.column_config.TextColumn(
                    "Status"
                ),
            }

            if col_pdf:
                df_exibir["Proposta (PDF)"] = df_filtrado[col_pdf]

                config_colunas["Proposta (PDF)"] = (
                    st.column_config.LinkColumn(
                        "Proposta (PDF)",
                        help="Clique para abrir o PDF da proposta.",
                        display_text="📥 Abrir PDF"
                    )
                )

            else:
                df_exibir["Proposta (PDF)"] = "Aguardando Link"

                config_colunas["Proposta (PDF)"] = (
                    st.column_config.TextColumn(
                        "Proposta (PDF)"
                    )
                )

            for col in df_exibir.columns:
                if col != "Proposta (PDF)":
                    df_exibir[col] = (
                        df_exibir[col]
                        .fillna("")
                        .astype(str)
                        .str.replace(
                            r"\.0$",
                            "",
                            regex=True
                        )
                        .str.strip()
                    )

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
