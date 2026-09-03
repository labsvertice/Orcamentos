import base64
import os
import re

import pandas as pd
import requests
import streamlit as st

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from streamlit_gsheets import GSheetsConnection


# =================================================================================
# CONFIGURAÇÕES GERAIS
# =================================================================================

# URL DO SEU APP WEB DO GOOGLE APPS SCRIPT (ORÇAMENTOS)
WEBAPP_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbwxyKpNaItwSD3CvC-gKgVWnIirhuF5_eTUvN9fultN5ZvktRob9071ZHHzE333leGK"
    "/exec"
)


# =================================================================================
# CONFIGURAÇÕES DA EVOLUTION API
# =================================================================================
#
# A URL e a API Key ficam nos Secrets do Streamlit.
#
# IMPORTANTE:
# A instância NÃO fica fixa no código.
#
# A instância efetiva é resolvida assim:
#
# 1. Evolution_Instance do usuário
# 2. se vazio → Evolution_Instance da empresa
# 3. se ambos vazios → WhatsApp não configurado
#
# =================================================================================

try:
    EVOLUTION_API_URL = st.secrets["evolution"]["api_url"]
    API_KEY = st.secrets["evolution"]["api_key"]
except Exception:
    EVOLUTION_API_URL = ""
    API_KEY = ""


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
    :root {
        --brand-bg: #F4F4F4;
        --brand-bg-2: #EAEAEA;
        --brand-panel: #FAFAFA;
        --brand-line: #D1D1D1;
        --brand-text: #16271F;
        --brand-muted: #5E6D64;
        --brand-green: #2F5D4F;
        --brand-green-dark: #23483D;
        --brand-gold: #B9954A;
        --brand-gold-light: #E7D7AF;
    }

    .stApp {
        background-color: var(--brand-bg) !important;
    }

    header[data-testid="stHeader"],
    [data-testid="stHeader"],
    header {
        display: none !important;
        height: 0px !important;
    }

    .main .block-container,
    [data-testid="stMainBlockContainer"] {
        padding-top: 2.2rem !important;
        padding-bottom: 2.5rem !important;
    }

    [data-testid="stSidebar"] {
        background: #E5E5E5 !important;
        border-right: 1px solid var(--brand-line) !important;
    }

    [data-testid="stSidebarContent"] {
        padding-top: 1.6rem !important;
    }

    h1, h2, h3, h4 {
        color: var(--brand-text) !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }

    p, label, .stCaption, [data-testid="stMarkdownContainer"] {
        color: var(--brand-text);
    }

    div.stButton > button,
    div.stFormSubmitButton > button {
        background: #D3A51D !important;
        color: #17231B !important;
        font-weight: 700 !important;
        border-radius: 9px !important;
        border: 1px solid #D3A51D !important;
        padding: 10px 24px !important;
        width: 100%;
        transition: all 0.2s ease !important;
    }

    div.stButton > button:hover,
    div.stFormSubmitButton > button:hover {
        background: #B58C0B !important;
        border-color: #B78D0D !important;
        box-shadow: 0 4px 12px rgba(35, 72, 61, 0.16) !important;
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div,
    div[data-baseweb="select"] > div {
        background: #C9C9C9 !important;
        border-color: #CDD6CF !important;
    }

    div[data-testid="stMetricValue"] {
        color: var(--brand-text) !important;
    }

    div[data-testid="stMetricLabel"] {
        color: var(--brand-muted) !important;
    }

    hr {
        border-color: var(--brand-line) !important;
    }

    .login-shell {
        max-width: 1180px;
        margin: 0 auto;
        padding-top: 2.5rem;
    }

    .login-card {
        background: rgba(247, 248, 245, 0.88);
        border: 1px solid var(--brand-line);
        border-radius: 14px;
        padding: 28px;
        box-shadow: 0 10px 30px rgba(22, 39, 31, 0.06);
    }

    div[data-testid="stForm"] {
        background: rgba(250, 250, 248, 0.94) !important;
        border: 1px solid #D0D3D0 !important;
        border-radius: 14px !important;
        padding: 26px 24px !important;
        box-shadow: 0 10px 28px rgba(22, 39, 31, 0.06) !important;
    }

    /* ============================================================
       PALETA NEUTRA DO PORTAL
       ============================================================ */

    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stApp"],
    .main {
        background: #F4F4F4 !important;
    }

    [data-testid="stForm"] {
        background: #FAFAFA !important;
        border: 1px solid #D1D1D1 !important;
    }

    /* Campos de preenchimento: cinza médio, sem tom verde. */
    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div,
    div[data-baseweb="select"] > div,
    [data-baseweb="base-input"] > div {
        background: #C9C9C9 !important;
        border: 1px solid #C6C6C6 !important;
        box-shadow: none !important;
    }

    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"] textarea,
    div[data-baseweb="select"] input {
        background: transparent !important;
        color: #202020 !important;
    }

    div[data-baseweb="input"] input::placeholder,
    div[data-baseweb="textarea"] textarea::placeholder {
        color: #667078 !important;
        opacity: 1 !important;
    }

    [data-baseweb] {
        --accent-color: #D3A51D;
    }

    [data-testid="stSidebar"] {
        background: #EAEAEA !important;
    }

    .brand-image-wrap {
        width: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 0 auto;
    }

    .login-title {
        text-align: center;
        color: var(--brand-text);
        font-size: 32px;
        font-weight: 750;
        margin: 20px 0 8px 0;
    }

    .login-subtitle {
        text-align: center;
        color: var(--brand-muted);
        font-size: 16px;
        margin-bottom: 24px;
    }

    .section-note {
        color: var(--brand-muted);
        font-size: 15px;
        margin-top: -8px;
        margin-bottom: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# GOOGLE SHEETS — CONEXÃO DIRETA VIA SERVICE ACCOUNT
# =============================================================================

SPREADSHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1B0w56eDkP9kT6a4o0eDS3Ll1qA5r1VYexBxbEZT38bU/edit"
)

SPREADSHEET_ID = (
    "1B0w56eDkP9kT6a4o0eDS3Ll1qA5r1VYexBxbEZT38bU"
)

USUARIOS_GID = 1751518313
EMPRESAS_GID = 751640019

conn = st.connection(
    "gsheets",
    type=GSheetsConnection
)


def obter_google_sheets_service():
    """Cria o cliente autenticado do Google Sheets a partir dos Secrets."""
    try:
        config = st.secrets["connections"]["gsheets"]

        required = [
            "type",
            "project_id",
            "private_key",
            "client_email",
            "token_uri",
        ]

        faltantes = [
            chave
            for chave in required
            if chave not in config
        ]

        if faltantes:
            raise RuntimeError(
                "Secrets incompleto em [connections.gsheets]. "
                f"Faltando: {', '.join(faltantes)}"
            )

        service_account_info = {
            "type": config["type"],
            "project_id": config["project_id"],
            "private_key_id": config.get(
                "private_key_id",
                ""
            ),
            "private_key": config["private_key"],
            "client_email": config["client_email"],
            "client_id": config.get(
                "client_id",
                ""
            ),
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
                "https://www.googleapis.com/oauth2/v1/certs",
            ),
        }

        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly"
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
            "Falha ao autenticar a Service Account "
            f"do Google Sheets: {e}"
        ) from e


def normalizar_colunas(df):
    if df is not None and not df.empty:
        df = df.copy()
        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
        )

    return df


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
                range=f"{nome_aba}!A:Z",
            )
            .execute()
        )

        values = result.get(
            "values",
            []
        )

        if not values:
            return pd.DataFrame()

        cabecalho = values[0]

        largura = max(
            len(cabecalho),
            max(
                (
                    len(linha)
                    for linha in values[1:]
                ),
                default=0
            ),
        )

        cabecalho = (
            list(cabecalho)
            + [
                f"Coluna_{i}"
                for i in range(
                    len(cabecalho),
                    largura
                )
            ]
        )

        dados = []

        for linha in values[1:]:

            linha = (
                list(linha)
                + [""] * (
                    largura - len(linha)
                )
            )

            dados.append(
                linha[:largura]
            )

        df = pd.DataFrame(
            dados,
            columns=cabecalho
        )

        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
        )

        return df

    except Exception as e:
        raise RuntimeError(
            f"Não foi possível ler a aba "
            f"'{nome_aba}' da planilha do "
            f"Proposta Inteligente: {e}"
        ) from e


