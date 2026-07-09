#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SISTEMA INSTITUCIONAL DE GESTION DOCUMENTAL ACR / AFA — STREAMLIT WEB v12.0.0
Analisis de Causa Raiz (ACR) y Analisis de Fallas y Acciones (AFA)
Version: 12.0.0 | Normativa: ISO 9001, ISO 14224, TPM, RCM
NUEVO: Historico completo, IA Gemini integrada, Corrector ortografico,
       Configuracion persistente, Textos humanizados y profesionales
================================================================================
"""

import streamlit as st
import sqlite3
import io
import os
import json
import datetime
import base64
import tempfile
import uuid
import re
import time
from pathlib import Path
from PIL import Image

# ── ReportLab ─────────────────────────────────────────────────────────────────
from reportlab.lib import colors as rl_colors
from reportlab.lib.pagesizes import A4, landscape as rl_landscape
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, NextPageTemplate,
    Table, TableStyle, Paragraph, Spacer,
    Image as RLImage, PageBreak, HRFlowable
)

# ── Gemini AI ─────────────────────────────────────────────────────────────────
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# ── Spellchecker ─────────────────────────────────────────────────────────────
try:
    from spellchecker import SpellChecker
    SPELL_AVAILABLE = True
except ImportError:
    SPELL_AVAILABLE = False

# ==============================================================================
# CONFIGURACION STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="Sistema ACR / AFA — ORICA",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# CONFIGURACION PERSISTENTE — Archivo JSON
# ==============================================================================
CONFIG_FILE = "config_sistema_acr_afa.json"

DEFAULT_CONFIG = {
    "nombre_empresa": "EMPRESA INDUSTRIAL S.A.",
    "direccion": "",
    "telefono": "",
    "correo": "",
    "gerente_planta": "",
    "jefe_mantenimiento": "",
    "texto_encabezado": "SISTEMA DE GESTION DE MANTENIMIENTO\nDEPARTAMENTO DE MANTENIMIENTO E INGENIERIA",
    "texto_pie_pagina": "Documento Controlado — Prohibida su reproduccion sin autorizacion | Normativa: ISO 9001 / ISO 14224 / TPM / RCM",
    "gemini_api_key": "",
    "gemini_model": "gemini-1.5-flash",
    "tema_color": "azul_orica",
    "ultima_modificacion": "",
}

def cargar_config():
    """Carga configuracion desde archivo JSON persistente."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def guardar_config(cfg):
    """Guarda configuracion en archivo JSON persistente."""
    cfg["ultima_modificacion"] = datetime.datetime.now().isoformat()
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return cfg

