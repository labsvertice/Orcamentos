import base64
import io
import os
import re
import time
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st
from PIL import Image

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
# A instância NÃO é fixa no código.
#
# Regra:
#
# 1. Evolution_Instance do usuário
# 2. se vazio → Evolution_Instance da empresa
# 3. se ambos vazios → nenhum WhatsApp configurado
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

    /* Mantém o cabeçalho nativo do Streamlit para preservar
       os controles de abrir/fechar a barra lateral, inclusive no celular. */
    header[data-testid="stHeader"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }

    /* Oculta apenas a decoração superior, sem remover o controle da sidebar. */
    header[data-testid="stHeader"] [data-testid="stDecoration"] {
        display: none !important;
    }

    .main .block-container,
    [data-testid="stMainBlockContainer"] {
        padding-top: 1.2rem !important;
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