def carregar_dados_planilha():
    """Lê Form_Responses usando a conexão GSheets."""
    try:
        df = conn.read(
            ttl=0
        )

        return normalizar_colunas(
            df
        )

    except Exception as e:

        st.error(
            f"Erro ao carregar Form_Responses: {e}"
        )

        return None


def carregar_usuarios():

    try:
        return ler_aba_sheets(
            "Usuarios"
        )

    except Exception as e:

        st.error(
            f"Erro ao carregar a aba Usuarios "
            f"(GID {USUARIOS_GID}): {e}"
        )

        return None


def carregar_empresas():

    try:
        return ler_aba_sheets(
            "Empresas"
        )

    except Exception as e:

        st.error(
            f"Erro ao carregar a aba Empresas "
            f"(GID {EMPRESAS_GID}): {e}"
        )

        return None


def localizar_coluna(
    df,
    candidatos
):

    if df is None or df.empty:
        return None

    mapa = {
        str(c).strip().lower(): c
        for c in df.columns
    }

    for candidato in candidatos:

        chave = (
            str(candidato)
            .strip()
            .lower()
        )

        if chave in mapa:

            return mapa[chave]

    return None


def valor_ativo(valor):

    return (
        str(valor)
        .strip()
        .lower()
        in {
            "sim",
            "true",
            "1",
            "ativo",
            "yes",
        }
    )


# =================================================================================
# EVOLUTION API
# =================================================================================

def evolution_configurada():

    return bool(
        EVOLUTION_API_URL
        and API_KEY
    )


def evolution_headers():

    return {
        "apikey": API_KEY,
        "Content-Type": "application/json",
    }


def obter_estado_instancia(
    instance_name
):
    """
    Consulta o estado de uma instância.

    Retorno:
        {
            "ok": True/False,
            "exists": True/False,
            "state": "open"/"close"/...,
            "status_code": 200/404/...,
            "data": {...}
        }
    """

    if not instance_name:

        return {
            "ok": False,
            "exists": False,
            "state": "disconnected",
            "status_code": None,
            "data": {},
        }

    if not evolution_configurada():

        return {
            "ok": False,
            "exists": False,
            "state": "disconnected",
            "status_code": None,
            "data": {},
        }

    try:

        url = (
            f"{EVOLUTION_API_URL}"
            f"/instance/connectionState/"
            f"{instance_name}"
        )

        response = requests.get(
            url,
            headers=evolution_headers(),
            timeout=5,
        )

        if response.status_code == 200:

            data = response.json()

            state = (
                data
                .get("instance", {})
                .get(
                    "state",
                    "disconnected"
                )
            )

            return {
                "ok": True,
                "exists": True,
                "state": state,
                "status_code": 200,
                "data": data,
            }

        if response.status_code == 404:

            return {
                "ok": False,
                "exists": False,
                "state": "disconnected",
                "status_code": 404,
                "data": {},
            }

        return {
            "ok": False,
            "exists": True,
            "state": "disconnected",
            "status_code": response.status_code,
            "data": {},
        }

    except Exception as e:

        return {
            "ok": False,
            "exists": None,
            "state": "disconnected",
            "status_code": None,
            "data": {
                "error": str(e)
            },
        }


def criar_instancia_evolution(
    instance_name
):
    """
    Cria automaticamente uma instância
    na Evolution API.

    A Evolution API permite criação via:
    POST /instance/create

    com qrcode=true.
    """

    if not instance_name:

        return {
            "ok": False,
            "status_code": None,
            "data": {},
            "mensagem": (
                "Nome da instância não informado."
            ),
        }

    if not evolution_configurada():

        return {
            "ok": False,
            "status_code": None,
            "data": {},
            "mensagem": (
                "A Evolution API não está "
                "configurada nos Secrets."
            ),
        }

    try:

        url = (
            f"{EVOLUTION_API_URL}"
            "/instance/create"
        )

        payload = {
            "instanceName": instance_name,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        }

        response = requests.post(
            url,
            headers=evolution_headers(),
            json=payload,
            timeout=15,
        )

        try:
            data = response.json()
        except Exception:
            data = {}

        if response.status_code in {
            200,
            201,
        }:

            return {
                "ok": True,
                "status_code": response.status_code,
                "data": data,
                "mensagem": (
                    "Instância criada "
                    "com sucesso."
                ),
            }

        # Caso a instância já exista,
        # tratamos como possível condição
        # de corrida e deixamos a rotina
        # de conexão seguir.
        texto_resposta = str(
            data or response.text
        ).lower()

        if response.status_code in {
            400,
            409,
        } and (
            "already"
            in texto_resposta
            or "exist"
            in texto_resposta
            or "instanc"
            in texto_resposta
        ):

            return {
                "ok": True,
                "status_code": response.status_code,
                "data": data,
                "mensagem": (
                    "A instância já existe."
                ),
            }

        return {
            "ok": False,
            "status_code": response.status_code,
            "data": data,
            "mensagem": (
                "A Evolution API retornou "
                f"status {response.status_code}."
            ),
        }

    except Exception as e:

        return {
            "ok": False,
            "status_code": None,
            "data": {},
            "mensagem": (
                "Falha ao criar a instância: "
                f"{e}"
            ),
        }


def obter_qr_code_evolution(
    instance_name
):
    """
    Solicita o QR Code da instância.

    Usa:
    GET /instance/connect/{instanceName}
    """

    if not instance_name:

        return {
            "ok": False,
            "base64": None,
            "pairing_code": None,
            "code": None,
            "status_code": None,
            "data": {},
            "mensagem": (
                "Nome da instância não informado."
            ),
        }

    if not evolution_configurada():

        return {
            "ok": False,
            "base64": None,
            "pairing_code": None,
            "code": None,
            "status_code": None,
            "data": {},
            "mensagem": (
                "A Evolution API não está "
                "configurada nos Secrets."
            ),
        }

    try:

        url = (
            f"{EVOLUTION_API_URL}"
            f"/instance/connect/"
            f"{instance_name}"
        )

        response = requests.get(
            url,
            headers=evolution_headers(),
            timeout=10,
        )

        try:
            data = response.json()
        except Exception:
            data = {}

        if response.status_code == 200:

            base64_qr = (
                data.get("base64")
                or data.get("qrcode")
                or data.get("qrCode")
            )

            pairing_code = data.get(
                "pairingCode"
            )

            code = data.get(
                "code"
            )

            return {
                "ok": bool(
                    base64_qr
                    or pairing_code
                    or code
                ),
                "base64": base64_qr,
                "pairing_code": pairing_code,
                "code": code,
                "status_code": 200,
                "data": data,
                "mensagem": (
                    "QR Code obtido."
                    if (
                        base64_qr
                        or pairing_code
                        or code
                    )
                    else
                    "A Evolution API não "
                    "retornou o QR Code ainda."
                ),
            }

        return {
            "ok": False,
            "base64": None,
            "pairing_code": None,
            "code": None,
            "status_code": response.status_code,
            "data": data,
            "mensagem": (
                "A Evolution API retornou "
                f"status {response.status_code}."
            ),
        }

    except Exception as e:

        return {
            "ok": False,
            "base64": None,
            "pairing_code": None,
            "code": None,
            "status_code": None,
            "data": {},
            "mensagem": (
                "Falha ao obter o QR Code: "
                f"{e}"
            ),
        }


def preparar_instancia_para_conexao(
    instance_name
):
    """
    Prepara a instância para conexão.

    Fluxo:
        1. verifica existência
        2. se não existir, cria
        3. depois solicita o QR Code

    """

    estado = obter_estado_instancia(
        instance_name
    )

    if estado["exists"] is True:

        return {
            "ok": True,
            "criada_agora": False,
            "estado": estado,
            "criacao": None,
        }

    if estado["status_code"] not in {
        404,
        None,
    }:

        return {
            "ok": False,
            "criada_agora": False,
            "estado": estado,
            "criacao": None,
            "mensagem": (
                "Não foi possível verificar "
                "a instância na Evolution API. "
                f"Status Code: "
                f"{estado['status_code']}"
            ),
        }

    criacao = criar_instancia_evolution(
        instance_name
    )

    if not criacao["ok"]:

        return {
            "ok": False,
            "criada_agora": False,
            "estado": estado,
            "criacao": criacao,
            "mensagem": criacao["mensagem"],
        }

    # A resposta de criação pode já trazer
    # o QR Code. Vamos aproveitar primeiro.
    return {
        "ok": True,
        "criada_agora": True,
        "estado": estado,
        "criacao": criacao,
    }