# ==============================================================================
# ESTILOS GLOBALES
# ==============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1a2f4a 0%, #1e3a5f 60%, #162d47 100%) !important; border-right: 3px solid #1e60a8; }
[data-testid="stSidebar"] * { color: #e8edf2 !important; }
[data-testid="stSidebar"] .stButton > button { background: rgba(255,255,255,0.08) !important; border: 1px solid rgba(255,255,255,0.18) !important; color: #e8edf2 !important; border-radius: 6px !important; font-weight: 500 !important; transition: all .2s !important; }
[data-testid="stSidebar"] .stButton > button:hover { background: rgba(30,96,168,0.6) !important; border-color: #4a90d9 !important; color: white !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15) !important; }
.inst-header-main { background: linear-gradient(135deg, #1e3a5f 0%, #1e60a8 100%); color: white; padding: 18px 28px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #4a90d9; box-shadow: 0 4px 16px rgba(30,58,95,.2); }
.inst-title { font-size: 1.5rem; font-weight: 700; letter-spacing: .4px; margin: 0; }
.inst-sub { font-size: .82rem; opacity: .82; margin-top: 4px; }
.seccion-band { background: linear-gradient(90deg, #1e60a8 0%, #2a7fd4 100%); color: white !important; font-weight: 600; padding: 8px 16px; border-radius: 6px; margin: 16px 0 8px 0; font-size: .92rem; letter-spacing: .3px; border-left: 4px solid #ffc107; box-shadow: 0 2px 6px rgba(30,96,168,.25); }
.seccion-cat { background: #1e3a5f; color: white !important; font-weight: 700; padding: 8px 14px; border-radius: 6px; margin: 12px 0 6px 0; font-size: .9rem; display: flex; align-items: center; gap: 8px; }
[data-testid="metric-container"] { background: white; border: 1px solid #dee2e6; border-radius: 10px; padding: 16px 20px; box-shadow: 0 2px 8px rgba(30,58,95,.08); border-top: 3px solid #1e60a8; }
[data-testid="metric-container"] [data-testid="stMetricLabel"] { font-size: .82rem !important; color: #6c757d !important; font-weight: 600 !important; text-transform: uppercase; letter-spacing: .5px; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 700 !important; color: #1e3a5f !important; }
div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #1e60a8, #1a4f8a) !important; color: white !important; border: none !important; border-radius: 7px !important; font-weight: 600 !important; padding: 8px 20px !important; letter-spacing: .3px; box-shadow: 0 3px 10px rgba(30,96,168,.35) !important; transition: all .2s !important; }
div.stButton > button[kind="primary"]:hover { background: linear-gradient(135deg, #1a4f8a, #163d6e) !important; box-shadow: 0 5px 16px rgba(30,96,168,.45) !important; transform: translateY(-1px); }
div.stButton > button[kind="secondary"] { border: 1.5px solid #1e60a8 !important; color: #1e60a8 !important; border-radius: 7px !important; font-weight: 500 !important; background: white !important; }
div.stButton > button[kind="secondary"]:hover { background: #f0f6ff !important; }
.stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div > div { border: 1.5px solid #ced4da !important; border-radius: 7px !important; font-family: 'Inter', sans-serif !important; font-size: .9rem !important; transition: border-color .15s !important; }
.stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus { border-color: #1e60a8 !important; box-shadow: 0 0 0 3px rgba(30,96,168,.12) !important; }
.stTextInput label, .stTextArea label, .stSelectbox label, .stRadio label, .stDateInput label, .stNumberInput label { font-weight: 600 !important; color: #2c3e50 !important; font-size: .85rem !important; letter-spacing: .2px; }
.stTabs [data-baseweb="tab-list"] { background: #f0f4f8; border-radius: 10px 10px 0 0; border-bottom: 2px solid #1e60a8; gap: 2px; padding: 4px 4px 0; }
.stTabs [data-baseweb="tab"] { background: transparent !important; border-radius: 8px 8px 0 0 !important; color: #4a5568 !important; font-weight: 600 !important; font-size: .88rem !important; padding: 8px 16px !important; border: none !important; transition: all .15s !important; }
.stTabs [aria-selected="true"] { background: #1e60a8 !important; color: white !important; box-shadow: 0 -2px 8px rgba(30,96,168,.2) !important; }
.stTabs [data-baseweb="tab-panel"] { background: white; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 10px 10px; padding: 20px !important; }
[data-testid="stExpander"] { border: 1px solid #e2e8f0 !important; border-radius: 8px !important; margin-bottom: 6px !important; overflow: hidden; }
[data-testid="stExpander"] summary { background: #f8fafc !important; border-radius: 8px !important; font-weight: 600 !important; color: #1e3a5f !important; padding: 10px 14px !important; font-size: .88rem !important; }
[data-testid="stExpander"] summary:hover { background: #eef3fa !important; }
[data-testid="stDataFrame"] { border: 1px solid #dee2e6 !important; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
[data-testid="stAlert"] { border-radius: 8px !important; border-left-width: 4px !important; font-weight: 500 !important; }
.badge-estado { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: .76rem; font-weight: 700; letter-spacing: .4px; text-transform: uppercase; }
.badge-BORRADOR { background:#e9ecef; color:#495057; }
.badge-EN_ANALISIS { background:#cfe2ff; color:#084298; }
.badge-REVISADO { background:#fff3cd; color:#664d03; }
.badge-APROBADO { background:#d1e7dd; color:#0a3622; }
.badge-CERRADO { background:#d3d3d3; color:#212529; }
.badge-RECHAZADO { background:#f8d7da; color:#842029; }
.prio-chip { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: .76rem; font-weight: 700; }
.prio-BAJA { background:#d1f2eb; color:#0e6655; }
.prio-MEDIA { background:#fef9c3; color:#7d6608; }
.prio-ALTA { background:#fde8c8; color:#9c4221; }
.prio-CRITICA { background:#fcd0d0; color:#7b1818; border: 1px solid #e74c3c; }
.kpi-card { background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px 22px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,.06); transition: transform .2s, box-shadow .2s; }
.kpi-card:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,.1); }
.kpi-num { font-size: 2.4rem; font-weight: 800; line-height: 1.1; margin: 4px 0; }
.kpi-label { font-size: .78rem; color: #6c757d; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; }
.kpi-pend { color: #dc3545; border-top: 4px solid #dc3545; }
.kpi-proc { color: #fd7e14; border-top: 4px solid #fd7e14; }
.kpi-cerr { color: #198754; border-top: 4px solid #198754; }
.kpi-venc { color: #6f42c1; border-top: 4px solid #6f42c1; }
.kpi-total { color: #1e60a8; border-top: 4px solid #1e60a8; }
[data-testid="stForm"] { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 20px !important; }
hr { border: none; border-top: 1px solid #e9ecef; margin: 16px 0; }
[data-testid="stProgress"] > div > div { background: linear-gradient(90deg, #1e60a8, #4a90d9) !important; border-radius: 4px !important; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f1f1f1; }
::-webkit-scrollbar-thumb { background: #adb5bd; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #1e60a8; }
.ai-badge { display: inline-flex; align-items: center; gap: 6px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 4px 12px; border-radius: 20px; font-size: .75rem; font-weight: 600; }
.corr-badge { display: inline-flex; align-items: center; gap: 6px; background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 4px 12px; border-radius: 20px; font-size: .75rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# BASE DE DATOS — Singleton con cache de sesion + HISTORICO
# ==============================================================================
DB_PATH = "acr_afa_system.db"

@st.cache_resource
def get_db():
    """Crea y cachea la conexion a SQLite."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _crear_tablas(conn)
    return conn

def _crear_tablas(conn):
    stmts = [
        """CREATE TABLE IF NOT EXISTS documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_documento TEXT CHECK(tipo_documento IN ('ACR','AFA')) NOT NULL,
            codigo TEXT UNIQUE NOT NULL,
            fecha_reporte TEXT NOT NULL,
            estado TEXT DEFAULT 'BORRADOR',
            reportado_por TEXT NOT NULL,
            cargo_reportante TEXT, area_reportante TEXT,
            aprobado_por TEXT, fecha_aprobacion TEXT,
            desc_problema_inicial TEXT, que_contexto TEXT, como_ocurre TEXT,
            quien TEXT, donde TEXT, cuando TEXT, cuanto TEXT, cual TEXT,
            como_enfoque TEXT, porque_enfoque TEXT, problema_enfocado TEXT,
            fecha_inicio_analisis TEXT, lider_afa TEXT, responsables TEXT,
            area_equipo TEXT, metodologia TEXT DEFAULT 'WHY-WHY',
            causa_raiz_identificada TEXT, verificacion_causa TEXT,
            evidencia_causa TEXT, observaciones_cierre TEXT, fecha_cierre TEXT,
            prioridad TEXT DEFAULT 'MEDIA', impacto_produccion TEXT,
            impacto_seguridad TEXT, impacto_ambiental TEXT, costo_estimado REAL DEFAULT 0,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultima_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS sesiones_acr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_acr TEXT NOT NULL, sesion_num INTEGER NOT NULL,
            fecha TEXT, hora_inicio TEXT, duracion TEXT,
            participantes TEXT, observaciones TEXT,
            FOREIGN KEY (codigo_acr) REFERENCES documentos(codigo) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS condiciones_basicas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_acr TEXT NOT NULL, categoria_6m TEXT NOT NULL, item TEXT NOT NULL,
            condicion_ideal TEXT, condicion_actual TEXT,
            aplica TEXT DEFAULT 'SI', diferencia TEXT DEFAULT 'NO',
            FOREIGN KEY (codigo_acr) REFERENCES documentos(codigo) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS why_why (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_documento TEXT NOT NULL, rama_id TEXT NOT NULL,
            definicion TEXT, pq1 TEXT, pq2 TEXT, pq3 TEXT, pq4 TEXT, pq5 TEXT,
            causa_raiz TEXT, accion_causa_raiz TEXT, responsable TEXT,
            fecha TEXT, prioridad TEXT DEFAULT 'MEDIA',
            estatus TEXT DEFAULT 'PENDIENTE', comentarios TEXT,
            FOREIGN KEY (codigo_documento) REFERENCES documentos(codigo) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS acciones_inmediatas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_acr TEXT NOT NULL, accion TEXT NOT NULL,
            responsable TEXT, fecha TEXT, fecha_cierre TEXT,
            estado TEXT DEFAULT 'PENDIENTE', eficacia TEXT DEFAULT 'POR_VERIFICAR',
            FOREIGN KEY (codigo_acr) REFERENCES documentos(codigo) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS evidencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_documento TEXT NOT NULL, nombre_archivo TEXT NOT NULL,
            tipo_evidencia TEXT, descripcion TEXT,
            imagen_blob BLOB, tamano_bytes INTEGER, formato TEXT,
            fecha_captura TEXT, seccion TEXT DEFAULT 'GENERAL',
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (codigo_documento) REFERENCES documentos(codigo) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS configuracion_empresa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_empresa TEXT NOT NULL DEFAULT 'EMPRESA INDUSTRIAL S.A.',
            direccion TEXT, telefono TEXT, correo TEXT,
            gerente_planta TEXT, jefe_mantenimiento TEXT,
            logo_blob BLOB, logo_ruta TEXT,
            texto_encabezado TEXT, texto_pie_pagina TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        # ── NUEVO: Tabla de historico de documentos cerrados ──
        """CREATE TABLE IF NOT EXISTS historico_documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_documento TEXT NOT NULL,
            codigo TEXT NOT NULL,
            codigo_original TEXT,
            fecha_reporte TEXT,
            fecha_cierre TEXT,
            estado_final TEXT,
            reportado_por TEXT,
            area_equipo TEXT,
            desc_problema_inicial TEXT,
            problema_enfocado TEXT,
            causa_raiz_identificada TEXT,
            verificacion_causa TEXT,
            observaciones_cierre TEXT,
            prioridad TEXT,
            costo_estimado REAL DEFAULT 0,
            impacto_produccion TEXT,
            impacto_seguridad TEXT,
            impacto_ambiental TEXT,
            fecha_archivado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            motivo_archivo TEXT DEFAULT 'Cierre completo del ciclo ACR/AFA'
        )""",
        # ── NUEVO: Tabla de seguimiento de acciones historicas ──
        """CREATE TABLE IF NOT EXISTS historico_acciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_documento TEXT NOT NULL,
            tipo_accion TEXT NOT NULL,
            accion TEXT NOT NULL,
            responsable TEXT,
            fecha_limite TEXT,
            fecha_cierre TEXT,
            estado_final TEXT,
            eficacia TEXT,
            fecha_archivado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        # ── NUEVO: Tabla de repeticiones de problemas ──
        """CREATE TABLE IF NOT EXISTS repeticiones_problemas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_original TEXT NOT NULL,
            codigo_repeticion TEXT NOT NULL,
            area_equipo TEXT,
            desc_similaridad TEXT,
            fecha_detectado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notas TEXT
        )""",
    ]
    for s in stmts:
        try:
            conn.execute(s)
        except Exception:
            pass
    conn.commit()

def db_query(sql, params=()):
    return get_db().execute(sql, params).fetchall()

def db_one(sql, params=()):
    return get_db().execute(sql, params).fetchone()

def db_run(sql, params=()):
    conn = get_db()
    cur = conn.execute(sql, params)
    conn.commit()
    return cur.lastrowid

# ==============================================================================
# UTILIDADES
# ==============================================================================
def gen_codigo(tipo):
    now = datetime.datetime.now()
    uid = str(uuid.uuid4())[:4].upper()
    return f"{tipo}-{now.strftime('%Y%m')}-{uid}"

def img_to_bytes(pil_img, fmt="PNG"):
    buf = io.BytesIO()
    pil_img.save(buf, format=fmt)
    return buf.getvalue()

def badge(estado):
    return f'<span class="badge-{estado}">{estado.replace("_"," ")}</span>'

def prio_badge(p):
    return f'<span class="prio-{p}">{p}</span>'

def get_empresa_cfg():
    """Obtiene configuracion de empresa desde DB o JSON persistente."""
    row = db_one("SELECT * FROM configuracion_empresa LIMIT 1")
    if row:
        return dict(row)
    # Fallback a JSON
    cfg = cargar_config()
    return {
        'nombre_empresa': cfg.get('nombre_empresa', 'EMPRESA INDUSTRIAL S.A.'),
        'direccion': cfg.get('direccion', ''),
        'telefono': cfg.get('telefono', ''),
        'correo': cfg.get('correo', ''),
        'gerente_planta': cfg.get('gerente_planta', ''),
        'jefe_mantenimiento': cfg.get('jefe_mantenimiento', ''),
        'texto_encabezado': cfg.get('texto_encabezado', 'SISTEMA DE GESTION DE MANTENIMIENTO'),
        'texto_pie_pagina': cfg.get('texto_pie_pagina', 'Documento Controlado | Normativa: ISO 9001 / ISO 14224 / TPM / RCM'),
        'logo_blob': None,
    }

# ==============================================================================
# CORRECTOR ORTOGRAFICO
# ==============================================================================
_spell_checker = None

def get_spell_checker():
    global _spell_checker
    if _spell_checker is None and SPELL_AVAILABLE:
        _spell_checker = SpellChecker(language='es')
    return _spell_checker

def corregir_ortografia(texto):
    """Corrige errores ortograficos en el texto usando spellchecker."""
    if not texto or not SPELL_AVAILABLE:
        return texto
    
    spell = get_spell_checker()
    if spell is None:
        return texto
    
    # Preservar saltos de linea y estructura
    lineas = texto.split('\n')
    lineas_corregidas = []
    
    for linea in lineas:
        palabras = linea.split()
        palabras_corregidas = []
        for palabra in palabras:
            # Preservar mayusculas iniciales y puntuacion
            limpia = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑüÜ]', '', palabra)
            if not limpia:
                palabras_corregidas.append(palabra)
                continue
            
            # Verificar si la palabra esta mal escrita
            if limpia.lower() not in spell:
                candidatos = spell.candidates(limpia)
                if candidatos:
                    mejor = list(candidatos)[0]
                    # Restaurar mayuscula inicial si la original la tenia
                    if limpia[0].isupper():
                        mejor = mejor.capitalize()
                    # Reconstruir palabra con puntuacion original
                    prefijo = palabra[:palabra.index(limpia[0])] if palabra[0] != limpia[0] else ''
                    sufijo = palabra[palabra.index(limpia[-1])+1:] if palabra[-1] != limpia[-1] else ''
                    palabras_corregidas.append(prefijo + mejor + sufijo)
                else:
                    palabras_corregidas.append(palabra)
            else:
                palabras_corregidas.append(palabra)
        
        lineas_corregidas.append(' '.join(palabras_corregidas))
    
    return '\n'.join(lineas_corregidas)

# ==============================================================================
# INTEGRACION CON GEMINI AI
# ==============================================================================
def get_gemini_client():
    """Inicializa y retorna el cliente de Gemini si esta configurado."""
    cfg = cargar_config()
    api_key = cfg.get('gemini_api_key', '')
    if not api_key or not GEMINI_AVAILABLE:
        return None
    
    try:
        genai.configure(api_key=api_key)
        model_name = cfg.get('gemini_model', 'gemini-1.5-flash')
        return genai.GenerativeModel(model_name)
    except Exception as e:
        st.error(f"Error al configurar Gemini: {e}")
        return None

def generar_acr_con_ia(contexto_problema, tipo='ACR'):
    """Genera un ACR/AFA completo usando Gemini AI basado en el contexto del problema."""
    model = get_gemini_client()
    if model is None:
        return None
    
    prompt = f"""
Eres un especialista senior en Ingenieria Mecatronica con 20 años de experiencia en Analisis de Causa Raiz (ACR) 
y Analisis de Fallas y Acciones (AFA) en entornos industriales mineros (ORICA). 
Debes analizar el siguiente problema y generar un documento profesional, detallado y bien justificado.

CONTEXTO DEL PROBLEMA (descrito por el usuario):
{contexto_problema}

TIPO DE DOCUMENTO: {tipo}

Genera la respuesta en formato JSON con la siguiente estructura exacta:
{{
  "desc_problema_inicial": "Descripcion detallada y profesional del problema inicial...",
  "que_contexto": "Contexto completo de lo que se observo, incluyendo condiciones operativas...",
  "como_ocurre": "Explicacion tecnica detallada de como ocurre la falla, secuencia de eventos...",
  "quien": "Quien detecto o origino el problema, roles y responsabilidades...",
  "donde": "Ubicacion exacta, equipo, sistema, subsistema afectado...",
  "cuanto": "Magnitud del impacto: frecuencia, duracion, costos estimados, produccion perdida...",
  "cuando": "Cronologia exacta del evento, fecha, hora, turno, condiciones previas...",
  "cual": "Especificaciones tecnicas: modelo, serie, componentes, materiales involucrados...",
  "problema_enfocado": "Sintesis profesional del problema usando 5W+2H, redactado como un experto...",
  "causa_raiz_identificada": "Causa raiz principal identificada con fundamentacion tecnica...",
  "verificacion_causa": "Metodo y evidencia de verificacion de la causa raiz...",
  "evidencia_causa": "Evidencias tecnicas que sustentan el analisis...",
  "why_why": [
    {{
      "definicion": "Definicion precisa del problema para esta rama...",
      "pq1": "Primera respuesta al Por Que con fundamentacion tecnica...",
      "pq2": "Segunda respuesta al Por Que, profundizando en la causa...",
      "pq3": "Tercera respuesta al Por Que, identificando sistemas afectados...",
      "pq4": "Cuarta respuesta al Por Que, analizando causas de gestion o diseno...",
      "pq5": "Quinta respuesta al Por Que, llegando a la causa raiz fundamental...",
      "causa_raiz": "Causa raiz final identificada en esta rama...",
      "accion_causa_raiz": "Accion correctiva especifica, medible y con responsable...",
      "responsable": "Area o persona responsable de la accion...",
      "prioridad": "CRITICA/ALTA/MEDIA/BAJA"
    }}
  ]
}}

INSTRUCCIONES CRITICAS:
1. Los textos deben ser humanizados pero extremadamente profesionales y tecnicos.
2. Cada campo debe tener 2-4 parrafos detallados con terminologia de ingenieria mecatronica.
3. El analisis Why-Why debe ser profundo, no superficial. Justifica cada nivel.
4. Usa terminologia de mantenimiento industrial: confiabilidad, MTBF, MTTR, RCM, FMEA.
5. Considera aspectos de: lubricacion, alineacion, vibracion, termografia, analisis de aceite.
6. Incluye referencias a estandares ISO 14224, ISO 9001 cuando sea relevante.
7. Las acciones deben ser SMART: Especificas, Medibles, Alcanzables, Relevantes, con Tiempo.
8. NO uses lenguaje robotico. Escribe como un ingeniero senior experimentado.
9. Cada respuesta "Por Que" debe ser una explicacion completa, no una frase corta.
10. Justifica cada conclusion con argumentos tecnicos solidos.

Responde SOLO con el JSON valido, sin texto adicional.
"""
    
    try:
        with st.spinner("🤖 Analizando con IA Gemini... Esto puede tomar 20-30 segundos..."):
            response = model.generate_content(prompt)
            texto_respuesta = response.text
            
            # Extraer JSON de la respuesta
            inicio = texto_respuesta.find('{')
            fin = texto_respuesta.rfind('}')
            if inicio != -1 and fin != -1:
                json_str = texto_respuesta[inicio:fin+1]
                datos = json.loads(json_str)
                return datos
            else:
                st.error("La IA no devolvio un formato JSON valido.")
                return None
    except Exception as e:
        st.error(f"Error al generar con IA: {e}")
        return None

def humanizar_texto_ia(texto_original, tipo_campo="general"):
    """Mejora y humaniza un texto usando Gemini AI."""
    model = get_gemini_client()
    if model is None or not texto_original:
        return texto_original
    
    prompt = f"""
Eres un ingeniero senior en mecatronica industrial. Mejora y profesionaliza el siguiente texto
para un documento ACR/AFA de alta calidad. El texto debe sonar natural, humano, pero con 
terminologia tecnica precisa y profesional.

TIPO DE CAMPO: {tipo_campo}
TEXTO ORIGINAL:
{texto_original}

INSTRUCCIONES:
1. Manten el significado original pero mejora la redaccion profesional.
2. Usa terminologia de ingenieria mecatronica y mantenimiento industrial.
3. El texto debe fluir como escrito por un experto humano, no una IA.
4. Incluye detalles tecnicos relevantes si el campo lo permite.
5. Corrige cualquier error gramatical u ortografico.
6. Responde SOLO con el texto mejorado, sin explicaciones adicionales.
"""
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return texto_original

# ==============================================================================
# FUNCIONES DE HISTORICO Y ARCHIVO
# ==============================================================================
def archivar_documento(codigo):
    """Archiva un documento cerrado al historico para referencia futura."""
    doc = db_one("SELECT * FROM documentos WHERE codigo=?", (codigo,))
    if not doc:
        return False
    
    d = dict(doc)
    
    # Verificar si ya esta archivado
    existe = db_one("SELECT id FROM historico_documentos WHERE codigo=?", (codigo,))
    if existe:
        return True  # Ya archivado
    
    # Archivar documento principal
    db_run("""INSERT INTO historico_documentos 
        (tipo_documento, codigo, codigo_original, fecha_reporte, fecha_cierre,
         estado_final, reportado_por, area_equipo, desc_problema_inicial,
         problema_enfocado, causa_raiz_identificada, verificacion_causa,
         observaciones_cierre, prioridad, costo_estimado,
         impacto_produccion, impacto_seguridad, impacto_ambiental)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (d['tipo_documento'], d['codigo'], d['codigo'], d['fecha_reporte'],
         d['fecha_cierre'], d['estado'], d['reportado_por'], d['area_equipo'],
         d['desc_problema_inicial'], d['problema_enfocado'],
         d['causa_raiz_identificada'], d['verificacion_causa'],
         d['observaciones_cierre'], d['prioridad'], d['costo_estimado'],
         d['impacto_produccion'], d['impacto_seguridad'], d['impacto_ambiental']))
    
    # Archivar acciones inmediatas
    accs = db_query("SELECT * FROM acciones_inmediatas WHERE codigo_acr=?", (codigo,))
    for a in accs:
        db_run("""INSERT INTO historico_acciones
            (codigo_documento, tipo_accion, accion, responsable, fecha_limite,
             fecha_cierre, estado_final, eficacia)
            VALUES (?,?,?,?,?,?,?,?)""",
            (codigo, 'INMEDIATA', a['accion'], a['responsable'], a['fecha'],
             a['fecha_cierre'], a['estado'], a['eficacia']))
    
    # Archivar acciones Why-Why
    wws = db_query("SELECT * FROM why_why WHERE codigo_documento=?", (codigo,))
    for w in wws:
        db_run("""INSERT INTO historico_acciones
            (codigo_documento, tipo_accion, accion, responsable, fecha_limite,
             fecha_cierre, estado_final, eficacia)
            VALUES (?,?,?,?,?,?,?,?)""",
            (codigo, 'CAUSA_RAIZ', w['accion_causa_raiz'], w['responsable'],
             w['fecha'], None, w['estatus'], 'POR_VERIFICAR'))
    
    return True

def buscar_historico_por_area(area=None, equipo=None, palabra_clave=None):
    """Busca en el historico de documentos por criterios."""
    sql = "SELECT * FROM historico_documentos WHERE 1=1"
    params = []
    
    if area:
        sql += " AND area_equipo LIKE ?"
        params.append(f"%{area}%")
    if equipo:
        sql += " AND desc_problema_inicial LIKE ?"
        params.append(f"%{equipo}%")
    if palabra_clave:
        sql += " AND (desc_problema_inicial LIKE ? OR problema_enfocado LIKE ? OR causa_raiz_identificada LIKE ?)"
        params.extend([f"%{palabra_clave}%", f"%{palabra_clave}%", f"%{palabra_clave}%"])
    
    sql += " ORDER BY fecha_archivado DESC"
    return db_query(sql, tuple(params))

def detectar_repeticion(codigo_nuevo, area_equipo, desc_problema):
    """Detecta si un problema similar ya existe en el historico."""
    sql = """SELECT codigo, desc_problema_inicial, problema_enfocado, causa_raiz_identificada
             FROM historico_documentos 
             WHERE area_equipo LIKE ? 
             AND (desc_problema_inicial LIKE ? OR problema_enfocado LIKE ?)
             ORDER BY fecha_archivado DESC LIMIT 5"""
    params = (f"%{area_equipo}%", f"%{desc_problema[:50]}%", f"%{desc_problema[:50]}%")
    return db_query(sql, params)

def registrar_repeticion(codigo_original, codigo_repeticion, area_equipo, notas=""):
    """Registra una repeticion de problema para seguimiento."""
    db_run("""INSERT INTO repeticiones_problemas 
        (codigo_original, codigo_repeticion, area_equipo, desc_similaridad, notas)
        VALUES (?,?,?,?,?)""",
        (codigo_original, codigo_repeticion, area_equipo, 
         "Problema similar detectado en el mismo area/equipo", notas))

# ==============================================================================
# PDF EXPORTER (portrait + landscape inteligente)
# ==============================================================================
def _colores():
    return {
        'azul':       rl_colors.HexColor('#1e3a5f'),
        'azul_claro': rl_colors.HexColor('#2a5a8c'),
        'azul_sec':   rl_colors.HexColor('#1e60a8'),
        'gris':       rl_colors.HexColor('#6c757d'),
        'gris_claro': rl_colors.HexColor('#f8f9fa'),
        'borde':      rl_colors.HexColor('#adb5bd'),
        'blanco':     rl_colors.HexColor('#ffffff'),
        'rojo_exsa':  rl_colors.HexColor('#cc2222'),
    }

def _estilos_pdf():
    base = getSampleStyleSheet()
    C = _colores()
    return {
        'celda': ParagraphStyle('C', parent=base['Normal'], fontSize=8, leading=10, fontName='Helvetica'),
        'celda_b': ParagraphStyle('CB', parent=base['Normal'], fontSize=8, leading=10, fontName='Helvetica-Bold'),
        'header': ParagraphStyle('H', parent=base['Normal'], fontSize=8, leading=10,
                                 fontName='Helvetica-Bold', textColor=C['blanco'], alignment=TA_CENTER),
        'seccion': ParagraphStyle('S', parent=base['Normal'], fontSize=9, leading=11,
                                  fontName='Helvetica-Bold', textColor=C['blanco']),
        'normal': ParagraphStyle('N', parent=base['Normal'], fontSize=8, leading=11, fontName='Helvetica'),
        'pie': ParagraphStyle('P', parent=base['Normal'], fontSize=7, leading=9,
                              textColor=C['gris'], fontName='Helvetica-Oblique', alignment=TA_CENTER),
        'flecha': ParagraphStyle('FL', parent=base['Normal'], fontSize=11,
                                 fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=C['blanco']),
    }

def _sec_header(texto, estilos, aw):
    C = _colores()
    data = [[Paragraph(f'<b>{texto}</b>', estilos['seccion'])]]
    t = Table(data, colWidths=[aw])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), C['azul_sec']),
        ('BOX', (0,0),(-1,-1), 0.5, C['azul']),
        ('LEFTPADDING', (0,0),(-1,-1), 6),
        ('TOPPADDING', (0,0),(-1,-1), 4),
        ('BOTTOMPADDING', (0,0),(-1,-1), 4),
    ]))
    return t

def _celda_texto(texto, estilos, aw):
    C = _colores()
    data = [[Paragraph(texto or ' ', estilos['normal'])]]
    t = Table(data, colWidths=[aw])
    t.setStyle(TableStyle([
        ('BOX', (0,0),(-1,-1), 0.5, C['borde']),
        ('LEFTPADDING', (0,0),(-1,-1), 5),
        ('RIGHTPADDING', (0,0),(-1,-1), 5),
        ('TOPPADDING', (0,0),(-1,-1), 4),
        ('BOTTOMPADDING', (0,0),(-1,-1), 4),
        ('VALIGN', (0,0),(-1,-1), 'TOP'),
    ]))
    return t

def _hdr_inst(codigo_form, edicion, tipo_doc, codigo, estilos, aw, cfg):
    C = _colores()
    logo_blob = cfg.get('logo_blob')
    texto_enc = cfg.get('texto_encabezado') or 'SISTEMA DE GESTION DE MANTENIMIENTO'
    nombre    = cfg.get('nombre_empresa') or 'EMPRESA INDUSTRIAL S.A.'

    if logo_blob:
        try:
            buf = io.BytesIO(logo_blob)
            logo_cell = RLImage(buf, width=28*mm, height=14*mm, kind='proportional')
        except Exception:
            logo_cell = Paragraph(f'<b>{nombre}</b>',
                ParagraphStyle('LT', parent=estilos['celda'], alignment=TA_CENTER, fontSize=8))
    else:
        logo_cell = Paragraph(
            '<font size="14" color="#e76f51"><b>O</b></font>'
            '<font size="14" color="#1e3a5f"><b>RICA</b></font>',
            ParagraphStyle('LC', parent=estilos['celda'], alignment=TA_CENTER, fontSize=14))

    centro = []
    for linea in texto_enc.split('\n'):
        if linea.strip():
            centro.append(Paragraph(f'<b>{linea.strip()}</b>',
                ParagraphStyle('CH', parent=estilos['celda'], alignment=TA_CENTER, fontSize=8)))
    centro.append(Paragraph(f'<b>{tipo_doc}</b>',
        ParagraphStyle('CS', parent=estilos['celda'], alignment=TA_CENTER,
                       fontSize=10, textColor=C['azul'])))

    der = [
        Paragraph('<b>Valido desde: 24/04/2026</b>',
            ParagraphStyle('D1', parent=estilos['celda'], fontSize=7)),
        Paragraph(f'<b>{codigo_form}</b>',
            ParagraphStyle('D2', parent=estilos['celda'], fontSize=8, alignment=TA_RIGHT)),
        Paragraph('Prox. revision: 24/04/2029',
            ParagraphStyle('D3', parent=estilos['celda'], fontSize=7)),
        Paragraph(f'<b>{edicion}</b>',
            ParagraphStyle('D4', parent=estilos['celda'], fontSize=8,
                           alignment=TA_RIGHT, textColor=C['rojo_exsa'])),
    ]

    t = Table([[logo_cell, centro, der]], colWidths=[30*mm, aw-70*mm, 40*mm])
    t.setStyle(TableStyle([
        ('BOX', (0,0),(-1,-1), 1.2, C['azul']),
        ('INNERGRID', (0,0),(-1,-1), 0.5, C['borde']),
        ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0),(-1,-1), 4),
        ('RIGHTPADDING', (0,0),(-1,-1), 4),
        ('TOPPADDING', (0,0),(-1,-1), 4),
        ('BOTTOMPADDING', (0,0),(-1,-1), 4),
    ]))
    return t

def exportar_pdf(codigo, es_acr):
    C = _colores()
    E = _estilos_pdf()
    cfg = get_empresa_cfg()
    nombre_empresa = cfg.get('nombre_empresa') or 'EMPRESA INDUSTRIAL S.A.'
    texto_pie = cfg.get('texto_pie_pagina') or \
        'Documento Controlado | Normativa: ISO 9001 / ISO 14224 / TPM / RCM'
    codigo_form = "MAN-F-054" if es_acr else "MAN-F-053"
    edicion = "EDICION:02"
    tipo_doc_label = "ANALISIS DE CAUSA RAIZ - ACR" if es_acr else "ANALISIS DE FALLAS - AFA"

    A4_PORT = A4
    A4_LAND = rl_landscape(A4)
    M = 15 * mm
    AW_PORT = A4_PORT[0] - 2*M
    AW_LAND = A4_LAND[0] - 2*M

    buf_pdf = io.BytesIO()

    fr_port = Frame(M, M, AW_PORT, A4_PORT[1]-2*M, id='portrait_frame')
    fr_land = Frame(M, M, AW_LAND, A4_LAND[1]-2*M, id='landscape_frame')

    def _pie(canvas_obj, doc_obj, page_w):
        canvas_obj.saveState()
        canvas_obj.setFont('Helvetica', 7)
        canvas_obj.setFillColor(C['gris'])
        canvas_obj.drawCentredString(page_w/2, M-6*mm,
            f'Pagina {doc_obj.page}  |  {codigo}  |  {tipo_doc_label}')
        canvas_obj.restoreState()

    tpl_p = PageTemplate(id='portrait',  frames=[fr_port], pagesize=A4_PORT,
                         onPage=lambda c,d: _pie(c,d, A4_PORT[0]))
    tpl_l = PageTemplate(id='landscape', frames=[fr_land], pagesize=A4_LAND,
                         onPage=lambda c,d: _pie(c,d, A4_LAND[0]))

    doc = BaseDocTemplate(buf_pdf, pageTemplates=[tpl_p, tpl_l], pagesize=A4_PORT)

    def HDR(aw): return _hdr_inst(codigo_form, edicion, tipo_doc_label, codigo, E, aw, cfg)
    def SEC(txt, aw=AW_PORT): return _sec_header(txt, E, aw)
    def TXT(txt, aw=AW_PORT): return _celda_texto(txt, E, aw)

    # Datos
    d = dict(db_one("SELECT * FROM documentos WHERE codigo=?", (codigo,)) or {})
    EL = []

    # ── RETRATO ───────────────────────────────────────────────────────────────
    EL.append(NextPageTemplate('portrait'))
    EL.extend([HDR(AW_PORT), Spacer(1,6)])

    # 1. Participantes
    EL.append(SEC("1.- Participantes"))
    tp = Table([
        [Paragraph('<b>Lider del AFA:</b>', E['celda']), Paragraph(d.get('lider_afa') or '', E['celda']),
         Paragraph('<b>Fecha inicio:</b>', E['celda']),   Paragraph(d.get('fecha_inicio_analisis') or '', E['celda']),
         Paragraph('<b>Responsables:</b>', E['celda']),   Paragraph(d.get('responsables') or '', E['celda'])],
        [Paragraph('<b>Area (equipo):</b>', E['celda']),  Paragraph(d.get('area_equipo') or '', E['celda']),
         Paragraph('<b>Codigo:</b>', E['celda']),          Paragraph(codigo, E['celda']),
         Paragraph('<b>Estado:</b>', E['celda']),           Paragraph(d.get('estado') or '', E['celda'])],
    ], colWidths=[32*mm,38*mm,32*mm,32*mm,22*mm,24*mm])
    tp.setStyle(TableStyle([
        ('BOX',(0,0),(-1,-1),0.8,C['azul']),('INNERGRID',(0,0),(-1,-1),0.3,C['borde']),
        ('BACKGROUND',(0,0),(0,-1),C['gris_claro']),('BACKGROUND',(2,0),(2,-1),C['gris_claro']),
        ('BACKGROUND',(4,0),(4,-1),C['gris_claro']),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
    ]))
    EL.extend([tp, Spacer(1,4)])

    # 2. Descripcion problema
    EL.append(SEC("2.- Descripcion del problema inicial"))
    EL.extend([TXT(d.get('desc_problema_inicial') or ''), Spacer(1,4)])

    # 3. Que? Contexto
    EL.append(SEC("3.- Que? (Que es lo que vio o paso?) Contexto"))
    EL.extend([TXT(d.get('que_contexto') or ''), Spacer(1,4)])

    # 4. Como ocurre
    EL.append(SEC("4.- Entienda como ocurre el problema (alcance)"))
    EL.extend([TXT(d.get('como_ocurre') or ''), Spacer(1,4)])

    # 5. 5W+2H
    EL.append(SEC("5.- Enfoque el problema — 5W + 2H"))
    t5w = Table([
        [Paragraph('<b>Quien?</b> Origino/Detecto el problema', E['celda']),
         Paragraph(d.get('quien') or '', E['normal']),
         Paragraph('<b>Donde?</b> Punto exacto donde nace el problema', E['celda']),
         Paragraph(d.get('donde') or '', E['normal'])],
        [Paragraph('<b>Cuanto?</b> Frecuencia, extension del dano', E['celda']),
         Paragraph(d.get('cuanto') or '', E['normal']),
         Paragraph('<b>Cuando?</b> Cuando inicio el problema', E['celda']),
         Paragraph(d.get('cuando') or '', E['normal'])],
    ], colWidths=[38*mm,52*mm,38*mm,52*mm])
    t5w.setStyle(TableStyle([
        ('BOX',(0,0),(-1,-1),0.8,C['azul']),('INNERGRID',(0,0),(-1,-1),0.3,C['borde']),
        ('BACKGROUND',(0,0),(0,-1),C['gris_claro']),('BACKGROUND',(2,0),(2,-1),C['gris_claro']),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
    ]))
    EL.append(t5w)
    tcual = Table([[Paragraph('<b>Cual?</b> Marcas, formatos, producto, materiales', E['celda']),
                   Paragraph(d.get('cual') or '', E['normal'])]], colWidths=[70*mm,110*mm])
    tcual.setStyle(TableStyle([
        ('BOX',(0,0),(-1,-1),0.8,C['azul']),('INNERGRID',(0,0),(-1,-1),0.3,C['borde']),
        ('BACKGROUND',(0,0),(0,-1),C['gris_claro']),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
    ]))
    EL.extend([tcual, Spacer(1,4)])

    # 6. Descripcion enfocada
    EL.append(SEC("6.- Descripcion del problema enfocado (5W+2H)"))
    EL.extend([TXT(d.get('problema_enfocado') or ''), Spacer(1,4)])

    # 7. Acciones inmediatas
    EL.append(SEC("7.- Acciones Inmediatas (Correccion / Contencion)"))
    accs = db_query("SELECT * FROM acciones_inmediatas WHERE codigo_acr=?", (codigo,))
    hdr_a = [[Paragraph(f'<b>{t}</b>', E['header']) for t in ['Accion','Responsable','Fecha','Estado','Eficacia']]]
    rows_a = [[Paragraph(r['accion'] or '', E['celda']), Paragraph(r['responsable'] or '', E['celda']),
               Paragraph(r['fecha'] or '', E['celda']),  Paragraph(r['estado'] or '', E['celda']),
               Paragraph(r['eficacia'] or '', E['celda'])] for r in accs] or \
             [[Paragraph('',E['celda'])]*5]
    ta = Table(hdr_a + rows_a, colWidths=[90*mm,40*mm,22*mm,18*mm,20*mm])
    ta.setStyle(TableStyle([
        ('BOX',(0,0),(-1,-1),0.8,C['azul']),('INNERGRID',(0,0),(-1,-1),0.3,C['borde']),
        ('BACKGROUND',(0,0),(-1,0),C['azul']),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[C['blanco'],C['gris_claro']]),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
    ]))
    EL.extend([ta, Spacer(1,4)])

    # 8. Condiciones 6M (solo ACR)
    if es_acr:
        EL.extend([PageBreak(), HDR(AW_PORT), Spacer(1,4)])
        EL.append(SEC("8.- Revision de condiciones basicas (6M)"))
        conds = db_query("SELECT * FROM condiciones_basicas WHERE codigo_acr=? ORDER BY categoria_6m,item", (codigo,))
        hdr_c = [[Paragraph(f'<b>{t}</b>', E['header'])
                  for t in ['6M','Condicion','Cond. Ideal','Cond. Actual (Hallazgo)','Aplica','Diferencia']]]
        rows_c = [[Paragraph(r['categoria_6m'] or '', E['celda']), Paragraph(r['item'] or '', E['celda']),
                   Paragraph(r['condicion_ideal'] or '', E['celda']), Paragraph(r['condicion_actual'] or '', E['celda']),
                   Paragraph(r['aplica'] or '', E['celda']), Paragraph(r['diferencia'] or '', E['celda'])]
                  for r in conds] or [[Paragraph('',E['celda'])]*6]
        tc = Table(hdr_c+rows_c, colWidths=[25*mm,28*mm,48*mm,48*mm,12*mm,19*mm])
        tc.setStyle(TableStyle([
            ('BOX',(0,0),(-1,-1),0.8,C['azul']),('INNERGRID',(0,0),(-1,-1),0.3,C['borde']),
            ('BACKGROUND',(0,0),(-1,0),C['azul']),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[C['blanco'],C['gris_claro']]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),3),
            ('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),('FONTSIZE',(0,0),(-1,-1),7),
        ]))
        EL.extend([tc, Spacer(1,4)])

    # ── PAISAJE — Why-Why ─────────────────────────────────────────────────────
    num_ww = "9" if es_acr else "7"
    EL.extend([NextPageTemplate('landscape'), PageBreak()])
    EL.extend([HDR(AW_LAND), Spacer(1,4)])
    EL.append(SEC(f"{num_ww}.- Analisis Why Why (WW)", AW_LAND))

    whys = db_query("SELECT * FROM why_why WHERE codigo_documento=? ORDER BY CAST(rama_id AS INTEGER)", (codigo,))
    col_prio = {'BAJA':rl_colors.HexColor('#d1f2eb'),'MEDIA':rl_colors.HexColor('#fef9c3'),
                'ALTA':rl_colors.HexColor('#fde8c8'),'CRITICA':rl_colors.HexColor('#fcd0d0')}
    est_fl = ParagraphStyle('FL',parent=getSampleStyleSheet()['Normal'],
                            fontSize=11,fontName='Helvetica-Bold',alignment=TA_CENTER,
                            textColor=rl_colors.HexColor('#1e60a8'))
    est_nm = ParagraphStyle('NM',parent=getSampleStyleSheet()['Normal'],
                            fontSize=8,alignment=TA_CENTER,textColor=C['blanco'])

    cols_ww = ['N','Definicion','>','Por que 1?','>','Por que 2?','>','Por que 3?',
               '>','Por que 4?','>','Por que 5?','>','Causa Raiz','Accion','Responsable','Prioridad','Fecha']
    hdr_ww = [[Paragraph(f'<b>{t}</b>', est_fl if t=='>' else E['header']) for t in cols_ww]]
    sty_ww = TableStyle([
        ('BOX',(0,0),(-1,-1),0.8,C['azul']),('INNERGRID',(0,0),(-1,-1),0.3,C['borde']),
        ('BACKGROUND',(0,0),(-1,0),C['azul']),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),2),('RIGHTPADDING',(0,0),(-1,-1),2),
        ('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),
        ('FONTSIZE',(0,0),(-1,-1),7),('ALIGN',(0,0),(0,-1),'CENTER'),
    ])
    for fc in [2,4,6,8,10,12]:
        sty_ww.add('BACKGROUND',(fc,1),(fc,-1),C['azul_claro'])
        sty_ww.add('ALIGN',(fc,0),(fc,-1),'CENTER')

    for i, w in enumerate(whys, 1):
        prio = (w['prioridad'] or 'MEDIA').upper()
        fila = [
            Paragraph(str(i), est_nm),
            Paragraph(w['definicion'] or '', E['celda']),
            Paragraph('>', est_fl),
            Paragraph(w['pq1'] or '', E['celda']),
            Paragraph('>', est_fl),
            Paragraph(w['pq2'] or '', E['celda']),
            Paragraph('>', est_fl),
            Paragraph(w['pq3'] or '', E['celda']),
            Paragraph('>', est_fl),
            Paragraph(w['pq4'] or '', E['celda']),
            Paragraph('>', est_fl),
            Paragraph(w['pq5'] or '', E['celda']),
            Paragraph('>', est_fl),
            Paragraph(w['causa_raiz'] or '', E['celda']),
            Paragraph(w['accion_causa_raiz'] or '', E['celda']),
            Paragraph(w['responsable'] or '', E['celda']),
            Paragraph(prio, ParagraphStyle('Pr',parent=E['celda'],
                backColor=col_prio.get(prio,C['blanco']),alignment=TA_CENTER,fontSize=7)),
            Paragraph(w['fecha'] or '', E['celda']),
        ]
        hdr_ww.append(fila)
        bg = C['blanco'] if i%2==1 else C['gris_claro']
        for ci in [0,1,3,5,7,9,11,13,14,15,16,17]:
            sty_ww.add('BACKGROUND',(ci,i),(ci,i),bg)

    if not whys:
        hdr_ww.append([Paragraph('',E['celda'])]*18)

    tww = Table(hdr_ww,
        colWidths=[8*mm,27*mm,5*mm,22*mm,5*mm,22*mm,5*mm,
                   20*mm,5*mm,20*mm,5*mm,20*mm,5*mm,
                   25*mm,25*mm,22*mm,14*mm,14*mm],
        repeatRows=1)
    tww.setStyle(sty_ww)
    EL.extend([tww, Spacer(1,4)])

    # ── RETRATO — Cierre y Anexos ────────────────────────────────────────────
    EL.extend([NextPageTemplate('portrait'), PageBreak()])
    EL.extend([HDR(AW_PORT), Spacer(1,4)])
    num_cierre = "10" if es_acr else "8"
    EL.append(SEC(f"{num_cierre}.- Cierre y Verificacion"))
    datos_c = [
        [Paragraph('<b>Causa Raiz Identificada:</b>', E['celda']),
         Paragraph(d.get('causa_raiz_identificada') or '', E['normal'])],
        [Paragraph('<b>Verificacion de la Causa:</b>', E['celda']),
         Paragraph(d.get('verificacion_causa') or '', E['normal'])],
        [Paragraph('<b>Evidencia de Causa:</b>', E['celda']),
         Paragraph(d.get('evidencia_causa') or '', E['normal'])],
        [Paragraph('<b>Observaciones de Cierre:</b>', E['celda']),
         Paragraph(d.get('observaciones_cierre') or '', E['normal'])],
    ]
    tci = Table(datos_c, colWidths=[45*mm,135*mm])
    tci.setStyle(TableStyle([
        ('BOX',(0,0),(-1,-1),0.8,C['azul']),('INNERGRID',(0,0),(-1,-1),0.3,C['borde']),
        ('BACKGROUND',(0,0),(0,-1),C['gris_claro']),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
    ]))
    EL.extend([tci, Spacer(1,4)])

    # Anexos (imagenes)
    evis = db_query("SELECT * FROM evidencias WHERE codigo_documento=? ORDER BY fecha_registro", (codigo,))
    if evis:
        num_anx = "11" if es_acr else "9"
        EL.extend([PageBreak(), HDR(AW_PORT), Spacer(1,4)])
        EL.append(SEC(f"{num_anx}.- Anexos (Evidencias fotograficas)"))
        for i, evi in enumerate(evis, 1):
            img_b = evi['imagen_blob']
            desc = evi['descripcion'] or evi['nombre_archivo'] or f"Imagen {i}"
            tipo_e = evi['tipo_evidencia'] or ''
            fmt = (evi['formato'] or '.jpg').lower()
            cap = Paragraph(f'<b>Figura {i}.</b> [{tipo_e}] {desc}',
                ParagraphStyle('Cap', parent=E['celda'], fontSize=8,
                               alignment=TA_CENTER, spaceBefore=2, spaceAfter=4))
            if img_b and fmt in ['.jpg','.jpeg','.png','.bmp','.gif','.tiff']:
                try:
                    buf = io.BytesIO(img_b)
                    img_rl = RLImage(buf, width=140*mm, height=90*mm, kind='proportional')
                    ti = Table([[img_rl]], colWidths=[AW_PORT])
                    ti.setStyle(TableStyle([
                        ('ALIGN',(0,0),(-1,-1),'CENTER'),
                        ('BOX',(0,0),(-1,-1),0.5,C['borde']),
                        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
                    ]))
                    EL.extend([ti, cap])
                except Exception:
                    EL.append(Paragraph(f'Figura {i}. {desc} (imagen no disponible)', E['normal']))
            EL.append(Spacer(1,6))

    # Footer
    EL.extend([Spacer(1,10),
               HRFlowable(width="100%", thickness=0.8, color=C['gris']),
               Paragraph(f'<i>{nombre_empresa} | {texto_pie}</i>', E['pie'])])

    doc.build(EL)
    buf_pdf.seek(0)
    return buf_pdf.getvalue()

# ==============================================================================
# COMPONENTES DE UI REUTILIZABLES
# ==============================================================================
def show_header(nombre_empresa="SISTEMA ACR / AFA"):
    cfg = get_empresa_cfg()
    logo_b = cfg.get('logo_blob')
    nombre = cfg.get('nombre_empresa') or nombre_empresa

    col_logo, col_titulo = st.columns([1, 6])
    with col_logo:
        if logo_b:
            try:
                img = Image.open(io.BytesIO(logo_b))
                st.image(img, width=120)
            except Exception:
                st.write("🏭")
        else:
            st.markdown("### 🔧")
    with col_titulo:
        st.markdown(f"""
        <div style="padding:10px 0">
            <div style="font-size:1.5rem;font-weight:700;color:#1e3a5f">{nombre}</div>
            <div style="font-size:.9rem;color:#2a5a8c">
                Sistema de Gestion Documental — ACR / AFA | ISO 9001 · ISO 14224 · TPM · RCM
            </div>
        </div>""", unsafe_allow_html=True)
    st.markdown("---")

def estado_color(estado):
    m = {'BORRADOR':'🔘','EN_ANALISIS':'🔵','REVISADO':'🟡',
         'APROBADO':'🟢','CERRADO':'⚫','RECHAZADO':'🔴'}
    return m.get(estado, '⚪')