def obter_qr_bytes(
    base64_qr
):
    """
    Converte base64/data URI em bytes de imagem.
    """

    if not base64_qr:
        return None

    try:

        valor = str(
            base64_qr
        ).strip()

        if "," in valor:

            valor = (
                valor
                .split(",", 1)[1]
            )

        return base64.b64decode(
            valor
        )

    except Exception:

        return None


def extrair_qr_da_resposta(
    data
):
    """
    Procura QR Code nos formatos mais comuns
    retornados pela Evolution.
    """

    if not isinstance(data, dict):

        return None, None, None

    base64_qr = (
        data.get("base64")
        or data.get("qrcode")
        or data.get("qrCode")
    )

    pairing_code = (
        data.get("pairingCode")
    )

    code = (
        data.get("code")
    )

    # Algumas respostas encapsulam em qrcode.
    qrcode_obj = data.get(
        "qrcode"
    )

    if isinstance(
        qrcode_obj,
        dict
    ):

        base64_qr = (
            base64_qr
            or qrcode_obj.get("base64")
        )

        pairing_code = (
            pairing_code
            or qrcode_obj.get(
                "pairingCode"
            )
        )

        code = (
            code
            or qrcode_obj.get("code")
        )

    # Algumas respostas de criação
    # trazem qrcode dentro de instance.
    instance_obj = data.get(
        "instance"
    )

    if isinstance(
        instance_obj,
        dict
    ):

        instance_qrcode = (
            instance_obj.get(
                "qrcode"
            )
        )

        if isinstance(
            instance_qrcode,
            dict
        ):

            base64_qr = (
                base64_qr
                or
                instance_qrcode.get(
                    "base64"
                )
            )

            pairing_code = (
                pairing_code
                or
                instance_qrcode.get(
                    "pairingCode"
                )
            )

            code = (
                code
                or
                instance_qrcode.get(
                    "code"
                )
            )

    return (
        base64_qr,
        pairing_code,
        code
    )


# =================================================================================
# AUTENTICAÇÃO DO USUÁRIO
# =================================================================================

def autenticar_usuario(
    login,
    senha
):

    df = carregar_usuarios()

    if df is None or df.empty:

        return None, (
            "Não foi possível carregar "
            "a aba Usuarios."
        )

    c_login = localizar_coluna(
        df,
        ["Login"]
    )

    c_senha = localizar_coluna(
        df,
        ["Senha"]
    )

    c_nome = localizar_coluna(
        df,
        ["Nome"]
    )

    c_empresa = localizar_coluna(
        df,
        ["Empresa_ID", "Empresa"]
    )

    c_perfil = localizar_coluna(
        df,
        ["Perfil_Acesso", "Perfil"]
    )

    c_ativo = localizar_coluna(
        df,
        ["Ativo"]
    )

    c_usuario = localizar_coluna(
        df,
        [
            "Usuario_ID",
            "Usuario ID"
        ]
    )

    # NOVO:
    # WhatsApp individual do usuário.
    c_instancia_usuario = localizar_coluna(
        df,
        [
            "Evolution_Instance",
            "Evolution Instance",
            "Instancia_Evolution",
            "Instância_Evolution",
        ]
    )

    obrigatorias = {
        "Login": c_login,
        "Senha": c_senha,
        "Nome": c_nome,
        "Empresa_ID": c_empresa,
        "Perfil_Acesso": c_perfil,
        "Ativo": c_ativo,
    }

    faltantes = [
        nome
        for nome, coluna
        in obrigatorias.items()
        if not coluna
    ]

    if faltantes:

        return None, (
            "A aba Usuarios está incompleta. "
            f"Colunas ausentes: "
            f"{', '.join(faltantes)}."
        )

    login_normalizado = (
        str(login or "")
        .strip()
        .lower()
    )

    df["__login"] = (
        df[c_login]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    encontrados = df[
        df["__login"]
        == login_normalizado
    ].copy()

    if encontrados.empty:

        return None, (
            "Login ou senha inválidos."
        )

    if len(encontrados) > 1:

        return None, (
            "Este login está duplicado "
            "na aba Usuarios. "
            "Procure o suporte."
        )

    registro = encontrados.iloc[0]

    if not valor_ativo(
        registro[c_ativo]
    ):

        return None, (
            "Este usuário está inativo "
            "no Proposta Inteligente."
        )

    if (
        str(senha or "")
        !=
        str(registro[c_senha] or "")
    ):

        return None, (
            "Login ou senha inválidos."
        )

    # Instância específica do usuário.
    instancia_usuario = ""

    if c_instancia_usuario:

        valor_instancia = (
            registro[
                c_instancia_usuario
            ]
        )

        if pd.notna(
            valor_instancia
        ):

            instancia_usuario = (
                str(valor_instancia)
                .strip()
            )

    return {

        "usuario_id": (
            str(
                registro[c_usuario]
            ).strip()
            if c_usuario
            else ""
        ),

        "nome": (
            str(
                registro[c_nome]
            ).strip()
        ),

        "login": (
            login_normalizado
        ),

        "empresa_ref": (
            str(
                registro[c_empresa]
            ).strip()
        ),

        "perfil_acesso": (
            str(
                registro[c_perfil]
            ).strip()
        ),

        "evolution_instance": (
            instancia_usuario
        ),

    }, None


# =================================================================================
# EMPRESA
# =================================================================================

def obter_empresa(
    empresa_ref
):

    df = carregar_empresas()

    if df is None or df.empty:

        return None, (
            "Não foi possível carregar "
            "a aba Empresas."
        )

    c_id = localizar_coluna(
        df,
        [
            "Empresa_ID",
            "Empresa ID"
        ]
    )

    c_nome = localizar_coluna(
        df,
        [
            "Nome_Empresa",
            "Nome Empresa",
            "Empresa"
        ]
    )

    c_template = localizar_coluna(
        df,
        [
            "Template_ID",
            "Template ID"
        ]
    )

    c_pasta = localizar_coluna(
        df,
        [
            "Pasta_Destino_ID",
            "Pasta Destino ID"
        ]
    )

    c_ativo = localizar_coluna(
        df,
        ["Ativo"]
    )

    c_cota = localizar_coluna(
        df,
        ["Cota"]
    )

    # NOVO:
    # WhatsApp padrão da empresa.
    c_instancia_empresa = localizar_coluna(
        df,
        [
            "Evolution_Instance",
            "Evolution Instance",
            "Instancia_Evolution",
            "Instância_Evolution",
        ]
    )

    if not c_id or not c_nome or not c_ativo:

        return None, (
            "A aba Empresas está incompleta. "
            "São esperadas: "
            "Empresa_ID, Nome_Empresa e Ativo."
        )

    referencia = (
        str(empresa_ref or "")
        .strip()
        .lower()
    )

    ids = (
        df[c_id]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    nomes = (
        df[c_nome]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    encontrados = df[
        (ids == referencia)
        |
        (nomes == referencia)
    ].copy()

    if encontrados.empty:

        return None, (
            f"A empresa '{empresa_ref}' "
            "não foi encontrada na aba Empresas."
        )

    if len(encontrados) > 1:

        return None, (
            f"Existem múltiplas empresas "
            f"correspondentes a "
            f"'{empresa_ref}'."
        )

    registro = encontrados.iloc[0]

    if not valor_ativo(
        registro[c_ativo]
    ):

        return None, (
            "A empresa vinculada ao "
            "usuário está inativa."
        )

    # Instância padrão da empresa.
    instancia_empresa = ""

    if c_instancia_empresa:

        valor_instancia = (
            registro[
                c_instancia_empresa
            ]
        )

        if pd.notna(
            valor_instancia
        ):

            instancia_empresa = (
                str(
                    valor_instancia
                ).strip()
            )

    return {

        "empresa_id": (
            str(
                registro[c_id]
            ).strip()
        ),

        "nome_empresa": (
            str(
                registro[c_nome]
            ).strip()
        ),

        "template_id": (
            str(
                registro[c_template]
            ).strip()
            if c_template
            else ""
        ),

        "pasta_destino_id": (
            str(
                registro[c_pasta]
            ).strip()
            if c_pasta
            else ""
        ),

        "cota": (
            registro[c_cota]
            if c_cota
            else ""
        ),

        "evolution_instance": (
            instancia_empresa
        ),

    }, None


# =================================================================================
# LIMPAR SESSÃO
# =================================================================================

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

        "evolution_instance_usuario",
        "evolution_instance_empresa",
        "evolution_instance",

    ]:

        st.session_state.pop(
            chave,
            None
        )


# =================================================================================
# TELA DE LOGIN
# =================================================================================

def tela_login():

    st.markdown(
        '<div class="login-shell">',
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # CABEÇALHO
    # --------------------------------------------------------

    _, header_col, _ = st.columns(
        [1, 2, 1]
    )

    with header_col:

        if os.path.exists(
            "cabecalho.png"
        ):

            st.image(
                "cabecalho.png",
                width=1120
            )

    st.markdown(
        '<div class="login-title">'
        '🔐 Acesso ao Portal de Propostas'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="login-subtitle">'
        'Entre com seu login e senha para '
        'acessar o Proposta Inteligente.'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # FORMULÁRIO
    # --------------------------------------------------------

    _, centro, _ = st.columns(
        [1, 1.35, 1]
    )

    with centro:

        with st.form(
            "form_login"
        ):

            login = st.text_input(
                "Login",
                placeholder="Ex: joao_empresa",
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

    # --------------------------------------------------------
    # RODAPÉ
    # --------------------------------------------------------

    if os.path.exists(
        "rodape.png"
    ):

        st.markdown(
            "<div style='height:22px;'></div>",
            unsafe_allow_html=True
        )

        _, footer_col, _ = st.columns(
            [1, 2, 1]
        )

        with footer_col:

            st.image(
                "rodape.png",
                width=1040
            )

    if entrar:

        if not login or not senha:

            st.error(
                "Informe o login e a senha."
            )

        else:

            usuario, erro = (
                autenticar_usuario(
                    login,
                    senha
                )
            )

            if erro:

                st.error(erro)

            else:

                empresa, erro_empresa = (
                    obter_empresa(
                        usuario[
                            "empresa_ref"
                        ]
                    )
                )

                if erro_empresa:

                    st.error(
                        erro_empresa
                    )

                else:

                    # ------------------------------------------------
                    # IDENTIDADE
                    # ------------------------------------------------

                    st.session_state[
                        "autenticado"
                    ] = True

                    st.session_state[
                        "usuario_id"
                    ] = (
                        usuario[
                            "usuario_id"
                        ]
                    )

                    st.session_state[
                        "usuario_nome"
                    ] = (
                        usuario[
                            "nome"
                        ]
                    )

                    st.session_state[
                        "usuario_login"
                    ] = (
                        usuario[
                            "login"
                        ]
                    )

                    st.session_state[
                        "empresa_id"
                    ] = (
                        empresa[
                            "empresa_id"
                        ]
                    )

                    st.session_state[
                        "empresa_nome"
                    ] = (
                        empresa[
                            "nome_empresa"
                        ]
                    )

                    st.session_state[
                        "perfil_acesso"
                    ] = (
                        usuario[
                            "perfil_acesso"
                        ]
                    )

                    st.session_state[
                        "template_id"
                    ] = (
                        empresa[
                            "template_id"
                        ]
                    )

                    st.session_state[
                        "pasta_destino_id"
                    ] = (
                        empresa[
                            "pasta_destino_id"
                        ]
                    )

                    st.session_state[
                        "cota_empresa"
                    ] = (
                        empresa[
                            "cota"
                        ]
                    )

                    # =================================================
                    # WHATSAPP
                    # =================================================

                    st.session_state[
                        "evolution_instance_usuario"
                    ] = (
                        usuario[
                            "evolution_instance"
                        ]
                    )

                    st.session_state[
                        "evolution_instance_empresa"
                    ] = (
                        empresa[
                            "evolution_instance"
                        ]
                    )

                    # Prioridade:
                    # usuário → empresa
                    st.session_state[
                        "evolution_instance"
                    ] = (
                        usuario[
                            "evolution_instance"
                        ]
                        or
                        empresa[
                            "evolution_instance"
                        ]
                    )

                    st.rerun()


# =================================================================================
# PROTEÇÃO DE ACESSO
# =================================================================================

if not st.session_state.get(
    "autenticado",
    False
):

    tela_login()
    st.stop()


# =================================================================================
# IDENTIDADE DA SESSÃO
# =================================================================================

NOME_USUARIO_LOGADO = (
    st.session_state[
        "usuario_nome"
    ]
)

LOGIN_USUARIO_LOGADO = (
    st.session_state[
        "usuario_login"
    ]
)

EMPRESA_ID_LOGADA = (
    st.session_state[
        "empresa_id"
    ]
)

NOME_EMPRESA_LOGADA = (
    st.session_state[
        "empresa_nome"
    ]
)

PERFIL_ACESSO_LOGADO = (
    st.session_state[
        "perfil_acesso"
    ]
)


# =================================================================================
# INSTÂNCIA EFETIVA
# =================================================================================
#
# Regra:
#
# 1. Usuário possui Evolution_Instance?
#       SIM → usa do usuário
#
# 2. Usuário vazio?
#       usa Evolution_Instance da empresa
#
# 3. Ambos vazios?
#       nenhum WhatsApp configurado
#
# =================================================================================

INSTANCE_NAME_LOGADA = (
    st.session_state
    .get(
        "evolution_instance_usuario",
        ""
    )
    .strip()
    or
    st.session_state
    .get(
        "evolution_instance_empresa",
        ""
    )
    .strip()
    or
    st.session_state
    .get(
        "evolution_instance",
        ""
    )
    .strip()
)


# =================================================================================
# 2. SIDEBAR / NAV
# =================================================================================

with st.sidebar:

    if os.path.exists(
        "proposta_inteligente.png"
    ):

        st.image(
            "proposta_inteligente.png",
            width=130
        )

    else:

        st.title(
            "📊 Proposta Inteligente"
        )

    st.markdown(
        f"#### Olá, "
        f"**{NOME_USUARIO_LOGADO}**! 👋"
    )

    st.caption(
        NOME_EMPRESA_LOGADA
    )

    st.caption(
        f"{LOGIN_USUARIO_LOGADO} • "
        f"{PERFIL_ACESSO_LOGADO}"
    )

    if INSTANCE_NAME_LOGADA:

        st.caption(
            "WhatsApp: "
            f"{INSTANCE_NAME_LOGADA}"
        )

    else:

        st.caption(
            "WhatsApp: não configurado"
        )

    if st.button(
        "↪️ Sair"
    ):

        limpar_sessao()
        st.rerun()

    st.divider()

    menu = st.radio(
        "Navegação Comercial:",
        [
            "➕ Novo Orçamento",
            "📋 Painel de Orçamentos",
            "📱 Conectar WhatsApp"
        ],
        index=0,
    )


# =================================================================================
# 3. NOVO ORÇAMENTO
# =================================================================================

if menu == "➕ Novo Orçamento":

    st.title(
        "📊 Novo Orçamento"
    )

    st.write(
        "Preencha as informações abaixo "
        "para estruturar e disparar a "
        "proposta comercial."
    )

    # NÃO cria instância aqui.
    # Apenas verifica o status.
    estado_wa = obter_estado_instancia(
        INSTANCE_NAME_LOGADA
    )

    if (
        INSTANCE_NAME_LOGADA
        and estado_wa["state"] == "open"
    ):

        badge_wa = "🟢 Conectado"

    elif INSTANCE_NAME_LOGADA:

        badge_wa = "🔴 Desconectado"

    else:

        badge_wa = "⚪ Não configurado"

    with st.form(
        "form_orcamento",
        clear_on_submit=True
    ):

        st.subheader(
            "1. Dados do Cliente"
        )

        col_nome, col_whatsapp = (
            st.columns(2)
        )

        with col_nome:

            nome_cliente = st.text_input(
                "Nome do Cliente / Contratante *"
            )

        with col_whatsapp:

            whatsapp_cliente = (
                st.text_input(
                    f"WhatsApp do Cliente "
                    f"(com DDD) * — {badge_wa}",
                    placeholder=(
                        "Ex: 5548999999999"
                    ),
                )
            )

        st.subheader(
            "2. Detalhes do Orçamento"
        )

        resumo_servicos = st.text_area(
            "Resumo dos Serviços *",
            placeholder=(
                "Ex: Reforma completa "
                "de um bar comercial..."
            )
        )

        st.subheader(
            "3. Valores e Itens"
        )

        itens_valores = st.text_area(
            "Itens, Quantidades e Valores "
            "da Obra *",
            placeholder=(
                "Ex:\n"
                "- Demolição de paredes | "
                "1 un | R$ 1.500,00\n"
                "- Pintura geral | "
                "120 m² | R$ 3.500,00"
            )
        )

        submitted = st.form_submit_button(
            "CRIAR ORÇAMENTO"
        )

        if submitted:

            if (
                nome_cliente
                and whatsapp_cliente
                and resumo_servicos
                and itens_valores
            ):

                if not WEBAPP_URL:

                    st.error(
                        "Por favor, configure "
                        "a URL do seu Apps Script "
                        "Web App no código."
                    )

                elif not INSTANCE_NAME_LOGADA:

                    st.error(
                        "Nenhum WhatsApp foi "
                        "configurado para este "
                        "usuário ou para a empresa."
                    )

                else:

                    with st.spinner(
                        "Registrando e processando proposta..."
                    ):

                        try:

                            payload = {

                                "nome": (
                                    nome_cliente
                                ),

                                "whatsapp": (
                                    whatsapp_cliente
                                ),

                                "resumo": (
                                    resumo_servicos
                                ),

                                "itens": (
                                    itens_valores
                                ),

                                # =================================================
                                # INSTÂNCIA EFETIVA
                                # =================================================

                                "instance": (
                                    INSTANCE_NAME_LOGADA
                                ),

                                "empresa_id": (
                                    EMPRESA_ID_LOGADA
                                ),

                                "vendedor": (
                                    NOME_USUARIO_LOGADO
                                ),

                                "usuario_id": (
                                    st.session_state.get(
                                        "usuario_id",
                                        ""
                                    )
                                ),

                            }

                            response = (
                                requests.post(
                                    WEBAPP_URL,
                                    json=payload,
                                    timeout=30
                                )
                            )

                            if (
                                response.status_code
                                == 200
                                and
                                response.json().get(
                                    "status"
                                )
                                == "success"
                            ):

                                st.success(
                                    f"✅ Orçamento para "
                                    f"**{nome_cliente}** "
                                    "registrado com sucesso!"
                                )

                            else:

                                st.error(
                                    "Erro ao registrar: "
                                    f"{response.text}"
                                )

                        except Exception as e:

                            st.error(
                                "Falha na comunicação: "
                                f"{e}"
                            )

            else:

                st.error(
                    "Por favor, preencha todos "
                    "os campos obrigatórios (*)."
                )


# =================================================================================
# PAINEL DE ORÇAMENTOS
# =================================================================================

elif menu == "📋 Painel de Orçamentos":

    st.title(
        "📋 Painel de Orçamentos"
    )

    st.write(
        "Acompanhe quantidade, volume financeiro "
        "e desempenho por período e vendedor."
    )

    st.divider()

    df_dados = (
        carregar_dados_planilha()
    )

    if (
        df_dados is not None
        and not df_dados.empty
    ):

        df_dados = df_dados.copy()

        df_dados.columns = (
            df_dados.columns
            .astype(str)
            .str.strip()
        )

        # ------------------------------------------------------------------
        # IDENTIFICAÇÃO DAS COLUNAS
        # ------------------------------------------------------------------

        col_carimbo = next(
            (
                c
                for c in df_dados.columns
                if (
                    "carimbo"
                    in c.lower()
                    or
                    "data"
                    in c.lower()
                )
            ),
            df_dados.columns[0]
        )

        col_nome = next(
            (
                c
                for c in df_dados.columns
                if "nome" in c.lower()
            ),
            df_dados.columns[1]
        )

        col_whats = next(
            (
                c
                for c in df_dados.columns
                if (
                    "whatsapp"
                    in c.lower()
                    or
                    "zap"
                    in c.lower()
                )
            ),
            df_dados.columns[2]
        )

        col_resumo = next(
            (
                c
                for c in df_dados.columns
                if "resumo" in c.lower()
            ),
            df_dados.columns[3]
        )

        col_itens = next(
            (
                c
                for c in df_dados.columns
                if "itens" in c.lower()
            ),
            df_dados.columns[4]
        )

        col_status = next(
            (
                c
                for c in df_dados.columns
                if "status" in c.lower()
            ),
            df_dados.columns[5]
        )

        col_empresa = next(
            (
                c
                for c in df_dados.columns
                if "empresa_id"
                in c.lower()
            ),
            None
        )

        col_vendedor = next(
            (
                c
                for c in df_dados.columns
                if "vendedor"
                in c.lower()
            ),
            None
        )

        col_usuario = next(
            (
                c
                for c in df_dados.columns
                if "usuario_id"
                in c.lower()
            ),
            None
        )

        col_pdf = next(
            (
                c
                for c in df_dados.columns
                if str(c).strip().lower()
                in {
                    "pdf_link",
                    "pdf link",
                    "proposta_pdf",
                    "proposta pdf",
                    "link_pdf",
                    "link pdf",
                }
            ),
            None
        )

        if col_pdf is None:

            col_pdf = next(
                (
                    c
                    for c in df_dados.columns
                    if (
                        "pdf"
                        in str(c).lower()
                        or
                        "link"
                        in str(c).lower()
                    )
                ),
                None
            )

        # ------------------------------------------------------------------
        # DATA
        # ------------------------------------------------------------------

        df_dados["Data_Parsed"] = (
            pd.to_datetime(
                df_dados[col_carimbo],
                dayfirst=True,
                errors="coerce"
            )
        )

        # ------------------------------------------------------------------
        # EMPRESA
        # ------------------------------------------------------------------

        if col_empresa:

            empresa_clean = (
                df_dados[col_empresa]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
            )

            empresa_logada = (
                str(
                    EMPRESA_ID_LOGADA
                )
                .strip()
                .lower()
            )

            df_dados = (
                df_dados[
                    empresa_clean
                    == empresa_logada
                ]
                .copy()
            )

        else:

            st.warning(
                "A coluna Empresa_ID ainda "
                "não foi encontrada em "
                "Form_Responses."
            )

        # ------------------------------------------------------------------
        # VENDEDOR
        # ------------------------------------------------------------------

        perfil_normalizado = (
            str(
                PERFIL_ACESSO_LOGADO
            )
            .strip()
            .lower()
        )

        if col_vendedor:

            df_dados[
                "Vendedor_Exibicao"
            ] = (
                df_dados[col_vendedor]
                .fillna("")
                .astype(str)
                .str.strip()
            )

        else:

            df_dados[
                "Vendedor_Exibicao"
            ] = ""

        if (
            perfil_normalizado
            != "administrador"
        ):

            vendedor_logado = (
                str(
                    NOME_USUARIO_LOGADO
                )
                .strip()
                .lower()
            )

            df_dados = (
                df_dados[
                    df_dados[
                        "Vendedor_Exibicao"
                    ]
                    .str.lower()
                    .eq(
                        vendedor_logado
                    )
                ]
                .copy()
            )

        # ------------------------------------------------------------------
        # STATUS
        # ------------------------------------------------------------------

        df_dados[
            "Status_Clean"
        ] = (
            df_dados[col_status]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        df_base = (
            df_dados[
                df_dados[
                    "Status_Clean"
                ]
                .isin(
                    [
                        "concluído",
                        "concluido"
                    ]
                )
            ]
            .copy()
        )

        if df_base.empty:

            st.info(
                "Nenhum orçamento concluído "
                "encontrado para este acesso."
            )

        else:

            # ------------------------------------------------------------------
            # VALOR TOTAL
            # ------------------------------------------------------------------

            col_valor = next(
                (
                    c
                    for c in df_base.columns
                    if (
                        str(c)
                        .strip()
                        .lower()
                        in {
                            "valor_total",
                            "valor total",
                            "valor_total_calculado",
                            "valor total calculado",
                        }
                        or
                        "valor_total"
                        in str(c)
                        .strip()
                        .lower()
                    )
                ),
                None
            )

            if col_valor is None:

                st.warning(
                    "A coluna Valor_Total (K) "
                    "ainda não foi encontrada "
                    "em Form_Responses."
                )

                df_base[
                    "Valor_Total"
                ] = 0.0

            else:

                def parse_valor_brasileiro(
                    valor
                ):

                    texto = (
                        str(
                            valor or ""
                        )
                        .strip()
                    )

                    if not texto:

                        return 0.0

                    texto = re.sub(
                        r"[^0-9,.-]",
                        "",
                        texto
                    )

                    if not texto:

                        return 0.0

                    if (
                        ","
                        in texto
                        and "."
                        in texto
                    ):

                        if (
                            texto.rfind(",")
                            >
                            texto.rfind(".")
                        ):

                            texto = (
                                texto
                                .replace(
                                    ".",
                                    ""
                                )
                                .replace(
                                    ",",
                                    "."
                                )
                            )

                        else:

                            texto = (
                                texto
                                .replace(
                                    ",",
                                    ""
                                )
                            )

                    elif "," in texto:

                        texto = (
                            texto
                            .replace(
                                ",",
                                "."
                            )
                        )

                    try:

                        return float(
                            texto
                        )

                    except (
                        ValueError,
                        TypeError
                    ):

                        return 0.0

                df_base[
                    "Valor_Total"
                ] = (
                    df_base[
                        col_valor
                    ]
                    .apply(
                        parse_valor_brasileiro
                    )
                )

            # ------------------------------------------------------------------
            # FILTROS
            # ------------------------------------------------------------------

            st.subheader(
                "🔎 Filtros"
            )

            (
                col_filtro1,
                col_filtro2,
                col_filtro3
            ) = st.columns(
                [1, 1, 1]
            )

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

                data_min = (
                    df_base[
                        "Data_Parsed"
                    ].min()
                )

                data_max = (
                    df_base[
                        "Data_Parsed"
                    ].max()
                )

                if (
                    pd.isna(data_min)
                    or
                    pd.isna(data_max)
                ):

                    data_min = (
                        pd.Timestamp.now()
                    )

                    data_max = (
                        pd.Timestamp.now()
                    )

                intervalo_datas = (
                    st.date_input(
                        "Intervalo",
                        value=(
                            data_min.date(),
                            data_max.date(),
                        ),
                    )
                )

            with col_filtro3:

                if (
                    perfil_normalizado
                    == "administrador"
                    and
                    col_vendedor
                    and
                    not df_base.empty
                ):

                    vendedores = sorted(
                        [
                            v
                            for v in
                            df_base[
                                "Vendedor_Exibicao"
                            ]
                            .dropna()
                            .astype(str)
                            .str.strip()
                            .unique()
                            if v
                        ]
                    )

                    vendedor_filtro = (
                        st.selectbox(
                            "Vendedor",
                            [
                                "Todos"
                            ]
                            + vendedores,
                            index=0,
                        )
                    )

                else:

                    vendedor_filtro = (
                        "Todos"
                    )

            agora = (
                pd.Timestamp.now()
            )

            if len(
                intervalo_datas
            ) == 2:

                inicio_custom = (
                    pd.Timestamp(
                        intervalo_datas[0]
                    )
                )

                fim_custom = (
                    pd.Timestamp(
                        intervalo_datas[1]
                    )
                    + pd.Timedelta(
                        days=1
                    )
                    - pd.Timedelta(
                        seconds=1
                    )
                )

            else:

                inicio_custom = (
                    pd.Timestamp(
                        intervalo_datas[0]
                    )
                )

                fim_custom = (
                    inicio_custom
                    + pd.Timedelta(
                        days=1
                    )
                    - pd.Timedelta(
                        seconds=1
                    )
                )

            if periodo == "Hoje":

                inicio_periodo = (
                    agora.normalize()
                )

                fim_periodo = (
                    inicio_periodo
                    + pd.Timedelta(
                        days=1
                    )
                    - pd.Timedelta(
                        seconds=1
                    )
                )

            elif periodo == "Últimos 7 dias":

                inicio_periodo = (
                    agora.normalize()
                    - pd.Timedelta(
                        days=6
                    )
                )

                fim_periodo = agora

            elif periodo == "Últimos 30 dias":

                inicio_periodo = (
                    agora.normalize()
                    - pd.Timedelta(
                        days=29
                    )
                )

                fim_periodo = agora

            elif periodo == "Este ano":

                inicio_periodo = (
                    pd.Timestamp(
                        year=agora.year,
                        month=1,
                        day=1
                    )
                )

                fim_periodo = agora

            elif periodo == "Todo o período":

                inicio_periodo = (
                    df_base[
                        "Data_Parsed"
                    ].min()
                )

                fim_periodo = (
                    df_base[
                        "Data_Parsed"
                    ].max()
                )

            else:

                inicio_periodo = (
                    pd.Timestamp(
                        year=agora.year,
                        month=agora.month,
                        day=1
                    )
                )

                fim_periodo = agora

            inicio_final = max(
                inicio_periodo,
                inicio_custom
            )

            fim_final = min(
                fim_periodo,
                fim_custom
            )

            df_filtrado = (
                df_base[
                    (
                        df_base[
                            "Data_Parsed"
                        ]
                        >= inicio_final
                    )
                    &
                    (
                        df_base[
                            "Data_Parsed"
                        ]
                        <= fim_final
                    )
                ]
                .copy()
            )

            if (
                perfil_normalizado
                == "administrador"
                and
                vendedor_filtro
                != "Todos"
            ):

                df_filtrado = (
                    df_filtrado[
                        df_filtrado[
                            "Vendedor_Exibicao"
                        ].eq(
                            vendedor_filtro
                        )
                    ]
                    .copy()
                )

            # ------------------------------------------------------------------
            # KPIs
            # ------------------------------------------------------------------

            qtd_orcamentos = (
                len(df_filtrado)
            )

            valor_total = (
                df_filtrado[
                    "Valor_Total"
                ].sum()
            )

            ticket_medio = (
                valor_total
                / qtd_orcamentos
                if qtd_orcamentos
                else 0.0
            )

            qtd_vendedores = (
                df_filtrado[
                    "Vendedor_Exibicao"
                ]
                .replace(
                    "",
                    pd.NA
                )
                .dropna()
                .nunique()
            )

            def moeda_br(
                valor
            ):

                return (
                    f"R$ {valor:,.2f}"
                    .replace(
                        ",",
                        "X"
                    )
                    .replace(
                        ".",
                        ","
                    )
                    .replace(
                        "X",
                        "."
                    )
                )

            (
                kpi1,
                kpi2,
                kpi3,
                kpi4
            ) = st.columns(4)

            with kpi1:

                st.metric(
                    "Orçamentos",
                    f"{qtd_orcamentos}"
                )

            with kpi2:

                st.metric(
                    "Valor Total Orçado",
                    moeda_br(
                        valor_total
                    )
                )

            with kpi3:

                st.metric(
                    "Ticket Médio",
                    moeda_br(
                        ticket_medio
                    )
                )

            with kpi4:

                if (
                    perfil_normalizado
                    == "administrador"
                ):

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
            # GRÁFICO 1 — EVOLUÇÃO MENSAL
            # ------------------------------------------------------------------

            st.subheader(
                "📈 Evolução dos Orçamentos"
            )

            df_grafico = (
                df_filtrado
                .dropna(
                    subset=[
                        "Data_Parsed"
                    ]
                )
                .copy()
            )

            if not df_grafico.empty:

                df_grafico["Mes"] = (
                    df_grafico[
                        "Data_Parsed"
                    ]
                    .dt.to_period("M")
                    .dt.to_timestamp()
                )

                mensal = (
                    df_grafico
                    .groupby(
                        "Mes",
                        as_index=False
                    )
                    .agg(
                        Valor_Total=(
                            "Valor_Total",
                            "sum"
                        )
                    )
                    .sort_values(
                        "Mes"
                    )
                )

                mensal[
                    "Mes_Label"
                ] = (
                    mensal[
                        "Mes"
                    ]
                    .dt.strftime(
                        "%m/%Y"
                    )
                )

                mensal[
                    "Valor_Label"
                ] = (
                    mensal[
                        "Valor_Total"
                    ]
                    .apply(
                        moeda_br
                    )
                )

                ordem_meses = (
                    mensal[
                        "Mes_Label"
                    ]
                    .tolist()
                )

                chart_evolucao_spec = {

                    "height": 300,

                    "width": "container",

                    "layer": [

                        {
                            "mark": {
                                "type": "line",
                                "point": {
                                    "filled": True,
                                    "size": 80
                                },
                                "strokeWidth": 3,
                                "color": "#2F5D4F"
                            },

                            "encoding": {

                                "x": {
                                    "field": "Mes_Label",
                                    "type": "ordinal",
                                    "sort": ordem_meses,
                                    "axis": {
                                        "title": None,
                                        "labelAngle": 0
                                    }
                                },

                                "y": {
                                    "field": "Valor_Total",
                                    "type": "quantitative",
                                    "axis": {
                                        "title": None,
                                        "format": ",.0f"
                                    }
                                },

                                "tooltip": [

                                    {
                                        "field": "Mes_Label",
                                        "type": "nominal",
                                        "title": "Mês"
                                    },

                                    {
                                        "field": "Valor_Label",
                                        "type": "nominal",
                                        "title": "Valor Total"
                                    }

                                ]
                            }
                        },

                        {
                            "mark": {
                                "type": "text",
                                "dy": -14,
                                "fontSize": 13,
                                "fontWeight": "bold",
                                "color": "#16271F"
                            },

                            "encoding": {

                                "x": {
                                    "field": "Mes_Label",
                                    "type": "ordinal",
                                    "sort": ordem_meses
                                },

                                "y": {
                                    "field": "Valor_Total",
                                    "type": "quantitative"
                                },

                                "text": {
                                    "field": "Valor_Label",
                                    "type": "nominal"
                                }

                            }
                        }

                    ]
                }

                st.vega_lite_chart(
                    mensal,
                    chart_evolucao_spec,
                    use_container_width=True,
                )

            else:

                st.info(
                    "Sem dados para o gráfico "
                    "no período selecionado."
                )

            # ------------------------------------------------------------------
            # GRÁFICO 2 — DESEMPENHO POR VENDEDOR
            # ------------------------------------------------------------------

            if (
                perfil_normalizado
                == "administrador"
            ):

                st.subheader(
                    "👥 Desempenho por Vendedor"
                )

                if not df_filtrado.empty:

                    por_vendedor = (
                        df_filtrado
                        .groupby(
                            "Vendedor_Exibicao",
                            as_index=False
                        )
                        .agg(
                            Orçamentos=(
                                "Valor_Total",
                                "size"
                            ),
                            Valor_Total=(
                                "Valor_Total",
                                "sum"
                            )
                        )
                        .sort_values(
                            "Valor_Total",
                            ascending=False
                        )
                    )

                    por_vendedor = (
                        por_vendedor.rename(
                            columns={
                                "Vendedor_Exibicao":
                                "Vendedor"
                            }
                        )
                    )

                    por_vendedor[
                        "Valor_Label"
                    ] = (
                        por_vendedor[
                            "Valor_Total"
                        ]
                        .apply(
                            moeda_br
                        )
                    )

                    ordem_vendedores = (
                        por_vendedor[
                            "Vendedor"
                        ]
                        .tolist()
                    )

                    (
                        col_chart1,
                        col_chart2
                    ) = st.columns(2)

                    with col_chart1:

                        st.caption(
                            "Quantidade de orçamentos"
                        )

                        chart_qtd_spec = {

                            "height": 300,

                            "width": "container",

                            "layer": [

                                {

                                    "mark": {
                                        "type": "bar",
                                        "color": "#2F5D4F",
                                        "cornerRadiusTopLeft": 6,
                                        "cornerRadiusTopRight": 6
                                    },

                                    "encoding": {

                                        "x": {
                                            "field": "Vendedor",
                                            "type": "nominal",
                                            "sort": ordem_vendedores,
                                            "axis": {
                                                "title": None,
                                                "labelAngle": 0
                                            }
                                        },

                                        "y": {
                                            "field": "Orçamentos",
                                            "type": "quantitative",
                                            "axis": {
                                                "title": None,
                                                "format": "d"
                                            }
                                        },

                                        "tooltip": [

                                            {
                                                "field": "Vendedor",
                                                "type": "nominal",
                                                "title": "Vendedor"
                                            },

                                            {
                                                "field": "Orçamentos",
                                                "type": "quantitative",
                                                "title": "Orçamentos",
                                                "format": "d"
                                            }

                                        ]
                                    }
                                },

                                {

                                    "mark": {
                                        "type": "text",
                                        "dy": -10,
                                        "fontSize": 14,
                                        "fontWeight": "bold",
                                        "color": "#16271F"
                                    },

                                    "encoding": {

                                        "x": {
                                            "field": "Vendedor",
                                            "type": "nominal",
                                            "sort": ordem_vendedores
                                        },

                                        "y": {
                                            "field": "Orçamentos",
                                            "type": "quantitative"
                                        },

                                        "text": {
                                            "field": "Orçamentos",
                                            "type": "quantitative",
                                            "format": "d"
                                        }

                                    }
                                }

                            ]
                        }

                        st.vega_lite_chart(
                            por_vendedor,
                            chart_qtd_spec,
                            use_container_width=True,
                        )

                    with col_chart2:

                        st.caption(
                            "Valor total orçado"
                        )

                        chart_valor_spec = {

                            "height": 300,

                            "width": "container",

                            "layer": [

                                {

                                    "mark": {
                                        "type": "bar",
                                        "color": "#B9954A",
                                        "cornerRadiusTopLeft": 6,
                                        "cornerRadiusTopRight": 6
                                    },

                                    "encoding": {

                                        "x": {
                                            "field": "Vendedor",
                                            "type": "nominal",
                                            "sort": ordem_vendedores,
                                            "axis": {
                                                "title": None,
                                                "labelAngle": 0
                                            }
                                        },

                                        "y": {
                                            "field": "Valor_Total",
                                            "type": "quantitative",
                                            "axis": {
                                                "title": None,
                                                "format": ",.0f"
                                            }
                                        },

                                        "tooltip": [

                                            {
                                                "field": "Vendedor",
                                                "type": "nominal",
                                                "title": "Vendedor"
                                            },

                                            {
                                                "field": "Valor_Label",
                                                "type": "nominal",
                                                "title": "Valor Total"
                                            }

                                        ]
                                    }
                                },

                                {

                                    "mark": {
                                        "type": "text",
                                        "dy": -10,
                                        "fontSize": 13,
                                        "fontWeight": "bold",
                                        "color": "#16271F"
                                    },

                                    "encoding": {

                                        "x": {
                                            "field": "Vendedor",
                                            "type": "nominal",
                                            "sort": ordem_vendedores
                                        },

                                        "y": {
                                            "field": "Valor_Total",
                                            "type": "quantitative"
                                        },

                                        "text": {
                                            "field": "Valor_Label",
                                            "type": "nominal"
                                        }

                                    }
                                }

                            ]
                        }

                        st.vega_lite_chart(
                            por_vendedor,
                            chart_valor_spec,
                            use_container_width=True,
                        )

                else:

                    st.info(
                        "Sem dados por vendedor "
                        "no período selecionado."
                    )

            # ------------------------------------------------------------------
            # HISTÓRICO
            # ------------------------------------------------------------------

            st.markdown("---")

            st.subheader(
                "📋 Histórico de Orçamentos"
            )

            df_exibir = (
                pd.DataFrame()
            )

            df_exibir[
                "Data do Envio"
            ] = (
                df_filtrado[
                    "Data_Parsed"
                ]
                .dt.strftime(
                    "%d/%m/%Y %H:%M"
                )
            )

            df_exibir[
                "Vendedor"
            ] = (
                df_filtrado[
                    "Vendedor_Exibicao"
                ]
            )

            df_exibir[
                "Resumo do Serviço"
            ] = (
                df_filtrado[
                    col_resumo
                ]
            )

            df_exibir[
                "Valor Total"
            ] = (
                df_filtrado[
                    "Valor_Total"
                ]
                .apply(
                    moeda_br
                )
            )

            df_exibir[
                "Status"
            ] = (
                df_filtrado[
                    col_status
                ]
            )

            config_colunas = {

                "Data do Envio":
                    st.column_config.TextColumn(
                        "Data do Envio"
                    ),

                "Vendedor":
                    st.column_config.TextColumn(
                        "Vendedor"
                    ),

                "Resumo do Serviço":
                    st.column_config.TextColumn(
                        "Resumo do Serviço"
                    ),

                "Valor Total":
                    st.column_config.TextColumn(
                        "Valor Total"
                    ),

                "Status":
                    st.column_config.TextColumn(
                        "Status"
                    ),

            }

            if col_pdf:

                df_exibir[
                    "Proposta (PDF)"
                ] = (
                    df_filtrado[
                        col_pdf
                    ]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                )

                config_colunas[
                    "Proposta (PDF)"
                ] = (
                    st.column_config.LinkColumn(
                        "Proposta (PDF)",
                        help=(
                            "Clique para abrir "
                            "o PDF da proposta."
                        ),
                        display_text=(
                            "📥 Abrir PDF"
                        ),
                        validate=(
                            "^https?://.*$"
                        )
                    )
                )

            else:

                df_exibir[
                    "Proposta (PDF)"
                ] = (
                    "Aguardando Link"
                )

                config_colunas[
                    "Proposta (PDF)"
                ] = (
                    st.column_config.TextColumn(
                        "Proposta (PDF)"
                    )
                )

            for col in df_exibir.columns:

                if (
                    col
                    != "Proposta (PDF)"
                ):

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
                column_config=(
                    config_colunas
                )
            )

    else:

        st.info(
            "Nenhum dado encontrado "
            "na planilha."
        )


# =================================================================================
# CONECTAR WHATSAPP
# =================================================================================

elif menu == "📱 Conectar WhatsApp":

    st.title(
        "📱 Status da Conexão WhatsApp"
    )

    st.write(
        "Gerencie a conexão da Evolution API "
        "para disparos automáticos de propostas."
    )

    st.divider()

    if not INSTANCE_NAME_LOGADA:

        st.warning(
            "⚠️ Nenhuma instância de WhatsApp "
            "foi configurada para este usuário "
            "nem para a empresa."
        )

        st.info(
            "Preencha Evolution_Instance em "
            "Usuarios para um WhatsApp individual "
            "ou em Empresas para o WhatsApp "
            "compartilhado."
        )

    elif not evolution_configurada():

        st.error(
            "A configuração da Evolution API "
            "não foi encontrada nos Secrets "
            "do Streamlit."
        )

        st.info(
            "Verifique se existe a seção "
            "[evolution] com api_url e api_key."
        )

    else:

        st.caption(
            "Instância utilizada nesta sessão: "
            f"**{INSTANCE_NAME_LOGADA}**"
        )

        st.markdown("")

        col_btn, col_status = (
            st.columns([1, 2])
        )

        with col_btn:

            verificar = st.button(
                "🔄 Verificar Status / Gerar QR Code"
            )

        # ================================================================
        # PREPARAÇÃO AUTOMÁTICA
        # ================================================================
        #
        # Mesmo sem clicar no botão, a página
        # já tenta preparar a instância.
        #
        # O botão serve para atualizar/refazer
        # o processo.
        #
        # ================================================================

        with st.spinner(
            "Verificando WhatsApp..."
        ):

            preparo = (
                preparar_instancia_para_conexao(
                    INSTANCE_NAME_LOGADA
                )
            )

        if not preparo["ok"]:

            st.error(
                "Não foi possível preparar "
                "a instância do WhatsApp."
            )

            if preparo.get(
                "mensagem"
            ):

                st.info(
                    preparo[
                        "mensagem"
                    ]
                )

        else:

            if preparo.get(
                "criada_agora"
            ):

                st.success(
                    "✅ Instância criada "
                    "automaticamente na "
                    "Evolution API."
                )

            # ============================================================
            # PRIMEIRO:
            # tenta usar QR retornado pela criação
            # ============================================================

            base64_qr = None
            pairing_code = None
            code = None

            criacao = (
                preparo.get(
                    "criacao"
                )
            )

            if criacao:

                (
                    base64_qr,
                    pairing_code,
                    code
                ) = (
                    extrair_qr_da_resposta(
                        criacao.get(
                            "data",
                            {}
                        )
                    )
                )

            # ============================================================
            # DEPOIS:
            # consulta o estado atual
            # ============================================================

            estado = obter_estado_instancia(
                INSTANCE_NAME_LOGADA
            )

            # ============================================================
            # CONECTADO
            # ============================================================

            if (
                estado["state"]
                == "open"
            ):

                st.success(
                    "🟢 **WhatsApp Conectado "
                    "e Operacional!**"
                )

                st.info(
                    "Sua instância está pronta "
                    "para enviar as propostas "
                    "automaticamente aos clientes."
                )

            # ============================================================
            # NÃO CONECTADO
            # ============================================================

            else:

                # Se ainda não temos QR,
                # solicitamos via endpoint connect.
                if not base64_qr:

                    with st.spinner(
                        "Preparando QR Code..."
                    ):

                        qr_resultado = (
                            obter_qr_code_evolution(
                                INSTANCE_NAME_LOGADA
                            )
                        )

                    if qr_resultado[
                        "ok"
                    ]:

                        base64_qr = (
                            qr_resultado[
                                "base64"
                            ]
                        )

                        pairing_code = (
                            qr_resultado[
                                "pairing_code"
                            ]
                        )

                        code = (
                            qr_resultado[
                                "code"
                            ]
                        )

                    else:

                        # Tenta mais uma vez
                        # somente se a instância
                        # acabou de ser criada.
                        if (
                            preparo.get(
                                "criada_agora"
                            )
                        ):

                            qr_resultado = (
                                obter_qr_code_evolution(
                                    INSTANCE_NAME_LOGADA
                                )
                            )

                            if qr_resultado[
                                "ok"
                            ]:

                                base64_qr = (
                                    qr_resultado[
                                        "base64"
                                    ]
                                )

                                pairing_code = (
                                    qr_resultado[
                                        "pairing_code"
                                    ]
                                )

                                code = (
                                    qr_resultado[
                                        "code"
                                    ]
                                )

                # ========================================================
                # MOSTRA QR
                # ========================================================

                if base64_qr:

                    st.warning(
                        "🟡 **WhatsApp aguardando "
                        "pareamento**"
                    )

                    st.write(
                        "Abra o WhatsApp no celular "
                        "que será conectado, entre em "
                        "**Aparelhos Conectados** e "
                        "escaneie o QR Code abaixo."
                    )

                    qr_bytes = (
                        obter_qr_bytes(
                            base64_qr
                        )
                    )

                    if qr_bytes:

                        col_qr1, col_qr2, col_qr3 = (
                            st.columns(
                                [1, 1, 1]
                            )
                        )

                        with col_qr2:

                            st.image(
                                qr_bytes,
                                width=300
                            )

                    else:

                        st.error(
                            "A Evolution API "
                            "retornou um QR Code, "
                            "mas não foi possível "
                            "decodificar a imagem."
                        )

                    if pairing_code:

                        st.caption(
                            "Código de pareamento: "
                            f"**{pairing_code}**"
                        )

                else:

                    st.warning(
                        "A instância existe, "
                        "mas a Evolution API "
                        "ainda não retornou "
                        "um QR Code."
                    )

                    if code:

                        st.caption(
                            f"Código retornado pela "
                            f"Evolution API: **{code}**"
                        )

                    st.info(
                        "Clique novamente em "
                        "**Verificar Status / "
                        "Gerar QR Code**."
                    )

                    # Mostra eventual erro técnico
                    # somente para diagnóstico.
                    if (
                        'qr_resultado'
                        in locals()
                        and
                        not qr_resultado.get(
                            "ok",
                            False
                        )
                    ):

                        status_qr = (
                            qr_resultado.get(
                                "status_code"
                            )
                        )

                        if status_qr:

                            st.caption(
                                "Status da API ao "
                                "solicitar QR: "
                                f"{status_qr}"
                            )

            # ============================================================
            # DEBUG CONTROLADO
            # ============================================================

            if (
                verificar
                and
                preparo["ok"]
            ):

                st.toast(
                    "Status atualizado.",
                    icon="✅"
                )
