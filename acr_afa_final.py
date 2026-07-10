#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SISTEMA INSTITUCIONAL DE GESTION DOCUMENTAL ACR / AFA — STREAMLIT WEB
Analisis de Causa Raiz (ACR) y Analisis de Fallas y Acciones (AFA)
Version: 13.0.0 | Normativa: ISO 9001, ISO 14224, TPM, RCM
================================================================================
NUEVAS FUNCIONALIDADES v13.0.0:
- Motor IA Gemini v3.x con fallback automatico a modelos gratuitos
- Manejo inteligente de errores 429 RESOURCE_EXHAUSTED con retry y backoff
- Soporte multimodal nativo con google.genai.types.Part
- Deteccion automatica de modelos disponibles en free tier
- Prompt de sistema optimizado para experto en ACR/AFA industrial
- Cadena de fallback: 3.5 Flash → 3.1 Flash-Lite → 2.5 Flash → 2.5 Flash-Lite
"""

import streamlit as st
import sqlite3
import io
import os
import datetime
import base64
import tempfile
import uuid
import json
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

# ── IA Gemini ─────────────────────────────────────────────────────────────────
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    types = None

# ── Correccion ortografica ────────────────────────────────────────────────────
try:
    import language_tool_python
    LANG_TOOL_AVAILABLE = True
except ImportError:
    LANG_TOOL_AVAILABLE = False

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
# ESTILOS GLOBALES
# ==============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a2f4a 0%, #1e3a5f 60%, #162d47 100%) !important;
    border-right: 3px solid #1e60a8;
}
[data-testid="stSidebar"] * { color: #e8edf2 !important; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    color: #e8edf2 !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    transition: all .2s !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(30,96,168,0.6) !important;
    border-color: #4a90d9 !important;
    color: white !important;
}
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15) !important; }

.inst-header-main {
    background: linear-gradient(135deg, #1e3a5f 0%, #1e60a8 100%);
    color: white; padding: 18px 28px; border-radius: 10px;
    margin-bottom: 20px; border-left: 5px solid #4a90d9;
    box-shadow: 0 4px 16px rgba(30,58,95,.2);
}
.inst-title  { font-size: 1.5rem; font-weight: 700; letter-spacing: .4px; margin: 0; }
.inst-sub    { font-size: .82rem; opacity: .82; margin-top: 4px; }

.seccion-band {
    background: linear-gradient(90deg, #1e60a8 0%, #2a7fd4 100%);
    color: white !important; font-weight: 600;
    padding: 8px 16px; border-radius: 6px;
    margin: 16px 0 8px 0; font-size: .92rem;
    letter-spacing: .3px; border-left: 4px solid #ffc107;
    box-shadow: 0 2px 6px rgba(30,96,168,.25);
}
.seccion-cat {
    background: #1e3a5f; color: white !important; font-weight: 700;
    padding: 8px 14px; border-radius: 6px; margin: 12px 0 6px 0;
    font-size: .9rem; display: flex; align-items: center; gap: 8px;
}

[data-testid="metric-container"] {
    background: white; border: 1px solid #dee2e6;
    border-radius: 10px; padding: 16px 20px;
    box-shadow: 0 2px 8px rgba(30,58,95,.08);
    border-top: 3px solid #1e60a8;
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    font-size: .82rem !important; color: #6c757d !important; font-weight: 600 !important;
    text-transform: uppercase; letter-spacing: .5px;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 2rem !important; font-weight: 700 !important; color: #1e3a5f !important;
}

div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1e60a8, #1a4f8a) !important;
    color: white !important; border: none !important;
    border-radius: 7px !important; font-weight: 600 !important;
    padding: 8px 20px !important; letter-spacing: .3px;
    box-shadow: 0 3px 10px rgba(30,96,168,.35) !important;
    transition: all .2s !important;
}
div.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #1a4f8a, #163d6e) !important;
    box-shadow: 0 5px 16px rgba(30,96,168,.45) !important;
    transform: translateY(-1px);
}
div.stButton > button[kind="secondary"] {
    border: 1.5px solid #1e60a8 !important; color: #1e60a8 !important;
    border-radius: 7px !important; font-weight: 500 !important;
    background: white !important;
}
div.stButton > button[kind="secondary"]:hover {
    background: #f0f6ff !important;
}

.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
    border: 1.5px solid #ced4da !important;
    border-radius: 7px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: .9rem !important;
    transition: border-color .15s !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #1e60a8 !important;
    box-shadow: 0 0 0 3px rgba(30,96,168,.12) !important;
}

.stTextInput label, .stTextArea label, .stSelectbox label,
.stRadio label, .stDateInput label, .stNumberInput label {
    font-weight: 600 !important; color: #2c3e50 !important;
    font-size: .85rem !important; letter-spacing: .2px;
}

.stTabs [data-baseweb="tab-list"] {
    background: #f0f4f8; border-radius: 10px 10px 0 0;
    border-bottom: 2px solid #1e60a8; gap: 2px; padding: 4px 4px 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important; border-radius: 8px 8px 0 0 !important;
    color: #4a5568 !important; font-weight: 600 !important;
    font-size: .88rem !important; padding: 8px 16px !important;
    border: none !important; transition: all .15s !important;
}
.stTabs [aria-selected="true"] {
    background: #1e60a8 !important; color: white !important;
    box-shadow: 0 -2px 8px rgba(30,96,168,.2) !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: white; border: 1px solid #e2e8f0;
    border-top: none; border-radius: 0 0 10px 10px;
    padding: 20px !important;
}

[data-testid="stExpander"] {
    border: 1px solid #e2e8f0 !important; border-radius: 8px !important;
    margin-bottom: 6px !important; overflow: hidden;
}
[data-testid="stExpander"] summary {
    background: #f8fafc !important; border-radius: 8px !important;
    font-weight: 600 !important; color: #1e3a5f !important;
    padding: 10px 14px !important; font-size: .88rem !important;
}
[data-testid="stExpander"] summary:hover {
    background: #eef3fa !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid #dee2e6 !important; border-radius: 8px;
    overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.06);
}

[data-testid="stAlert"] {
    border-radius: 8px !important; border-left-width: 4px !important;
    font-weight: 500 !important;
}

.badge-estado {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: .76rem; font-weight: 700; letter-spacing: .4px;
    text-transform: uppercase;
}
.badge-BORRADOR     { background:#e9ecef; color:#495057; }
.badge-EN_ANALISIS  { background:#cfe2ff; color:#084298; }
.badge-REVISADO     { background:#fff3cd; color:#664d03; }
.badge-APROBADO     { background:#d1e7dd; color:#0a3622; }
.badge-CERRADO      { background:#d3d3d3; color:#212529; }
.badge-RECHAZADO    { background:#f8d7da; color:#842029; }

.prio-chip {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: .76rem; font-weight: 700;
}
.prio-BAJA    { background:#d1f2eb; color:#0e6655; }
.prio-MEDIA   { background:#fef9c3; color:#7d6608; }
.prio-ALTA    { background:#fde8c8; color:#9c4221; }
.prio-CRITICA { background:#fcd0d0; color:#7b1818; border: 1px solid #e74c3c; }

.kpi-card {
    background: white; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 18px 22px; text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,.06);
    transition: transform .2s, box-shadow .2s;
}
.kpi-card:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,.1); }
.kpi-num  { font-size: 2.4rem; font-weight: 800; line-height: 1.1; margin: 4px 0; }
.kpi-label { font-size: .78rem; color: #6c757d; font-weight: 600;
              text-transform: uppercase; letter-spacing: .5px; }
.kpi-pend  { color: #dc3545; border-top: 4px solid #dc3545; }
.kpi-proc  { color: #fd7e14; border-top: 4px solid #fd7e14; }
.kpi-cerr  { color: #198754; border-top: 4px solid #198754; }
.kpi-venc  { color: #6f42c1; border-top: 4px solid #6f42c1; }
.kpi-total { color: #1e60a8; border-top: 4px solid #1e60a8; }

[data-testid="stForm"] {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 16px 20px !important;
}

hr { border: none; border-top: 1px solid #e9ecef; margin: 16px 0; }

[data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, #1e60a8, #4a90d9) !important;
    border-radius: 4px !important;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f1f1f1; }
::-webkit-scrollbar-thumb { background: #adb5bd; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #1e60a8; }

.ia-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: linear-gradient(135deg, #1e60a8, #2a7fd4);
    color: white; padding: 6px 14px; border-radius: 20px;
    font-size: .82rem; font-weight: 600; margin-bottom: 8px;
}
.ia-badge::before { content: "🤖"; }

.ia-context-box {
    background: linear-gradient(135deg, #f0f6ff 0%, #e8f0fe 100%);
    border: 2px solid #1e60a8; border-radius: 10px;
    padding: 16px; margin: 12px 0;
}

.ia-generated-field {
    background: #f8fafc; border-left: 4px solid #10b981;
    padding: 12px 16px; border-radius: 0 8px 8px 0;
    margin: 8px 0;
}

.humanize-badge {
    display: inline-flex; align-items: center; gap: 4px;
    background: #fef3c7; color: #92400e;
    padding: 3px 10px; border-radius: 12px;
    font-size: .72rem; font-weight: 600;
}

/* Nuevos estilos para estado de conexion IA */
.ia-status-ok {
    background: linear-gradient(135deg, #d1f2eb, #a9dfbf);
    border: 1px solid #27ae60;
    color: #0e6655;
    padding: 8px 14px;
    border-radius: 8px;
    font-weight: 600;
    font-size: .85rem;
}
.ia-status-warn {
    background: linear-gradient(135deg, #fef9c3, #fde8c8);
    border: 1px solid #f39c12;
    color: #7d6608;
    padding: 8px 14px;
    border-radius: 8px;
    font-weight: 600;
    font-size: .85rem;
}
.ia-status-err {
    background: linear-gradient(135deg, #f8d7da, #f5b7b1);
    border: 1px solid #e74c3c;
    color: #842029;
    padding: 8px 14px;
    border-radius: 8px;
    font-weight: 600;
    font-size: .85rem;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# BASE DE DATOS
# ==============================================================================
DB_PATH = "acr_afa_system.db"

@st.cache_resource
def get_db():
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
            ultima_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            es_historico INTEGER DEFAULT 0,
            fecha_archivado TEXT,
            motivo_reapertura TEXT,
            documento_padre TEXT,
            version INTEGER DEFAULT 1
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
        """CREATE TABLE IF NOT EXISTS historico_documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_original TEXT NOT NULL,
            codigo_historico TEXT NOT NULL,
            tipo_documento TEXT NOT NULL,
            fecha_archivado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            motivo_archivado TEXT,
            estado_final TEXT,
            datos_json TEXT NOT NULL,
            acciones_completadas INTEGER DEFAULT 0,
            acciones_totales INTEGER DEFAULT 0,
            FOREIGN KEY (codigo_original) REFERENCES documentos(codigo) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS config_ia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT,
            modelo TEXT DEFAULT 'gemini-3.5-flash',
            temperatura REAL DEFAULT 0.3,
            max_tokens INTEGER DEFAULT 4096,
            idioma TEXT DEFAULT 'es',
            estilo_redaccion TEXT DEFAULT 'tecnico_profesional',
            nivel_detalle TEXT DEFAULT 'detallado',
            activar_correccion INTEGER DEFAULT 1,
            activar_humanizar INTEGER DEFAULT 1,
            prompt_personalizado TEXT,
            fallback_automatico INTEGER DEFAULT 1,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS seguimiento_acciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_documento TEXT NOT NULL,
            tipo_accion TEXT NOT NULL,
            id_accion INTEGER NOT NULL,
            fecha_seguimiento TEXT NOT NULL,
            estado TEXT NOT NULL,
            observaciones TEXT,
            responsable_seguimiento TEXT,
            evidencia_cumplimiento TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (codigo_documento) REFERENCES documentos(codigo) ON DELETE CASCADE
        )""",
    ]
    for s in stmts:
        try:
            conn.execute(s)
        except Exception:
            pass
    conn.commit()
    # Migracion: actualizar modelos antiguos a la nueva nomenclatura v3.x
    try:
        cur = conn.execute("SELECT id, modelo FROM config_ia")
        for row in cur.fetchall():
            modelo_actual = row['modelo'].lower().strip() if row['modelo'] else ''
            modelo_nuevo = _mapear_modelo_a_v3(modelo_actual)
            if modelo_nuevo != modelo_actual:
                conn.execute("UPDATE config_ia SET modelo=? WHERE id=?", (modelo_nuevo, row['id']))
        conn.commit()
    except Exception:
        pass

def _mapear_modelo_a_v3(modelo):
    """Mapea cualquier nombre de modelo antiguo a la nomenclatura v3.x actual."""
    if not modelo:
        return 'gemini-3.5-flash'
    mapeo = {
        'gemini-3.5-flash': 'gemini-3.5-flash',
        'gemini-3.1-flash-lite': 'gemini-3.1-flash-lite',
        'gemini-3.1-pro': 'gemini-3.1-pro',
        'gemini-3.1-flash': 'gemini-3.1-flash',
        'gemini-3.0-flash': 'gemini-3.5-flash',
        'gemini-3.0-pro': 'gemini-3.1-pro',
        'gemini-2.5-flash': 'gemini-3.5-flash',
        'gemini-2.5-flash-lite': 'gemini-3.1-flash-lite',
        'gemini-2.5-pro': 'gemini-3.1-pro',
        'gemini-2.0-flash': 'gemini-3.5-flash',
        'gemini-2.0-flash-lite': 'gemini-3.1-flash-lite',
        'gemini-2.0-pro': 'gemini-3.1-pro',
        'gemini-1.5-flash': 'gemini-3.5-flash',
        'gemini-1.5-pro': 'gemini-3.1-pro',
    }
    return mapeo.get(modelo, 'gemini-3.5-flash')

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
    row = db_one("SELECT * FROM configuracion_empresa LIMIT 1")
    return dict(row) if row else {}

def get_ia_cfg():
    row = db_one("SELECT * FROM config_ia LIMIT 1")
    if not row:
        return {}
    cfg = dict(row)
    # Asegurar modelo valido
    modelo = cfg.get('modelo', '')
    cfg['modelo'] = _mapear_modelo_a_v3(modelo)
    # Actualizar en BD si cambio
    if modelo != cfg['modelo']:
        db_run("UPDATE config_ia SET modelo=? WHERE id=?", (cfg['modelo'], cfg['id']))
    return cfg

def save_ia_cfg(cfg_dict):
    existing = db_one("SELECT id FROM config_ia LIMIT 1")
    if existing:
        db_run("""UPDATE config_ia SET
            api_key=?, modelo=?, temperatura=?, max_tokens=?,
            idioma=?, estilo_redaccion=?, nivel_detalle=?,
            activar_correccion=?, activar_humanizar=?, prompt_personalizado=?,
            fallback_automatico=?
            WHERE id=?""",
            (cfg_dict.get('api_key',''), cfg_dict.get('modelo','gemini-3.5-flash'),
             cfg_dict.get('temperatura',0.3), cfg_dict.get('max_tokens',4096),
             cfg_dict.get('idioma','es'), cfg_dict.get('estilo_redaccion','tecnico_profesional'),
             cfg_dict.get('nivel_detalle','detallado'),
             cfg_dict.get('activar_correccion',1), cfg_dict.get('activar_humanizar',1),
             cfg_dict.get('prompt_personalizado',''), cfg_dict.get('fallback_automatico',1),
             existing['id']))
    else:
        db_run("""INSERT INTO config_ia
            (api_key,modelo,temperatura,max_tokens,idioma,estilo_redaccion,
             nivel_detalle,activar_correccion,activar_humanizar,prompt_personalizado,fallback_automatico)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (cfg_dict.get('api_key',''), cfg_dict.get('modelo','gemini-3.5-flash'),
             cfg_dict.get('temperatura',0.3), cfg_dict.get('max_tokens',4096),
             cfg_dict.get('idioma','es'), cfg_dict.get('estilo_redaccion','tecnico_profesional'),
             cfg_dict.get('nivel_detalle','detallado'),
             cfg_dict.get('activar_correccion',1), cfg_dict.get('activar_humanizar',1),
             cfg_dict.get('prompt_personalizado',''), cfg_dict.get('fallback_automatico',1)))

print("Parte 1 generada correctamente")



# ==============================================================================
# MOTOR DE IA GEMINI v3.x CON FALLBACK AUTOMATICO
# ==============================================================================
class GeminiEngine:
    """
    Motor de IA para autocompletar campos ACR/AFA con Gemini.

    Caracteristicas:
    - Cadena de fallback automatico cuando un modelo agota cuota (429)
    - Retry con backoff exponencial para errores temporales
    - Deteccion inteligente de errores RESOURCE_EXHAUSTED
    - Soporte multimodal nativo con types.Part
    - Cooldown tracking para evitar requests a modelos bloqueados
    """

    # ==============================================================================
    # CADENA DE FALLBACK: Orden de prioridad de modelos
    # ==============================================================================
    # Modelos gratuitos (Free Tier) - Julio 2026
    # gemini-3.5-flash:     15 RPM, 1,500 RPD - Default, mas rapido
    # gemini-3.1-flash-lite: 30 RPM, 1,500 RPD - Alto throughput
    # gemini-2.5-flash:      Legacy, paid-only desde Abril 2026
    # gemini-2.5-flash-lite: Legacy, paid-only desde Abril 2026

    CADENA_FALLBACK = [
        'gemini-3.5-flash',      # PRIMARY: Default, free tier
        'gemini-3.1-flash-lite', # SECONDARY: Alto throughput, free tier
        'gemini-2.5-flash',      # TERTIARY: Legacy fallback
        'gemini-2.5-flash-lite', # FINAL: Legacy budget fallback
    ]

    # Modelos de pago (requieren billing habilitado)
    MODELOS_PAGO = [
        'gemini-3.1-pro',
        'gemini-3.1-pro-preview',
        'gemini-3.0-pro',
        'gemini-2.5-pro',
        'gemini-2.0-pro',
    ]

    # Todos los modelos validos soportados
    MODELOS_VALIDOS = CADENA_FALLBACK + MODELOS_PAGO

    def __init__(self, api_key=None, modelo='gemini-3.5-flash'):
        self.api_key = api_key
        self.modelo_preferido = self._validar_modelo(modelo)
        self.client = None
        self.cooldowns = {}  # model_name -> earliest_retry_time (epoch)
        self.ultimo_modelo_usado = None
        self.estado_conexion = "NO_INICIALIZADO"
        self.mensaje_estado = ""

        if api_key and GEMINI_AVAILABLE:
            try:
                os.environ['GEMINI_API_KEY'] = api_key
                os.environ['GOOGLE_API_KEY'] = api_key
                self.client = genai.Client()
                self.estado_conexion = "CONECTADO"
                self.mensaje_estado = "Conexion exitosa con Gemini API"
            except Exception as e:
                self.estado_conexion = "ERROR"
                self.mensaje_estado = "Error inicializando Gemini: " + str(e)
                st.error(self.mensaje_estado)

    def _validar_modelo(self, modelo):
        # Corrige automaticamente nombres de modelos invalidos a la nomenclatura v3.x
        if not modelo:
            return 'gemini-3.5-flash'
        modelo = modelo.strip().lower()
        if modelo in self.MODELOS_VALIDOS:
            return modelo
        return _mapear_modelo_a_v3(modelo)

    def is_ready(self):
        return self.client is not None and GEMINI_AVAILABLE

    def _esta_en_cooldown(self, modelo):
        # Verifica si un modelo esta en periodo de cooldown por rate limit
        if modelo in self.cooldowns:
            if time.time() < self.cooldowns[modelo]:
                return True
            else:
                del self.cooldowns[modelo]
        return False

    def _agregar_cooldown(self, modelo, segundos=60):
        # Agrega un modelo a cooldown despues de un error 429
        self.cooldowns[modelo] = time.time() + segundos

    def _detectar_formato_imagen(self, bytes_img):
        # Detecta el formato de imagen a partir de los bytes magicos
        if not bytes_img:
            return 'image/jpeg'
        if bytes_img[:8] == b'\x89PNG\r\n\x1a\n':
            return 'image/png'
        elif bytes_img[:2] == b'\xff\xd8':
            return 'image/jpeg'
        elif bytes_img[:4] == b'GIF8':
            return 'image/gif'
        elif bytes_img[:4] == b'RIFF' and bytes_img[8:12] == b'WEBP':
            return 'image/webp'
        elif bytes_img[:4] == b'\x42\x4d':
            return 'image/bmp'
        return 'image/jpeg'

    def _construir_contenido_multimodal(self, prompt, archivos_adjuntos=None):
        # Construye el contenido multimodal usando la API moderna de google.genai
        if not archivos_adjuntos or len(archivos_adjuntos) == 0:
            return prompt

        contenido = [prompt]

        for archivo in archivos_adjuntos:
            if archivo['tipo'] == 'imagen' and archivo.get('bytes'):
                mime_type = self._detectar_formato_imagen(archivo['bytes'])
                if types:
                    contenido.append(
                        types.Part.from_bytes(data=archivo['bytes'], mime_type=mime_type)
                    )
                else:
                    contenido.append({
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(archivo['bytes']).decode('utf-8')
                        }
                    })
            elif archivo['tipo'] == 'pdf' and archivo.get('bytes'):
                if types:
                    contenido.append(
                        types.Part.from_bytes(data=archivo['bytes'], mime_type='application/pdf')
                    )
                else:
                    contenido.append({
                        "inline_data": {
                            "mime_type": "application/pdf",
                            "data": base64.b64encode(archivo['bytes']).decode('utf-8')
                        }
                    })

        return contenido

    def _es_error_cuota(self, error):
        # Detecta si un error es de tipo cuota agotada (429 / RESOURCE_EXHAUSTED)
        error_str = str(error).lower()
        patrones_cuota = [
            '429', 'resource_exhausted', 'quota exceeded', 'rate limit',
            'too many requests', 'quota_dimension', 'quota_limit',
            'resource has been exhausted',
        ]
        return any(p in error_str for p in patrones_cuota)

    def _es_error_modelo_invalido(self, error):
        # Detecta si el error es porque el modelo no existe o no esta disponible
        error_str = str(error).lower()
        patrones_invalido = [
            'not found', 'invalid model', 'model not found', 'unsupported model',
            'does not exist', 'not supported', '404',
        ]
        return any(p in error_str for p in patrones_invalido)

    def _call_gemini_con_fallback(self, prompt, system_instruction=None, temperature=0.3,
                                   max_tokens=4096, archivos_adjuntos=None):
        # Llama a Gemini con cadena de fallback automatico
        if not self.is_ready():
            return None, None, "Cliente Gemini no inicializado"

        modelos_a_probar = [self.modelo_preferido]
        for m in self.CADENA_FALLBACK:
            if m not in modelos_a_probar:
                modelos_a_probar.append(m)

        contenido = self._construir_contenido_multimodal(prompt, archivos_adjuntos)

        info_fallback = []
        ultimo_error = None

        for modelo in modelos_a_probar:
            if self._esta_en_cooldown(modelo):
                msg = "Modelo " + modelo + " en cooldown (rate limit previo)"
                info_fallback.append(msg)
                continue

            for intento in range(3):
                try:
                    config_kwargs = {
                        'temperature': temperature,
                        'max_output_tokens': max_tokens,
                    }
                    if system_instruction:
                        config_kwargs['system_instruction'] = system_instruction

                    if types:
                        gen_config = types.GenerateContentConfig(**config_kwargs)
                    else:
                        gen_config = config_kwargs

                    response = self.client.models.generate_content(
                        model=modelo,
                        contents=contenido,
                        config=gen_config
                    )

                    texto = response.text if hasattr(response, 'text') else str(response)
                    self.ultimo_modelo_usado = modelo
                    self.estado_conexion = "CONECTADO"

                    if len(info_fallback) > 0:
                        info_msg = "Usando " + modelo + " (fallback tras: " + ", ".join(info_fallback) + ")"
                    else:
                        info_msg = "Usando " + modelo + " (modelo preferido)"

                    return texto, modelo, info_msg

                except Exception as e:
                    ultimo_error = e
                    error_str = str(e)

                    if self._es_error_cuota(e):
                        wait_time = (2 ** intento) + (time.time() % 1)
                        self._agregar_cooldown(modelo, segundos=60 * (intento + 1))
                        info_fallback.append(modelo + ": Cuota agotada")
                        time.sleep(wait_time)
                        break

                    elif self._es_error_modelo_invalido(e):
                        info_fallback.append(modelo + ": Modelo no disponible")
                        break

                    elif intento < 2:
                        wait_time = (2 ** intento) + 1
                        info_fallback.append(modelo + ": Error temporal (intento " + str(intento+1) + "/3)")
                        time.sleep(wait_time)
                    else:
                        info_fallback.append(modelo + ": Error persistente: " + error_str[:80])

        self.estado_conexion = "ERROR"
        error_final = str(ultimo_error) if ultimo_error else "Todos los modelos fallaron"
        return None, None, "Sin modelos disponibles. Ultimo error: " + error_final[:200]

    def generar_acr_completo(self, contexto_problema, tipo='ACR', archivos_adjuntos=None):
        # Genera un ACR/AFA completo a partir del contexto del problema
        ia_cfg = get_ia_cfg()
        estilo = ia_cfg.get('estilo_redaccion', 'tecnico_profesional')
        detalle = ia_cfg.get('nivel_detalle', 'detallado')
        idioma = ia_cfg.get('idioma', 'es')
        temp = float(ia_cfg.get('temperatura', 0.3))
        max_tok = int(ia_cfg.get('max_tokens', 4096))
        prompt_extra = ia_cfg.get('prompt_personalizado', '')

        instrucciones_archivos = ""
        if archivos_adjuntos and len(archivos_adjuntos) > 0:
            tipos_archivos = []
            for arch in archivos_adjuntos:
                if arch['tipo'] == 'imagen':
                    tipos_archivos.append("imagen (" + arch.get('nombre', 'foto') + ")")
                elif arch['tipo'] == 'pdf':
                    tipos_archivos.append("PDF (" + arch.get('nombre', 'documento') + ")")
            instrucciones_archivos = """
ADEMAS, se han adjuntado los siguientes archivos para tu analisis visual/documental: """ + ", ".join(tipos_archivos) + """.
Analiza cuidadosamente estas imagenes/documentos adjuntos para:
- Identificar componentes, equipos, condiciones visibles en las fotos
- Leer procedimientos, manuales o diagramas en los PDFs adjuntos
- Correlacionar lo que ves en las imagenes con el contexto descrito
- Identificar posibles causas visibles (desgaste, corrosion, fugas, danos, etc.)
- Extraer datos tecnicos relevantes de los documentos adjuntos
- Usar la informacion visual y documental para fundamentar mejor tus analisis de 5W+2H y 5 Porques
"""

        idioma_str = "espanol" if idioma == 'es' else "english"

        system_instruction = """Eres un experto en ingenieria mecatronica con 20 anos de experiencia en mantenimiento industrial, 
especializado en Analisis de Causa Raiz (ACR) y Analisis de Fallas (AFA) bajo normativas ISO 9001, ISO 14224, TPM y RCM.

Tu estilo de redaccion es: """ + estilo + """
Nivel de detalle requerido: """ + detalle + """
Idioma de respuesta: """ + idioma_str + """

Debes analizar el problema descrito y generar un documento ACR/AFA completo con:
- Descripcion tecnica precisa del problema
- Analisis 5W+2H detallado y justificado
- 5 Porques (Why-Why) con ramas multiples, cada una con causas raiz bien fundamentadas
- Condiciones basicas 6M (solo para ACR)
- Acciones inmediatas de contencion
- Acciones correctivas sobre causas raiz

Los textos deben ser profesionales, sin errores ortograficos, bien estructurados con parrafos completos,
usando terminologia tecnica apropiada de ingenieria mecatronica y mantenimiento industrial.

Responde UNICAMENTE en formato JSON con la siguiente estructura exacta:
{
    "desc_problema_inicial": "...",
    "que_contexto": "...",
    "como_ocurre": "...",
    "quien": "...",
    "donde": "...",
    "cuanto": "...",
    "cuando": "...",
    "cual": "...",
    "problema_enfocado": "...",
    "ramas_why_why": [
        {
            "definicion": "...",
            "pq1": "...",
            "pq2": "...",
            "pq3": "...",
            "pq4": "...",
            "pq5": "...",
            "causa_raiz": "...",
            "accion_causa_raiz": "...",
            "responsable": "...",
            "prioridad": "MEDIA"
        }
    ],
    "acciones_inmediatas": [
        {
            "accion": "...",
            "responsable": "...",
            "fecha": "YYYY-MM-DD",
            "estado": "PENDIENTE"
        }
    ],
    "condiciones_6m": [
        {
            "categoria": "MAQUINA",
            "item": "Lubricacion",
            "condicion_ideal": "...",
            "condicion_actual": "...",
            "aplica": "SI",
            "diferencia": "NO"
        }
    ]
}"""

        if prompt_extra:
            system_instruction = system_instruction + "\n\nINSTRUCCIONES ADICIONALES DEL USUARIO:\n" + prompt_extra

        prompt = instrucciones_archivos + "\n\nCONTEXTO DEL PROBLEMA (descrito por el usuario):\n" + contexto_problema + "\n\nTIPO DE DOCUMENTO: " + tipo + "\n\nGenera el documento completo en formato JSON. Asegurate de que cada campo tenga contenido sustancial con parrafos bien desarrollados, justificaciones tecnicas y analisis profundo como un especialista en ingenieria mecatronica lo haria."

        # Llamar con fallback automatico
        respuesta, modelo_usado, info = self._call_gemini_con_fallback(
            prompt,
            system_instruction=system_instruction,
            temperature=temp,
            max_tokens=max_tok,
            archivos_adjuntos=archivos_adjuntos
        )

        # Mostrar info de fallback en la UI
        if info:
            if "fallback" in info.lower():
                st.info("🔄 " + info)
            else:
                st.success(info)

        if not respuesta:
            st.error("❌ La IA no pudo generar el documento. " + info)
            return None

        try:
            json_match = re.search(r'\{.*\}', respuesta, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                return json.loads(respuesta)
        except json.JSONDecodeError as e:
            st.error("❌ La IA no devolvio un formato JSON valido. Error: " + str(e)[:100])
            st.code(respuesta[:500], language="text")
            return None

    def humanizar_texto(self, texto):
        if not texto or not self.is_ready():
            return texto

        system_instruction = "Eres un editor tecnico especializado en documentacion de mantenimiento industrial."
        prompt = """Reescribe el siguiente texto de un analisis ACR/AFA para que suene mas natural y humano,
manteniendo el tono profesional tecnico de ingenieria mecatronica. 
Corrige cualquier error ortografico o gramatical. 
Manten la terminologia tecnica pero haz que el flujo sea mas conversacional y menos robotico.
No agregues explicaciones, solo devuelve el texto reescrito.

TEXTO:
""" + texto

        respuesta, modelo, info = self._call_gemini_con_fallback(
            prompt,
            system_instruction=system_instruction,
            temperature=0.4,
            max_tokens=4096
        )
        return respuesta if respuesta else texto

    def corregir_ortografia(self, texto):
        if not texto or not self.is_ready():
            return texto

        system_instruction = "Eres un corrector ortografico profesional."
        prompt = """Corrige UNICAMENTE los errores ortograficos, gramaticales y de puntuacion del siguiente texto.
NO cambies el contenido, el significado ni la estructura. Solo corrige errores de redaccion.
Manten la terminologia tecnica intacta. Devuelve SOLO el texto corregido.

TEXTO:
""" + texto

        respuesta, modelo, info = self._call_gemini_con_fallback(
            prompt,
            system_instruction=system_instruction,
            temperature=0.1,
            max_tokens=4096
        )
        return respuesta if respuesta else texto

    def probar_conexion(self):
        if not self.is_ready():
            return False, "Cliente no inicializado. Verifique la API Key."

        try:
            respuesta, modelo, info = self._call_gemini_con_fallback(
                "Responde unicamente: CONEXION_OK",
                temperature=0.0,
                max_tokens=10
            )
            if respuesta and "CONEXION_OK" in respuesta:
                return True, "✅ Conexion exitosa con " + modelo + "! " + info
            else:
                resp_corta = respuesta[:100] if respuesta else 'Ninguna'
                return False, "⚠️ Conexion parcial. Respuesta: " + resp_corta
        except Exception as e:
            return False, "❌ Error de conexion: " + str(e)[:200]

# ==============================================================================
# CORRECCION ORTOGRAFICA CON LANGUAGE TOOL
# ==============================================================================
class OrtografiaEngine:
    def __init__(self):
        self.tool = None
        if LANG_TOOL_AVAILABLE:
            try:
                self.tool = language_tool_python.LanguageTool('es')
            except Exception:
                pass

    def is_ready(self):
        return self.tool is not None

    def corregir(self, texto):
        if not texto or not self.is_ready():
            return texto
        try:
            matches = self.tool.check(texto)
            return language_tool_python.utils.correct(texto, matches)
        except Exception:
            return texto

# ==============================================================================
# FUNCIONES DE CORRECCION UNIFICADAS
# ==============================================================================
def corregir_texto(texto, usar_ia=True):
    if not texto:
        return texto

    ia_cfg = get_ia_cfg()
    usar_correccion = ia_cfg.get('activar_correccion', 1) == 1

    if not usar_correccion:
        return texto

    lt = OrtografiaEngine()
    if lt.is_ready():
        texto = lt.corregir(texto)

    if usar_ia:
        api_key = ia_cfg.get('api_key', '')
        modelo = ia_cfg.get('modelo', 'gemini-3.5-flash')
        if api_key:
            gemini = GeminiEngine(api_key, modelo)
            if gemini.is_ready():
                texto = gemini.corregir_ortografia(texto)

    return texto

def humanizar_texto(texto):
    if not texto:
        return texto

    ia_cfg = get_ia_cfg()
    usar_humanizar = ia_cfg.get('activar_humanizar', 1) == 1

    if not usar_humanizar:
        return texto

    api_key = ia_cfg.get('api_key', '')
    modelo = ia_cfg.get('modelo', 'gemini-3.5-flash')
    if api_key:
        gemini = GeminiEngine(api_key, modelo)
        if gemini.is_ready():
            return gemini.humanizar_texto(texto)

    return texto

def procesar_texto_final(texto):
    texto = corregir_texto(texto, usar_ia=True)
    texto = humanizar_texto(texto)
    return texto

# ==============================================================================
# HISTORICO DE DOCUMENTOS
# ==============================================================================
def archivar_documento(codigo, motivo="Documento completado y cerrado"):
    doc = db_one("SELECT * FROM documentos WHERE codigo=?", (codigo,))
    if not doc:
        return False

    d = dict(doc)

    accs = db_query("SELECT COUNT(*) as total FROM acciones_inmediatas WHERE codigo_acr=?", (codigo,))
    accs_cerr = db_query("SELECT COUNT(*) as total FROM acciones_inmediatas WHERE codigo_acr=? AND estado='CERRADO'", (codigo,))

    datos_json = json.dumps(d, default=str, ensure_ascii=False)

    codigo_historico = "HIST-" + codigo + "-" + datetime.datetime.now().strftime('%Y%m%d%H%M%S')

    db_run("""INSERT INTO historico_documentos
        (codigo_original, codigo_historico, tipo_documento, motivo_archivado,
         estado_final, datos_json, acciones_completadas, acciones_totales)
        VALUES(?,?,?,?,?,?,?,?)""",
        (codigo, codigo_historico, d['tipo_documento'], motivo,
         d['estado'], datos_json,
         accs_cerr[0]['total'] if accs_cerr else 0,
         accs[0]['total'] if accs else 0))

    db_run("UPDATE documentos SET es_historico=1, fecha_archivado=? WHERE codigo=?",
           (datetime.datetime.now().isoformat(), codigo))

    return True

def obtener_historico(filtro_tipo='TODOS', busqueda=''):
    sql = "SELECT * FROM historico_documentos WHERE 1=1"
    params = []
    if filtro_tipo != 'TODOS':
        sql += " AND tipo_documento=?"
        params.append(filtro_tipo)
    if busqueda:
        sql += " AND (codigo_original LIKE ? OR codigo_historico LIKE ? OR motivo_archivado LIKE ?)"
        b = "%" + busqueda + "%"
        params.extend([b, b, b])
    sql += " ORDER BY fecha_archivado DESC"
    return db_query(sql, tuple(params))

def restaurar_documento(codigo_historico):
    hist = db_one("SELECT * FROM historico_documentos WHERE codigo_historico=?", (codigo_historico,))
    if not hist:
        return None

    datos = json.loads(hist['datos_json'])

    nuevo_codigo = gen_codigo(datos['tipo_documento'])
    datos['codigo'] = nuevo_codigo
    datos['estado'] = 'BORRADOR'
    datos['es_historico'] = 0
    datos['fecha_archivado'] = None
    datos['version'] = (datos.get('version', 1) or 1) + 1
    datos['documento_padre'] = hist['codigo_original']

    cols = []
    vals = []
    for k, v in datos.items():
        if k not in ['id', 'fecha_registro', 'ultima_modificacion']:
            cols.append(k)
            vals.append(v)

    placeholders = ','.join(['?' for _ in vals])
    db_run("INSERT INTO documentos (" + ','.join(cols) + ") VALUES (" + placeholders + ")", tuple(vals))

    return nuevo_codigo

def obtener_estadisticas_historico():
    total_docs = db_one("SELECT COUNT(*) as total FROM documentos WHERE es_historico=0")
    total_hist = db_one("SELECT COUNT(*) as total FROM historico_documentos")

    accs_totales = db_one("""SELECT COUNT(*) as total FROM acciones_inmediatas ai
        JOIN documentos d ON ai.codigo_acr = d.codigo WHERE d.es_historico=0""")
    accs_cerradas = db_one("""SELECT COUNT(*) as total FROM acciones_inmediatas ai
        JOIN documentos d ON ai.codigo_acr = d.codigo 
        WHERE d.es_historico=0 AND ai.estado='CERRADO'""")

    return {
        'total_activos': total_docs['total'] if total_docs else 0,
        'total_historico': total_hist['total'] if total_hist else 0,
        'acciones_totales': accs_totales['total'] if accs_totales else 0,
        'acciones_cerradas': accs_cerradas['total'] if accs_cerradas else 0,
    }

print("Parte 2 generada correctamente")



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
    data = [[Paragraph('<b>' + texto + '</b>', estilos['seccion'])]]
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
            logo_cell = Paragraph('<b>' + nombre + '</b>',
                ParagraphStyle('LT', parent=estilos['celda'], alignment=TA_CENTER, fontSize=8))
    else:
        logo_cell = Paragraph(
            '<font size="14" color="#e76f51"><b>O</b></font>'
            '<font size="14" color="#1e3a5f"><b>RICA</b></font>',
            ParagraphStyle('LC', parent=estilos['celda'], alignment=TA_CENTER, fontSize=14))

    centro = []
    for linea in texto_enc.split('\n'):
        if linea.strip():
            centro.append(Paragraph('<b>' + linea.strip() + '</b>',
                ParagraphStyle('CH', parent=estilos['celda'], alignment=TA_CENTER, fontSize=8)))
    centro.append(Paragraph('<b>' + tipo_doc + '</b>',
        ParagraphStyle('CS', parent=estilos['celda'], alignment=TA_CENTER,
                       fontSize=10, textColor=C['azul'])))

    der = [
        Paragraph('<b>Valido desde: 24/04/2026</b>',
            ParagraphStyle('D1', parent=estilos['celda'], fontSize=7)),
        Paragraph('<b>' + codigo_form + '</b>',
            ParagraphStyle('D2', parent=estilos['celda'], fontSize=8, alignment=TA_RIGHT)),
        Paragraph('Prox. revision: 24/04/2029',
            ParagraphStyle('D3', parent=estilos['celda'], fontSize=7)),
        Paragraph('<b>' + edicion + '</b>',
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
    texto_pie = cfg.get('texto_pie_pagina') or         'Documento Controlado | Normativa: ISO 9001 / ISO 14224 / TPM / RCM'
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
            'Pagina ' + str(doc_obj.page) + '  |  ' + codigo + '  |  ' + tipo_doc_label)
        canvas_obj.restoreState()

    tpl_p = PageTemplate(id='portrait',  frames=[fr_port], pagesize=A4_PORT,
                         onPage=lambda c,d: _pie(c,d, A4_PORT[0]))
    tpl_l = PageTemplate(id='landscape', frames=[fr_land], pagesize=A4_LAND,
                         onPage=lambda c,d: _pie(c,d, A4_LAND[0]))

    doc = BaseDocTemplate(buf_pdf, pageTemplates=[tpl_p, tpl_l], pagesize=A4_PORT)

    def HDR(aw): return _hdr_inst(codigo_form, edicion, tipo_doc_label, codigo, E, aw, cfg)
    def SEC(txt, aw=AW_PORT): return _sec_header(txt, E, aw)
    def TXT(txt, aw=AW_PORT): return _celda_texto(txt, E, aw)

    d = dict(db_one("SELECT * FROM documentos WHERE codigo=?", (codigo,)) or {})
    EL = []

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
    hdr_a = [[Paragraph('<b>' + t + '</b>', E['header']) for t in ['Accion','Responsable','Fecha','Estado','Eficacia']]]
    rows_a = [[Paragraph(r['accion'] or '', E['celda']), Paragraph(r['responsable'] or '', E['celda']),
               Paragraph(r['fecha'] or '', E['celda']),  Paragraph(r['estado'] or '', E['celda']),
               Paragraph(r['eficacia'] or '', E['celda'])] for r in accs] or              [[Paragraph('',E['celda'])]*5]
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
        hdr_c = [[Paragraph('<b>' + t + '</b>', E['header'])
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

    # Why-Why
    num_ww = "9" if es_acr else "7"
    EL.extend([NextPageTemplate('landscape'), PageBreak()])
    EL.extend([HDR(AW_LAND), Spacer(1,4)])
    EL.append(SEC(num_ww + ".- Analisis Why Why (WW)", AW_LAND))

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
    hdr_ww = [[Paragraph('<b>' + t + '</b>', est_fl if t=='>' else E['header']) for t in cols_ww]]
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
        prio = (w['prioridad'] or 'MEDIA').strip().upper()
        if prio not in ['BAJA','MEDIA','ALTA','CRITICA']:
            prio = 'MEDIA'
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

    # Cierre
    EL.extend([NextPageTemplate('portrait'), PageBreak()])
    EL.extend([HDR(AW_PORT), Spacer(1,4)])
    num_cierre = "10" if es_acr else "8"
    EL.append(SEC(num_cierre + ".- Cierre y Verificacion"))
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

    # Anexos
    evis = db_query("SELECT * FROM evidencias WHERE codigo_documento=? ORDER BY fecha_registro", (codigo,))
    if evis:
        num_anx = "11" if es_acr else "9"
        EL.extend([PageBreak(), HDR(AW_PORT), Spacer(1,4)])
        EL.append(SEC(num_anx + ".- Anexos (Evidencias fotograficas)"))
        for i, evi in enumerate(evis, 1):
            img_b = evi['imagen_blob']
            desc = evi['descripcion'] or evi['nombre_archivo'] or ("Imagen " + str(i))
            tipo_e = evi['tipo_evidencia'] or ''
            fmt = (evi['formato'] or '.jpg').lower()
            cap = Paragraph('<b>Figura ' + str(i) + '.</b> [' + tipo_e + '] ' + desc,
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
                    EL.append(Paragraph('Figura ' + str(i) + '. ' + desc + ' (imagen no disponible)', E['normal']))
            EL.append(Spacer(1,6))

    EL.extend([Spacer(1,10),
               HRFlowable(width="100%", thickness=0.8, color=C['gris']),
               Paragraph('<i>' + nombre_empresa + ' | ' + texto_pie + '</i>', E['pie'])])

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
        st.markdown("""
        <div style="padding:10px 0">
            <div style="font-size:1.5rem;font-weight:700;color:#1e3a5f">""" + nombre + """</div>
            <div style="font-size:.9rem;color:#2a5a8c">
                Sistema de Gestion Documental — ACR / AFA | ISO 9001 · ISO 14224 · TPM · RCM
            </div>
        </div>""", unsafe_allow_html=True)
    st.markdown("---")

def estado_color(estado):
    m = {'BORRADOR':'🔘','EN_ANALISIS':'🔵','REVISADO':'🟡',
         'APROBADO':'🟢','CERRADO':'⚫','RECHAZADO':'🔴'}
    return m.get(estado, '⚪')

print("Parte 3 generada correctamente")



# ==============================================================================
# PAGINAS PRINCIPALES
# ==============================================================================

# ── Pagina: Dashboard ─────────────────────────────────────────────────────────
def page_dashboard():
    show_header()
    st.markdown("## 📊 Panel Principal")

    docs = db_query("SELECT * FROM documentos WHERE es_historico=0 ORDER BY fecha_registro DESC")
    total = len(docs)
    acrs  = sum(1 for d in docs if d['tipo_documento']=='ACR')
    afas  = total - acrs
    abiertos = sum(1 for d in docs if d['estado'] not in ('CERRADO','APROBADO'))
    cerrados = sum(1 for d in docs if d['estado'] in ('CERRADO','APROBADO'))

    stats = obtener_estadisticas_historico()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📄 Total Documentos", total)
    c2.metric("🔍 ACR", acrs)
    c3.metric("⚠️ AFA", afas)
    c4.metric("✅ Cerrados / Aprobados", cerrados)
    c5.metric("📚 Historico", stats['total_historico'])

    st.markdown("---")

    today = datetime.date.today().isoformat()
    accs_venc = db_query("""SELECT ai.*, d.tipo_documento, d.codigo 
        FROM acciones_inmediatas ai
        JOIN documentos d ON ai.codigo_acr = d.codigo
        WHERE ai.fecha < ? AND ai.estado != 'CERRADO' AND d.es_historico=0""", (today,))
    if accs_venc:
        st.warning("⚠️ **" + str(len(accs_venc)) + " accion(es) vencida(s)** — Requiere atencion inmediata")

    st.markdown("### 📋 Documentos Recientes")

    if not docs:
        st.info("No hay documentos registrados. Cree su primer ACR o AFA desde el menu lateral.")
        return

    for d in docs[:15]:
        with st.expander(
            estado_color(d['estado']) + " **" + d['codigo'] + "** — " + d['tipo_documento'] + " | " +
            (d['desc_problema_inicial'][:70] if d['desc_problema_inicial'] else 'Sin descripcion') + "...",
            expanded=False
        ):
            c1, c2, c3 = st.columns(3)
            c1.write("**Tipo:** " + d['tipo_documento'])
            c1.write("**Estado:** " + d['estado'])
            c2.write("**Reportado por:** " + d['reportado_por'])
            c2.write("**Area:** " + (d['area_equipo'] or '—'))
            c3.write("**Prioridad:** " + d['prioridad'])
            c3.write("**Fecha:** " + d['fecha_reporte'])

            bc1, bc2, bc3, bc4 = st.columns([1,1,1,1])
            if bc1.button("✏️ Editar", key="edit_" + d['codigo']):
                st.session_state['pagina'] = 'form'
                st.session_state['doc_codigo'] = d['codigo']
                st.session_state['doc_tipo'] = d['tipo_documento']
                st.rerun()
            if bc2.button("📄 Exportar PDF", key="pdf_" + d['codigo']):
                with st.spinner("Generando PDF..."):
                    pdf_bytes = exportar_pdf(d['codigo'], d['tipo_documento']=='ACR')
                bc2.download_button("⬇️ Descargar", pdf_bytes,
                                    file_name=d['codigo'] + ".pdf",
                                    mime="application/pdf",
                                    key="dl_" + d['codigo'])
            if d['estado'] in ('CERRADO', 'APROBADO'):
                if bc3.button("📚 Archivar", key="arch_" + d['codigo']):
                    archivar_documento(d['codigo'])
                    st.success("Documento " + d['codigo'] + " archivado al historico.")
                    st.rerun()
            if bc4.button("🗑 Eliminar", key="del_" + d['codigo']):
                db_run("DELETE FROM documentos WHERE codigo=?", (d['codigo'],))
                st.success("Documento " + d['codigo'] + " eliminado.")
                st.rerun()

# ── Pagina: Nuevo / Editar Documento ─────────────────────────────────────────
def page_form():
    show_header()
    tipo = st.session_state.get('doc_tipo', 'ACR')
    codigo = st.session_state.get('doc_codigo')
    es_nuevo = codigo is None

    icon = "🔍" if tipo == 'ACR' else "⚠️"
    titulo_tipo = "ANALISIS DE CAUSA RAIZ" if tipo == 'ACR' else "ANALISIS DE FALLAS"
    st.markdown("## " + icon + " " + titulo_tipo + " (" + tipo + ")")

    d = {}
    if not es_nuevo:
        row = db_one("SELECT * FROM documentos WHERE codigo=?", (codigo,))
        if row:
            d = dict(row)
        else:
            st.error("Documento no encontrado.")
            return

    if es_nuevo:
        codigo = gen_codigo(tipo)
        st.info("**Codigo generado:** `" + codigo + "`")
    else:
        st.info("**Editando:** `" + codigo + "`")

    # ── SECCION IA ────────────────────────────────────────────────────────────
    ia_cfg = get_ia_cfg()
    api_key = ia_cfg.get('api_key', '')

    # Mostrar estado de conexion IA
    st.markdown("---")

    # Barra de estado de IA
    col_estado_ia, col_info_ia = st.columns([1, 3])
    with col_estado_ia:
        if api_key and GEMINI_AVAILABLE:
            gemini_test = GeminiEngine(api_key, ia_cfg.get('modelo','gemini-3.5-flash'))
            if gemini_test.is_ready():
                st.markdown('<div class="ia-status-ok">🟢 IA Conectada</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="ia-status-err">🔴 IA Error</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="ia-status-warn">🟡 IA No Configurada</div>', unsafe_allow_html=True)

    with col_info_ia:
        modelo_actual = ia_cfg.get('modelo', 'gemini-3.5-flash')
        st.caption("Modelo: `" + modelo_actual + "` | Fallback automatico: " + 
                   ("✅ Activado" if ia_cfg.get('fallback_automatico', 1) else "❌ Desactivado"))

    st.markdown("### 🤖 Asistente IA — Generacion Automatica con Gemini")

    with st.expander("📝 Ingresar Contexto del Problema para IA", expanded=es_nuevo):
        st.markdown("""
        <div class="ia-context-box">
            <b>Instrucciones:</b> Describa el problema con sus propias palabras. Sea lo mas detallado posible:
            <ul>
                <li>Que equipo o proceso fallo</li>
                <li>Cuando y como ocurrio</li>
                <li>Sintomas observados</li>
                <li>Impacto en produccion, seguridad o medio ambiente</li>
                <li>Cualquier dato relevante (temperaturas, presiones, vibraciones, etc.)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        contexto_ia = st.text_area(
            "Describa el problema con sus propias palabras:",
            height=200,
            placeholder="Ejemplo: El motor principal de la bomba de agua de enfriamiento del reactor R-101 presento vibraciones anormales desde el turno de la noche. El operador reporto ruido metalico y temperatura del casing elevada a 85C (normal: 60C). La bomba se detuvo automaticamente por proteccion termica...",
            key="contexto_ia_input"
        )

        # ── ARCHIVOS ADJUNTOS PARA LA IA ──
        st.markdown("---")
        st.markdown("### 📎 Adjuntar Archivos para Analisis de la IA")
        st.caption("Suba fotos del problema, manuales tecnicos, procedimientos, diagramas, o cualquier documento que ayude a la IA a entender mejor el contexto.")

        archivos_ia = st.file_uploader(
            "Seleccionar imagenes o PDFs (fotos del problema, manuales, procedimientos, diagramas)",
            type=['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'pdf'],
            accept_multiple_files=True,
            key="archivos_ia_uploader"
        )

        # Mostrar preview de archivos adjuntos
        if archivos_ia:
            cols_preview = st.columns(min(len(archivos_ia), 4))
            archivos_procesados = []
            for i, archivo in enumerate(archivos_ia):
                bytes_archivo = archivo.read()
                tipo_archivo = 'imagen' if archivo.type.startswith('image/') else 'pdf'
                archivos_procesados.append({
                    'bytes': bytes_archivo,
                    'tipo': tipo_archivo,
                    'nombre': archivo.name,
                    'mime': archivo.type
                })
                with cols_preview[i % 4]:
                    if tipo_archivo == 'imagen':
                        try:
                            img = Image.open(io.BytesIO(bytes_archivo))
                            st.image(img, caption="📷 " + archivo.name, use_container_width=True)
                        except Exception:
                            st.info("📷 " + archivo.name)
                    else:
                        st.info("📄 " + archivo.name + " (PDF)")
            # Guardar en session state para uso posterior
            st.session_state['ia_archivos_adjuntos'] = archivos_procesados
        else:
            st.session_state['ia_archivos_adjuntos'] = []

        st.markdown("---")
        col_gen, col_cfg = st.columns([1, 3])
        generar_ia = col_gen.button("🤖 GENERAR DOCUMENTO CON IA", type="primary", use_container_width=True)

        with col_cfg:
            modelo_display = ia_cfg.get('modelo','gemini-3.5-flash')
            correccion_display = '✅' if ia_cfg.get('activar_correccion') else '❌'
            humanizar_display = '✅' if ia_cfg.get('activar_humanizar') else '❌'
            st.caption("Modelo: " + modelo_display + " | Correccion: " + correccion_display + " | Humanizar: " + humanizar_display)

        if generar_ia:
            if not api_key:
                st.error("❌ No hay API Key configurada. Configure la IA en el menu lateral > Configuracion IA.")
            elif not contexto_ia.strip():
                st.error("❌ Debe describir el problema antes de generar.")
            else:
                archivos_adjuntos = st.session_state.get('ia_archivos_adjuntos', [])
                num_archivos = len(archivos_adjuntos)
                if num_archivos > 0:
                    mensaje_procesando = "🤖 La IA esta analizando el problema y " + str(num_archivos) + " archivo(s) adjunto(s)... Esto puede tomar 30-90 segundos."
                else:
                    mensaje_procesando = "🤖 La IA esta analizando el problema y generando el documento completo... Esto puede tomar 30-60 segundos."

                with st.spinner(mensaje_procesando):
                    gemini = GeminiEngine(api_key, ia_cfg.get('modelo','gemini-3.5-flash'))
                    resultado = gemini.generar_acr_completo(contexto_ia, tipo, archivos_adjuntos=archivos_adjuntos)

                if resultado:
                    st.session_state['ia_resultado'] = resultado
                    st.session_state['ia_codigo'] = codigo
                    st.session_state['ia_tipo'] = tipo
                    st.success("✅ Documento generado por IA. Revise y ajuste los campos en las pestanas.")
                    st.rerun()
                else:
                    st.error("❌ La IA no pudo generar el documento. Verifique su API Key e intente de nuevo.")

    # Aplicar resultados de IA
    ia_resultado = st.session_state.get('ia_resultado')
    if ia_resultado and st.session_state.get('ia_codigo') == codigo:
        if es_nuevo:
            _save_doc_general(codigo, tipo, True, {
                'fecha_reporte': datetime.date.today(),
                'reportado_por': 'Generado por IA',
                'estado': 'BORRADOR',
                'prioridad': 'MEDIA',
            })

        campos_ia = {
            'desc_problema_inicial': ia_resultado.get('desc_problema_inicial', ''),
            'que_contexto': ia_resultado.get('que_contexto', ''),
            'como_ocurre': ia_resultado.get('como_ocurre', ''),
            'quien': ia_resultado.get('quien', ''),
            'donde': ia_resultado.get('donde', ''),
            'cuanto': ia_resultado.get('cuanto', ''),
            'cuando': ia_resultado.get('cuando', ''),
            'cual': ia_resultado.get('cual', ''),
            'problema_enfocado': ia_resultado.get('problema_enfocado', ''),
        }

        for k, v in campos_ia.items():
            if v:
                campos_ia[k] = procesar_texto_final(v)

        db_run("""UPDATE documentos SET
            desc_problema_inicial=?, que_contexto=?, como_ocurre=?,
            quien=?, donde=?, cuanto=?, cuando=?, cual=?,
            problema_enfocado=?, ultima_modificacion=CURRENT_TIMESTAMP
            WHERE codigo=?""",
            (campos_ia['desc_problema_inicial'], campos_ia['que_contexto'],
             campos_ia['como_ocurre'], campos_ia['quien'], campos_ia['donde'],
             campos_ia['cuanto'], campos_ia['cuando'], campos_ia['cual'],
             campos_ia['problema_enfocado'], codigo))

        for i, rama in enumerate(ia_resultado.get('ramas_why_why', []), 1):
            rama_corregida = {k: procesar_texto_final(v) if isinstance(v, str) else v 
                             for k, v in rama.items()}
            db_run("""INSERT OR REPLACE INTO why_why
                (codigo_documento, rama_id, definicion, pq1, pq2, pq3, pq4, pq5,
                 causa_raiz, accion_causa_raiz, responsable, prioridad, fecha)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (codigo, str(i), rama_corregida.get('definicion',''),
                 rama_corregida.get('pq1',''), rama_corregida.get('pq2',''),
                 rama_corregida.get('pq3',''), rama_corregida.get('pq4',''),
                 rama_corregida.get('pq5',''), rama_corregida.get('causa_raiz',''),
                 rama_corregida.get('accion_causa_raiz',''),
                 rama_corregida.get('responsable',''),
                 rama_corregida.get('prioridad','MEDIA'),
                 str(datetime.date.today())))

        for acc in ia_resultado.get('acciones_inmediatas', []):
            acc_corregida = {k: procesar_texto_final(v) if isinstance(v, str) else v 
                            for k, v in acc.items()}
            db_run("""INSERT INTO acciones_inmediatas
                (codigo_acr, accion, responsable, fecha, estado)
                VALUES(?,?,?,?,?)""",
                (codigo, acc_corregida.get('accion',''),
                 acc_corregida.get('responsable',''),
                 acc_corregida.get('fecha', str(datetime.date.today())),
                 acc_corregida.get('estado','PENDIENTE')))

        if tipo == 'ACR':
            for cond in ia_resultado.get('condiciones_6m', []):
                db_run("""INSERT OR REPLACE INTO condiciones_basicas
                    (codigo_acr, categoria_6m, item, condicion_ideal, condicion_actual, aplica, diferencia)
                    VALUES(?,?,?,?,?,?,?)""",
                    (codigo, cond.get('categoria',''), cond.get('item',''),
                     procesar_texto_final(cond.get('condicion_ideal','')),
                     procesar_texto_final(cond.get('condicion_actual','')),
                     cond.get('aplica','SI'), cond.get('diferencia','NO')))


        # ==============================================================================
        # GUARDAR IMAGENES ADJUNTAS PARA IA COMO EVIDENCIAS/ANEXOS DEL DOCUMENTO
        # ==============================================================================
        archivos_ia_guardar = st.session_state.get('ia_archivos_adjuntos', [])
        if archivos_ia_guardar:
            num_evis_guardadas = 0
            for idx, archivo in enumerate(archivos_ia_guardar):
                if archivo.get('bytes'):
                    tipo_evi = 'REFERENCIA'
                    desc_evi = 'Imagen adjunta para analisis de IA'
                    if archivo['tipo'] == 'imagen':
                        tipo_evi = 'REFERENCIA'
                        desc_evi = 'Foto del problema - Analisis IA (' + str(idx+1) + ')'
                    elif archivo['tipo'] == 'pdf':
                        tipo_evi = 'REFERENCIA'
                        desc_evi = 'Documento adjunto - Analisis IA (' + str(idx+1) + '): ' + archivo.get('nombre', 'PDF')
                    
                    fmt = '.' + archivo.get('nombre', 'file.jpg').split('.')[-1].lower()
                    if fmt not in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.pdf']:
                        fmt = '.jpg'
                    
                    db_run("""INSERT INTO evidencias
                        (codigo_documento, nombre_archivo, tipo_evidencia, descripcion,
                         imagen_blob, tamano_bytes, formato, seccion)
                        VALUES(?,?,?,?,?,?,?,?)""",
                        (codigo,
                         archivo.get('nombre', 'archivo_' + str(idx+1)),
                         tipo_evi,
                         desc_evi,
                         archivo['bytes'],
                         len(archivo['bytes']),
                         fmt,
                         'GENERAL'))
                    num_evis_guardadas += 1
            
            if num_evis_guardadas > 0:
                st.success('📎 ' + str(num_evis_guardadas) + ' imagen(es)/documento(s) adjunto(s) guardados como evidencias en el documento.')

        del st.session_state['ia_resultado']
        del st.session_state['ia_codigo']
        del st.session_state['ia_tipo']

        row = db_one("SELECT * FROM documentos WHERE codigo=?", (codigo,))
        if row:
            d = dict(row)
        st.success("✅ Campos de IA aplicados. Puede editarlos manualmente en las pestanas.")
        st.rerun()

    # ── TABS ──────────────────────────────────────────────────────────────────
    if tipo == 'ACR':
        tabs = st.tabs(["1. Datos Generales", "2. Problema / 5W+2H",
                        "3. Condiciones 6M", "4. Analisis WW",
                        "5. Cierre", "6. Anexos"])
    else:
        tabs = st.tabs(["1. Datos Generales", "2. Problema / 5W+2H",
                        "3. Analisis WW", "4. Cierre", "5. Anexos"])

    # ── TAB 1: Datos Generales ────────────────────────────────────────────────
    with tabs[0]:
        st.markdown('<div class="seccion-band">1. DATOS GENERALES Y PARTICIPANTES</div>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            fecha_reporte   = st.date_input("Fecha de Reporte *",
                value=datetime.date.fromisoformat(d['fecha_reporte']) if d.get('fecha_reporte') else datetime.date.today(),
                key="fr")
            reportado_por   = st.text_input("Reportado por *", value=d.get('reportado_por',''), key="rp")
            cargo_reportante= st.text_input("Cargo del reportante", value=d.get('cargo_reportante',''), key="cr")
            area_reportante = st.text_input("Area reportante", value=d.get('area_reportante',''), key="ar")
        with c2:
            lider_afa       = st.text_input("Lider del AFA", value=d.get('lider_afa',''), key="la")
            area_equipo     = st.text_input("Area / Equipo", value=d.get('area_equipo',''), key="ae")
            responsables    = st.text_area("Responsables del analisis", value=d.get('responsables',''),
                                           height=80, key="resp")
            fecha_inicio    = st.date_input("Fecha inicio del analisis",
                value=datetime.date.fromisoformat(d['fecha_inicio_analisis'])
                      if d.get('fecha_inicio_analisis') else datetime.date.today(), key="fi")

        c3, c4 = st.columns(2)
        with c3:
            estado  = st.selectbox("Estado del documento",
                ['BORRADOR','EN_ANALISIS','REVISADO','APROBADO','RECHAZADO','CERRADO'],
                index=['BORRADOR','EN_ANALISIS','REVISADO','APROBADO','RECHAZADO','CERRADO'].index(
                    d.get('estado','BORRADOR')), key="est")
            prioridad = st.selectbox("Prioridad",['BAJA','MEDIA','ALTA','CRITICA'],
                index=['BAJA','MEDIA','ALTA','CRITICA'].index(
                (d.get('prioridad','MEDIA') or 'MEDIA').strip().upper() if (d.get('prioridad','MEDIA') or 'MEDIA').strip().upper() in ['BAJA','MEDIA','ALTA','CRITICA'] else 'MEDIA'
            ), key="prio")
        with c4:
            aprobado_por = st.text_input("Aprobado por", value=d.get('aprobado_por',''), key="ap")
            costo_estimado = st.number_input("Costo estimado (S/.)", min_value=0.0,
                value=float(d.get('costo_estimado') or 0), step=100.0, key="ce")

        st.markdown("**Impactos**")
        ci1, ci2, ci3 = st.columns(3)
        imp_prod = ci1.text_input("Impacto en Produccion", value=d.get('impacto_produccion',''), key="ip")
        imp_seg  = ci2.text_input("Impacto en Seguridad", value=d.get('impacto_seguridad',''), key="is")
        imp_amb  = ci3.text_input("Impacto Ambiental", value=d.get('impacto_ambiental',''), key="ia")

        if tipo == 'ACR':
            st.markdown('<div class="seccion-band">REGISTRO DE SESIONES</div>', unsafe_allow_html=True)
            sesiones_db = db_query("SELECT * FROM sesiones_acr WHERE codigo_acr=? ORDER BY sesion_num",
                                   (codigo,)) if not es_nuevo else []

            with st.form("form_sesion"):
                sc1, sc2, sc3 = st.columns(3)
                ses_num  = sc1.number_input("N° Sesion", min_value=1,
                    value=len(sesiones_db)+1, step=1)
                ses_fech = sc2.date_input("Fecha sesion", value=datetime.date.today())
                ses_hora = sc3.text_input("Hora inicio (HH:MM)", value="08:00")
                sc4, sc5 = st.columns(2)
                ses_dur  = sc4.text_input("Duracion (hrs)", value="2")
                ses_part = sc5.text_area("Participantes", height=60)
                ses_obs  = st.text_area("Observaciones", height=60)
                if st.form_submit_button("+ Agregar Sesion", type="primary"):
                    db_run("INSERT INTO sesiones_acr (codigo_acr,sesion_num,fecha,hora_inicio,duracion,participantes,observaciones) VALUES(?,?,?,?,?,?,?)",
                           (codigo, ses_num, str(ses_fech), ses_hora, ses_dur, ses_part, ses_obs))
                    st.success("Sesion agregada.")
                    st.rerun()

            if sesiones_db:
                st.dataframe(
                    [{"Sesion": s['sesion_num'], "Fecha": s['fecha'], "Hora": s['hora_inicio'],
                      "Duracion": s['duracion'], "Participantes": s['participantes'],
                      "Observaciones": s['observaciones']} for s in sesiones_db],
                    use_container_width=True, hide_index=True)

        if st.button("💾 Guardar Datos Generales", type="primary", key="save_gen"):
            _save_doc_general(codigo, tipo, es_nuevo, locals())
            st.session_state['doc_codigo'] = codigo
            st.session_state['es_nuevo_guardado'] = False
            st.success("✅ Guardado correctamente. Codigo: `" + codigo + "`")
            st.rerun()

    # ── TAB 2: Problema / 5W+2H ───────────────────────────────────────────────
    with tabs[1]:
        _tab_problema(codigo, d, tipo, es_nuevo)

    if tipo == 'ACR':
        with tabs[2]:
            _tab_condiciones_6m(codigo, d, es_nuevo)
        with tabs[3]:
            _tab_why_why(codigo, es_nuevo)
        with tabs[4]:
            _tab_cierre(codigo, d, es_nuevo)
        with tabs[5]:
            _tab_anexos(codigo, es_nuevo)
    else:
        with tabs[2]:
            _tab_why_why(codigo, es_nuevo)
        with tabs[3]:
            _tab_cierre(codigo, d, es_nuevo)
        with tabs[4]:
            _tab_anexos(codigo, es_nuevo)

    st.markdown("---")
    if not es_nuevo or st.session_state.get('doc_codigo'):
        cod_actual = st.session_state.get('doc_codigo', codigo)
        st.markdown("### 📥 Exportar Documento")
        if st.button("📄 Generar PDF Institucional", type="primary"):
            with st.spinner("Generando PDF con orientacion inteligente..."):
                pdf_b = exportar_pdf(cod_actual, tipo=='ACR')
            st.download_button("⬇️ Descargar PDF", pdf_b,
                               file_name=cod_actual + ".pdf",
                               mime="application/pdf")

def _save_doc_general(codigo, tipo, es_nuevo, local_vars):
    fr    = str(local_vars.get('fecha_reporte', datetime.date.today()))
    rp    = local_vars.get('reportado_por', '')
    cr    = local_vars.get('cargo_reportante', '')
    ar    = local_vars.get('area_reportante', '')
    la    = local_vars.get('lider_afa', '')
    ae    = local_vars.get('area_equipo', '')
    resp  = local_vars.get('responsables', '')
    fi    = str(local_vars.get('fecha_inicio', datetime.date.today()))
    est   = local_vars.get('estado', 'BORRADOR')
    prio  = local_vars.get('prioridad', 'MEDIA')
    ap    = local_vars.get('aprobado_por', '')
    ce    = local_vars.get('costo_estimado', 0.0)
    ip    = local_vars.get('imp_prod', '')
    is_   = local_vars.get('imp_seg', '')
    ia    = local_vars.get('imp_amb', '')

    if es_nuevo:
        db_run("""INSERT OR IGNORE INTO documentos
            (tipo_documento,codigo,fecha_reporte,estado,reportado_por,cargo_reportante,
             area_reportante,lider_afa,area_equipo,responsables,fecha_inicio_analisis,
             aprobado_por,prioridad,costo_estimado,impacto_produccion,impacto_seguridad,impacto_ambiental)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (tipo,codigo,fr,est,rp,cr,ar,la,ae,resp,fi,ap,prio,ce,ip,is_,ia))
    else:
        db_run("""UPDATE documentos SET
            fecha_reporte=?,estado=?,reportado_por=?,cargo_reportante=?,
            area_reportante=?,lider_afa=?,area_equipo=?,responsables=?,
            fecha_inicio_analisis=?,aprobado_por=?,prioridad=?,costo_estimado=?,
            impacto_produccion=?,impacto_seguridad=?,impacto_ambiental=?,
            ultima_modificacion=CURRENT_TIMESTAMP
            WHERE codigo=?""",
               (fr,est,rp,cr,ar,la,ae,resp,fi,ap,prio,ce,ip,is_,ia,codigo))

print("Parte 4 generada correctamente")



def _tab_problema(codigo, d, tipo, es_nuevo):
    st.markdown('<div class="seccion-band">2. DESCRIPCION DEL PROBLEMA</div>', unsafe_allow_html=True)

    desc_inicial = st.text_area("1. Descripcion del problema inicial",
        value=d.get('desc_problema_inicial',''), height=100, key="dpi")

    col_corr1, col_corr2 = st.columns([1, 5])
    if col_corr1.button("✏️ Corregir", key="corr_desc"):
        desc_inicial = corregir_texto(desc_inicial)
        st.rerun()
    if col_corr2.button("🔄 Humanizar", key="hum_desc"):
        desc_inicial = humanizar_texto(desc_inicial)
        st.rerun()

    st.markdown('<div class="seccion-band">3. QUE? — Contexto (Fotos, Graficas, Flujos)</div>',
                unsafe_allow_html=True)
    que_ctx = st.text_area("Que fue lo que vio? Que tarea fallo? Que debio pasar?",
        value=d.get('que_contexto',''), height=100, key="qc")

    col_corr3, col_corr4 = st.columns([1, 5])
    if col_corr3.button("✏️ Corregir", key="corr_que"):
        que_ctx = corregir_texto(que_ctx)
        st.rerun()
    if col_corr4.button("🔄 Humanizar", key="hum_que"):
        que_ctx = humanizar_texto(que_ctx)
        st.rerun()

    _upload_imagenes_inline(codigo, 'que', es_nuevo)

    st.markdown('<div class="seccion-band">4. COMO? — Entienda como ocurre el problema</div>',
                unsafe_allow_html=True)
    como_oc = st.text_area("Como ocurrio? Como se ejecuto el trabajo?",
        value=d.get('como_ocurre',''), height=100, key="co")

    col_corr5, col_corr6 = st.columns([1, 5])
    if col_corr5.button("✏️ Corregir", key="corr_como"):
        como_oc = corregir_texto(como_oc)
        st.rerun()
    if col_corr6.button("🔄 Humanizar", key="hum_como"):
        como_oc = humanizar_texto(como_oc)
        st.rerun()

    _upload_imagenes_inline(codigo, 'como', es_nuevo)

    st.markdown('<div class="seccion-band">5. ENFOQUE DEL PROBLEMA — 5W + 2H</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    quien  = c1.text_area("Quien? (origino / detecto)", value=d.get('quien',''), height=80, key="quien")
    donde  = c2.text_area("Donde? (punto exacto del problema)", value=d.get('donde',''), height=80, key="donde")
    cuanto = c1.text_area("Cuanto? (frecuencia, extension, monto)", value=d.get('cuanto',''), height=80, key="cuanto")
    cuando = c2.text_area("Cuando? (inicio del problema)", value=d.get('cuando',''), height=80, key="cuando")
    cual   = st.text_area("Cual? (marcas, formatos, producto, materiales)", value=d.get('cual',''), height=60, key="cual")

    st.markdown('<div class="seccion-band">6. DESCRIPCION DEL PROBLEMA ENFOCADO</div>',
                unsafe_allow_html=True)
    prob_enf = st.text_area("Describa el problema enfocado (use la info del 5W+2H)",
        value=d.get('problema_enfocado',''), height=100, key="pe")

    col_corr7, col_corr8 = st.columns([1, 5])
    if col_corr7.button("✏️ Corregir", key="corr_pe"):
        prob_enf = corregir_texto(prob_enf)
        st.rerun()
    if col_corr8.button("🔄 Humanizar", key="hum_pe"):
        prob_enf = humanizar_texto(prob_enf)
        st.rerun()

    st.markdown('<div class="seccion-band">7. ACCIONES INMEDIATAS (Correccion / Contencion)</div>',
                unsafe_allow_html=True)
    _seccion_acciones_inmediatas(codigo, es_nuevo)

    if st.button("💾 Guardar Problema / 5W+2H", type="primary", key="save_prob"):
        if not es_nuevo or st.session_state.get('doc_codigo'):
            db_run("""UPDATE documentos SET
                desc_problema_inicial=?, que_contexto=?, como_ocurre=?,
                quien=?, donde=?, cuanto=?, cuando=?, cual=?,
                problema_enfocado=?, ultima_modificacion=CURRENT_TIMESTAMP
                WHERE codigo=?""",
                   (desc_inicial, que_ctx, como_oc, quien, donde, cuanto, cuando,
                    cual, prob_enf, codigo))
            st.success("✅ Datos del problema guardados.")

def _upload_imagenes_inline(codigo, seccion, es_nuevo):
    if es_nuevo and not st.session_state.get('doc_codigo'):
        st.caption("_Guarda primero los datos generales para poder subir imagenes._")
        return
    with st.expander("📷 Imagenes / Evidencias de esta seccion (" + seccion.upper() + ")", expanded=False):
        c1, c2 = st.columns([3,1])
        desc_img = c1.text_input("Descripcion / Comentario de la imagen",
                                   placeholder="Describa lo que muestra la foto...",
                                   key="desc_img_" + seccion)
        tipo_evi = c2.selectbox("Tipo de evidencia",
                                  ['FALLA','CAUSA','ACCION','VERIFICACION','REFERENCIA','OTRO'],
                                  key="tipo_evi_" + seccion)
        uploaded = st.file_uploader("Seleccionar imagen",
            type=['png','jpg','jpeg','bmp','gif'],
            key="uploader_" + seccion)
        if st.button("➕ Agregar imagen a evidencias", key="btn_img_" + seccion) and uploaded:
            img_b = uploaded.read()
            fmt = "." + uploaded.name.split('.')[-1].lower()
            desc_final = desc_img.strip() if desc_img and desc_img.strip() else ("Evidencia seccion " + seccion.upper() + ": " + uploaded.name)
            # Guardar con seccion especifica y tambien como anexo general
            db_run("""INSERT INTO evidencias
                (codigo_documento,nombre_archivo,tipo_evidencia,descripcion,imagen_blob,tamano_bytes,formato,seccion)
                VALUES(?,?,?,?,?,?,?,?)""",
                   (codigo, uploaded.name, tipo_evi, desc_final,
                    img_b, len(img_b), fmt, seccion))
            st.success("✅ Imagen '" + uploaded.name + "' agregada a evidencias (tambien visible en Anexos).")
            st.rerun()

        evis = db_query("SELECT * FROM evidencias WHERE codigo_documento=? AND seccion=? ORDER BY fecha_registro",
                        (codigo, seccion)) if not es_nuevo else []
        if evis:
            st.markdown("**" + str(len(evis)) + " imagen(es) en esta seccion:**")
            cols = st.columns(min(len(evis), 4))
            for i, evi in enumerate(evis):
                with cols[i % 4]:
                    if evi['imagen_blob']:
                        try:
                            img = Image.open(io.BytesIO(evi['imagen_blob']))
                            st.image(img, caption="Fig. " + str(i+1) + " [" + evi['tipo_evidencia'] + "] " + (evi['descripcion'] or evi['nombre_archivo'])[:40],
                                     use_container_width=True)
                        except Exception:
                            st.caption("Fig. " + str(i+1) + ": " + evi['nombre_archivo'])
                    if st.button("🗑 Eliminar", key="del_evi_" + str(evi['id'])):
                        db_run("DELETE FROM evidencias WHERE id=?", (evi['id'],))
                        st.rerun()

def _seccion_acciones_inmediatas(codigo, es_nuevo):
    if es_nuevo and not st.session_state.get('doc_codigo'):
        st.caption("_Guarda primero los datos generales._")
        return

    accs = db_query("SELECT * FROM acciones_inmediatas WHERE codigo_acr=? ORDER BY id", (codigo,))
    if accs:
        import pandas as pd
        df = pd.DataFrame([{
            "ID": a['id'], "Accion": a['accion'], "Responsable": a['responsable'],
            "Fecha": a['fecha'], "Estado": a['estado'], "Eficacia": a['eficacia']
        } for a in accs])
        st.dataframe(df.drop(columns=['ID']), use_container_width=True, hide_index=True)

    st.markdown("**Registrar nueva accion:**")
    with st.form("form_accion", clear_on_submit=True):
        accion_txt = st.text_area("Accion (*)", height=70, key="acc_txt")
        fc1, fc2, fc3, fc4 = st.columns(4)
        acc_resp  = fc1.text_input("Responsable", key="acc_resp")
        acc_fecha = fc2.date_input("Fecha", value=datetime.date.today(), key="acc_fecha")
        acc_est   = fc3.selectbox("Estado", ['PENDIENTE','EN_PROCESO','CERRADO'], key="acc_est")
        acc_efic  = fc4.selectbox("Eficacia", ['POR_VERIFICAR','EFICAZ','NO_EFICAZ'], key="acc_efic")
        c_sub, c_del = st.columns(2)
        submitted = c_sub.form_submit_button("+ AGREGAR ACCION", type="primary")
        if submitted and accion_txt.strip():
            db_run("""INSERT INTO acciones_inmediatas
                (codigo_acr,accion,responsable,fecha,estado,eficacia)
                VALUES(?,?,?,?,?,?)""",
                   (codigo, accion_txt.strip(), acc_resp, str(acc_fecha), acc_est, acc_efic))
            st.success("Accion registrada.")
            st.rerun()

    if accs:
        id_del = st.selectbox("Eliminar accion con ID:",
                              options=[0]+[a['id'] for a in accs],
                              format_func=lambda x: "Seleccionar..." if x==0 else
                              "ID " + str(x) + ": " + next((a['accion'][:50] for a in accs if a['id']==x), ''),
                              key="del_acc_id")
        if id_del and st.button("🗑 Eliminar accion seleccionada", key="del_acc_btn"):
            db_run("DELETE FROM acciones_inmediatas WHERE id=?", (id_del,))
            st.success("Accion eliminada.")
            st.rerun()

def _tab_condiciones_6m(codigo, d, es_nuevo):
    if es_nuevo and not st.session_state.get('doc_codigo'):
        st.warning("Guarda primero los datos generales.")
        return

    st.markdown('<div class="seccion-band">8. REVISION DE CONDICIONES BASICAS — 6M</div>',
                unsafe_allow_html=True)
    st.caption("Verifique cada condicion basica. Complete la Condicion Actual (Hallazgo) y marque si aplica y si existe diferencia respecto al ideal.")

    CONDICIONES_6M = {
        "MAQUINA": [
            ("Lubricacion",
             "Los componentes estan lubricados con el tipo correcto, frecuencia, cantidad y metodo de lubricacion designado."),
            ("Ajuste",
             "La tornilleria y perneria tiene el nivel adecuado de ajuste segun especificacion."),
            ("Limpieza",
             "Los componentes estan libres de contaminantes para que puedan ser inspeccionados y no haya deterioro forzado."),
            ("Confiabilidad",
             "Se cuenta con data confiable para realizar los analisis de fallas y planes de remediacion."),
            ("Operatividad",
             "El equipo esta siendo usado a la velocidad, carga, presion, etc. para la cual fue disenado. El diseno fue seguido para escribir las especificaciones o estandares de operacion y opera de esa forma."),
            ("Instalacion",
             "El equipo fue instalado bajo un riguroso seguimiento de practicas de construccion y estandares. Las condiciones de diseno de instalaciones fueron alcanzadas y se siguen."),
            ("Fabricacion",
             "El producto esta siendo fabricado y armado como lo especifica la placa o patron de diseno."),
        ],
        "MATERIAL": [
            ("Seleccion correcta de componentes",
             "Los dibujos y planos son correctos. Las especificaciones de materiales son las adecuadas de acuerdo al diseno. Cuenta con la configuracion correcta."),
            ("Materiales",
             "Se han usado los materiales correctos en cantidad y especificacion de acuerdo a la guia de proceso y especificaciones del material."),
            ("Especificacion",
             "Las especificaciones tecnicas del material cumplen con los requerimientos del proceso y estan documentadas."),
        ],
        "MANO DE OBRA": [
            ("Gente",
             "El personal cuenta con los skills tecnicos para poder realizar sus tareas. Han demostrado tener la habilidad para realizarlas."),
            ("Operador/mantenedor",
             "El operador o mantenedor ejecuta las tareas segun el procedimiento establecido, sin desviaciones que dahen el equipo o generen reprocesos."),
        ],
        "METODO": [
            ("Proceso",
             "Las principales variables de proceso (presion, temperatura, caudal, flujo) estan dentro del rango de operacion normal. El proceso incorpora elementos que permitan identificar/evitar defectos rapidamente: gestion visual, poka yoke, checklist, LUPS."),
            ("Estandares de operacion",
             "Los procesos de trabajo definidos no estan generando el problema. Estan siendo seguidos consistentemente. Check list, Procedimientos, Entrenamientos. Los pasos y su secuencia han sido definidos correctamente. El layout de operacion ayuda a que el trabajo se realice sin errores ni reprocesos. No se realizan acciones que dahen al equipo o sean innecesarias."),
            ("Diseno",
             "El diseno del equipo/proceso fue seguido para escribir las especificaciones o estandares de operacion y opera de esa forma. El layout de operacion es el adecuado."),
        ],
        "MEDICION": [
            ("Confiabilidad de datos",
             "Se cuenta con data confiable y trazable para realizar los analisis de fallas y planes de remediacion. Los instrumentos de medicion estan calibrados y dentro de rango."),
        ],
        "MEDIO AMBIENTE": [
            ("Ambientales",
             "El equipo esta siendo usado en condiciones ambientales aceptables (temperatura, humedad, polvo, vibracion, corrosion, etc.) segun especificacion del fabricante."),
        ],
    }

    ICONO_CAT = {
        "MAQUINA": "⚙️", "MATERIAL": "🔩", "MANO DE OBRA": "👷",
        "METODO": "📋", "MEDICION": "📏", "MEDIO AMBIENTE": "🌿"
    }

    conds_db = {f"{r['categoria_6m']}|{r['item']}": dict(r)
                for r in db_query("SELECT * FROM condiciones_basicas WHERE codigo_acr=?", (codigo,))}

    cambios = []
    for cat, items in CONDICIONES_6M.items():
        st.markdown("""
        <div style="background:#1e3a5f;color:white;font-weight:700;padding:8px 14px;
                    border-radius:6px;margin:14px 0 8px 0;font-size:.95rem;">
            """ + ICONO_CAT.get(cat,'') + " " + cat + """
        </div>""", unsafe_allow_html=True)

        for (item, condicion_ideal_default) in items:
            key = cat + "|" + item
            existing = conds_db.get(key, {})
            aplica_val = existing.get('aplica', 'SI')
            diferencia_val = existing.get('diferencia', 'NO')

            if aplica_val == 'SI' and diferencia_val == 'SI':
                border_color = "#dc3545"
                estado_icon = "🔴"
            elif aplica_val == 'NO':
                border_color = "#6c757d"
                estado_icon = "⚫"
            else:
                border_color = "#198754"
                estado_icon = "🟢"

            with st.expander(estado_icon + " **" + item + "**", expanded=(diferencia_val=='SI')):
                st.markdown("**📌 Condicion Ideal:**")
                ideal = st.text_area("",
                    value=existing.get('condicion_ideal', condicion_ideal_default),
                    height=90, key="ci_" + key,
                    help="Esta es la condicion que deberia existir segun el estandar.")

                st.markdown("**🔍 Condicion Actual — Hallazgo o Causa Inmediata:**")
                actual = st.text_area("",
                    value=existing.get('condicion_actual',''),
                    height=80, key="ca_" + key,
                    placeholder="Describa lo que encontro en campo...",
                    help="Describa la condicion real encontrada durante la inspeccion.")

                cr1, cr2 = st.columns(2)
                aplica = cr1.radio("¿Aplica esta condicion?",
                    ['SI','NO'],
                    index=0 if aplica_val == 'SI' else 1,
                    horizontal=True, key="ap_" + key)
                diferencia = cr2.radio("¿Existe diferencia respecto al ideal?",
                    ['NO','SI'],
                    index=0 if diferencia_val == 'NO' else 1,
                    horizontal=True, key="df_" + key)

                if diferencia == 'SI':
                    st.warning("⚠️ Se detectó diferencia. Esta condición debe incluirse en el análisis Why-Why.")

                cambios.append((cat, item, ideal, actual, aplica, diferencia, existing.get('id')))

    st.markdown("---")
    col_save, col_info = st.columns([1, 3])
    if col_save.button("💾 Guardar Condiciones 6M", type="primary", key="save_6m", use_container_width=True):
        for cat, item, ideal, actual, aplica, diferencia, id_exist in cambios:
            if id_exist:
                db_run("""UPDATE condiciones_basicas SET condicion_ideal=?,condicion_actual=?,aplica=?,diferencia=?
                    WHERE id=?""", (ideal, actual, aplica, diferencia, id_exist))
            else:
                db_run("""INSERT INTO condiciones_basicas
                    (codigo_acr,categoria_6m,item,condicion_ideal,condicion_actual,aplica,diferencia)
                    VALUES(?,?,?,?,?,?,?)""", (codigo, cat, item, ideal, actual, aplica, diferencia))
        st.success("✅ Condiciones 6M guardadas correctamente.")
        st.rerun()

    conds_actuales = db_query("SELECT * FROM condiciones_basicas WHERE codigo_acr=? AND diferencia='SI'", (codigo,))
    if conds_actuales:
        col_info.info("⚠️ **" + str(len(conds_actuales)) + " condicion(es) con diferencia detectada** — deben incluirse en el análisis Why-Why.")

def _tab_why_why(codigo, es_nuevo):
    if es_nuevo and not st.session_state.get('doc_codigo'):
        st.warning("Guarda primero los datos generales.")
        return

    st.markdown('<div class="seccion-band">ANALISIS WHY-WHY — Tabla Interactiva</div>',
                unsafe_allow_html=True)
    st.caption("Complete cada rama de analisis. Las flechas → indican la secuencia causal horizontal.")

    whys = db_query("SELECT * FROM why_why WHERE codigo_documento=? ORDER BY CAST(rama_id AS INTEGER)",
                    (codigo,))

    PRIO_COLS = {'BAJA':'🟢','MEDIA':'🟡','ALTA':'🟠','CRITICA':'🔴'}

    for i, w in enumerate(whys):
        # Normalizar prioridad: mayúsculas, strip, default seguro
        prio_raw = (w['prioridad'] or 'MEDIA').strip().upper()
        if prio_raw not in ['BAJA','MEDIA','ALTA','CRITICA']:
            prio_raw = 'MEDIA'

        with st.expander(
            "**Rama " + str(w['rama_id']) + "** " + PRIO_COLS.get(prio_raw,'⚪') +
            " | Def: " + ((w['definicion'] or '—')[:50]) + "...",
            expanded=False
        ):
            st.markdown("**Cadena causal:**")
            chain_cols = st.columns([3,0.3,2,0.3,2,0.3,2,0.3,2,0.3,2,0.3,3])
            chain_cols[0].markdown("**Definicion**<br><small>" + (w['definicion'] or '—') + "</small>",
                                   unsafe_allow_html=True)
            for ci, (pq, label) in enumerate([(w['pq1'],'PQ1'),(w['pq2'],'PQ2'),(w['pq3'],'PQ3'),
                                               (w['pq4'],'PQ4'),(w['pq5'],'PQ5'),(w['causa_raiz'],'Causa')]):
                chain_cols[ci*2+1].markdown('<div style="color:#1e60a8;font-size:1.5rem;text-align:center">→</div>',
                                            unsafe_allow_html=True)
                chain_cols[ci*2+2].markdown("**" + label + "**<br><small>" + (pq or '—') + "</small>",
                                            unsafe_allow_html=True)

            st.markdown("---")
            wc1, wc2 = st.columns(2)
            new_def = wc1.text_area("Definicion del problema", value=w['definicion'] or '', height=60, key="wdef_" + str(w['id']))
            new_pq1 = wc2.text_area("Por que 1?", value=w['pq1'] or '', height=60, key="wp1_" + str(w['id']))
            wc3, wc4 = st.columns(2)
            new_pq2 = wc3.text_area("Por que 2?", value=w['pq2'] or '', height=60, key="wp2_" + str(w['id']))
            new_pq3 = wc4.text_area("Por que 3?", value=w['pq3'] or '', height=60, key="wp3_" + str(w['id']))
            wc5, wc6 = st.columns(2)
            new_pq4 = wc5.text_area("Por que 4?", value=w['pq4'] or '', height=60, key="wp4_" + str(w['id']))
            new_pq5 = wc6.text_area("Por que 5?", value=w['pq5'] or '', height=60, key="wp5_" + str(w['id']))
            wc7, wc8 = st.columns(2)
            new_cr   = wc7.text_area("Causa Raiz", value=w['causa_raiz'] or '', height=60, key="wcr_" + str(w['id']))
            new_acc  = wc8.text_area("Accion sobre Causa Raiz", value=w['accion_causa_raiz'] or '', height=60, key="wacc_" + str(w['id']))
            wc9, wc10, wc11 = st.columns(3)
            new_resp = wc9.text_input("Responsable", value=w['responsable'] or '', key="wresp_" + str(w['id']))
            # Normalizar prioridad del DB para el selectbox
            _prio_db = (w['prioridad'] or 'MEDIA').strip().upper()
            if _prio_db not in ['BAJA','MEDIA','ALTA','CRITICA']:
                _prio_db = 'MEDIA'
            new_prio = wc10.selectbox("Prioridad", ['BAJA','MEDIA','ALTA','CRITICA'],
                index=['BAJA','MEDIA','ALTA','CRITICA'].index(_prio_db),
                key="wprio_" + str(w['id']))
            new_fech = wc11.date_input("Fecha",
                value=datetime.date.fromisoformat(w['fecha']) if w['fecha'] else datetime.date.today(),
                key="wfech_" + str(w['id']))

            col_wc1, col_wc2 = st.columns([1, 1])
            if col_wc1.button("✏️ Corregir Ortografia de Rama", key="corr_w_" + str(w['id'])):
                new_def = corregir_texto(new_def)
                new_pq1 = corregir_texto(new_pq1)
                new_pq2 = corregir_texto(new_pq2)
                new_pq3 = corregir_texto(new_pq3)
                new_pq4 = corregir_texto(new_pq4)
                new_pq5 = corregir_texto(new_pq5)
                new_cr = corregir_texto(new_cr)
                new_acc = corregir_texto(new_acc)
                db_run("""UPDATE why_why SET definicion=?,pq1=?,pq2=?,pq3=?,pq4=?,pq5=?,
                    causa_raiz=?,accion_causa_raiz=?,responsable=?,prioridad=?,fecha=?
                    WHERE id=?""",
                       (new_def,new_pq1,new_pq2,new_pq3,new_pq4,new_pq5,
                        new_cr,new_acc,new_resp,new_prio,str(new_fech),w['id']))
                st.success("✅ Ortografia corregida y guardada.")
                st.rerun()

            ba, bb = st.columns(2)
            if ba.button("💾 Actualizar Rama", key="wupd_" + str(w['id'])):
                db_run("""UPDATE why_why SET definicion=?,pq1=?,pq2=?,pq3=?,pq4=?,pq5=?,
                    causa_raiz=?,accion_causa_raiz=?,responsable=?,prioridad=?,fecha=?
                    WHERE id=?""",
                       (new_def,new_pq1,new_pq2,new_pq3,new_pq4,new_pq5,
                        new_cr,new_acc,new_resp,new_prio,str(new_fech),w['id']))
                st.success("Rama " + w['rama_id'] + " actualizada.")
                st.rerun()
            if bb.button("🗑 Eliminar Rama", key="wdel_" + str(w['id'])):
                db_run("DELETE FROM why_why WHERE id=?", (w['id'],))
                st.success("Rama eliminada.")
                st.rerun()

    st.markdown("---")
    st.markdown("**+ Nueva Rama de Analisis:**")
    with st.form("form_new_rama", clear_on_submit=True):
        rama_num = len(whys) + 1
        rc1, rc2 = st.columns(2)
        nr_def = rc1.text_area("Definicion del problema *", height=60)
        nr_pq1 = rc2.text_area("Por que 1?", height=60)
        rc3, rc4 = st.columns(2)
        nr_pq2 = rc3.text_area("Por que 2?", height=60)
        nr_pq3 = rc4.text_area("Por que 3?", height=60)
        rc5, rc6 = st.columns(2)
        nr_pq4 = rc5.text_area("Por que 4?", height=60)
        nr_pq5 = rc6.text_area("Por que 5?", height=60)
        rc7, rc8 = st.columns(2)
        nr_cr  = rc7.text_area("Causa Raiz", height=60)
        nr_acc = rc8.text_area("Accion sobre Causa Raiz", height=60)
        rc9, rc10, rc11 = st.columns(3)
        nr_resp = rc9.text_input("Responsable")
        nr_prio = rc10.selectbox("Prioridad", ['BAJA','MEDIA','ALTA','CRITICA'], index=1)
        # Asegurar que la prioridad se guarde normalizada
        nr_prio = (nr_prio or 'MEDIA').strip().upper()
        if nr_prio not in ['BAJA','MEDIA','ALTA','CRITICA']:
            nr_prio = 'MEDIA' 
        nr_fech = rc11.date_input("Fecha", value=datetime.date.today())
        if st.form_submit_button("+ AGREGAR RAMA", type="primary"):
            if nr_def.strip():
                db_run("""INSERT INTO why_why
                    (codigo_documento,rama_id,definicion,pq1,pq2,pq3,pq4,pq5,
                     causa_raiz,accion_causa_raiz,responsable,prioridad,fecha)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (codigo, str(rama_num), nr_def, nr_pq1, nr_pq2, nr_pq3, nr_pq4, nr_pq5,
                        nr_cr, nr_acc, nr_resp, nr_prio, str(nr_fech)))
                st.success("Rama " + str(rama_num) + " agregada.")
                st.rerun()
            else:
                st.error("La definicion del problema es obligatoria.")

def _tab_cierre(codigo, d, es_nuevo):
    st.markdown('<div class="seccion-band">CIERRE Y VERIFICACION</div>', unsafe_allow_html=True)

    causa_id   = st.text_area("Causa Raiz Identificada",
        value=d.get('causa_raiz_identificada',''), height=80, key="crid")
    verif      = st.text_area("Verificacion de la Causa",
        value=d.get('verificacion_causa',''), height=80, key="vc")
    evidencia  = st.text_area("Evidencia de Causa",
        value=d.get('evidencia_causa',''), height=80, key="ec")
    obs_cierre = st.text_area("Observaciones de Cierre",
        value=d.get('observaciones_cierre',''), height=80, key="oc")
    fecha_cierre = st.date_input("Fecha de Cierre",
        value=datetime.date.fromisoformat(d['fecha_cierre']) if d.get('fecha_cierre') else datetime.date.today(),
        key="fc_cierre")

    col_c1, col_c2 = st.columns([1, 5])
    if col_c1.button("✏️ Corregir Todo Cierre", key="corr_cierre"):
        causa_id = corregir_texto(causa_id)
        verif = corregir_texto(verif)
        evidencia = corregir_texto(evidencia)
        obs_cierre = corregir_texto(obs_cierre)
        st.rerun()

    if st.button("💾 Guardar Cierre", type="primary", key="save_cierre"):
        if not es_nuevo or st.session_state.get('doc_codigo'):
            db_run("""UPDATE documentos SET
                causa_raiz_identificada=?,verificacion_causa=?,evidencia_causa=?,
                observaciones_cierre=?,fecha_cierre=?,ultima_modificacion=CURRENT_TIMESTAMP
                WHERE codigo=?""",
                   (causa_id, verif, evidencia, obs_cierre, str(fecha_cierre), codigo))
            st.success("✅ Cierre guardado correctamente.")

def _tab_anexos(codigo, es_nuevo):
    st.markdown('<div class="seccion-band">ANEXOS — Evidencias Fotograficas y Documentos</div>',
                unsafe_allow_html=True)
    if es_nuevo and not st.session_state.get('doc_codigo'):
        st.warning("Guarda primero los datos generales.")
        return

    # ── FORMULARIO PARA AGREGAR NUEVA EVIDENCIA ──
    with st.form("form_anx", clear_on_submit=True):
        st.markdown("**📎 Agregar nueva evidencia al documento**")
        ac1, ac2 = st.columns([3,1])
        desc_anx = ac1.text_input("Descripcion / Comentario de la evidencia",
                                    placeholder="Ej: Foto del rodamiento con desgaste visible en pista interna")
        tipo_anx = ac2.selectbox("Tipo de evidencia",
                                   ['FALLA','CAUSA','ACCION','VERIFICACION','REFERENCIA','SESION','OTRO'])
        uploaded_anx = st.file_uploader("Seleccionar archivo (imagen o PDF)",
            type=['png','jpg','jpeg','bmp','gif','pdf'],
            help="Suba fotos del equipo, diagramas, procedimientos, o cualquier documento de soporte")
        if st.form_submit_button("➕ Agregar Evidencia", type="primary"):
            if uploaded_anx:
                img_b = uploaded_anx.read()
                fmt = "." + uploaded_anx.name.split('.')[-1].lower()
                # Usar descripcion proporcionada, o generar una automatica
                desc_final = desc_anx.strip() if desc_anx and desc_anx.strip() else ("Evidencia: " + uploaded_anx.name)
                db_run("""INSERT INTO evidencias
                    (codigo_documento,nombre_archivo,tipo_evidencia,descripcion,imagen_blob,tamano_bytes,formato,seccion)
                    VALUES(?,?,?,?,?,?,?,?)""",
                       (codigo, uploaded_anx.name, tipo_anx, desc_final,
                        img_b, len(img_b), fmt, 'GENERAL'))
                st.success("✅ Evidencia '" + uploaded_anx.name + "' agregada con descripcion.")
                st.rerun()
            else:
                st.warning("⚠️ Seleccione un archivo primero.")

    # ── LISTADO DE EVIDENCIAS EXISTENTES ──
    evis = db_query("SELECT * FROM evidencias WHERE codigo_documento=? ORDER BY fecha_registro", (codigo,))
    if evis:
        st.markdown("---")
        st.markdown("### 📷 Evidencias registradas (" + str(len(evis)) + ")")

        for i, evi in enumerate(evis):
            with st.container():
                col_img, col_info = st.columns([2, 3])

                with col_img:
                    if evi['imagen_blob'] and evi['formato'] in ['.jpg','.jpeg','.png','.bmp','.gif']:
                        try:
                            img = Image.open(io.BytesIO(evi['imagen_blob']))
                            st.image(img, use_container_width=True,
                                     caption="Fig. " + str(i+1))
                        except Exception:
                            st.info("📷 Imagen no disponible")
                    else:
                        st.info("📄 " + evi['nombre_archivo'] + " (PDF/Documento)")

                with col_info:
                    st.markdown("**Figura " + str(i+1) + "** | Tipo: `" + evi['tipo_evidencia'] + "`")

                    # Campo editable para la descripcion
                    nueva_desc = st.text_area("Descripcion / Comentario:",
                        value=evi['descripcion'] or evi['nombre_archivo'],
                        height=80,
                        key="desc_evi_" + str(evi['id']))

                    col_upd, col_del = st.columns(2)
                    if col_upd.button("💾 Actualizar descripcion", key="upd_evi_" + str(evi['id'])):
                        db_run("UPDATE evidencias SET descripcion=? WHERE id=?",
                               (nueva_desc.strip(), evi['id']))
                        st.success("✅ Descripcion actualizada.")
                        st.rerun()

                    if col_del.button("🗑 Eliminar", key="del_anx_" + str(evi['id'])):
                        db_run("DELETE FROM evidencias WHERE id=?", (evi['id'],))
                        st.success("🗑 Evidencia eliminada.")
                        st.rerun()

                st.markdown("---")
    else:
        st.info("📭 No hay evidencias registradas aun. Use el formulario de arriba para agregar fotos o documentos.")

print("Parte 5 generada correctamente")



# ── Pagina: Configuracion Empresa ─────────────────────────────────────────────
def page_config_empresa():
    show_header()
    st.markdown("## ⚙️ Configuracion de Empresa")
    st.markdown("Configure el encabezado, logo y pie de pagina que aparecera en todos los PDFs exportados.")

    cfg = get_empresa_cfg()

    with st.form("form_empresa"):
        st.markdown("**Datos Generales**")
        fc1, fc2 = st.columns(2)
        nombre_emp = fc1.text_input("Nombre de Empresa *", value=cfg.get('nombre_empresa',''))
        direccion  = fc2.text_input("Direccion", value=cfg.get('direccion',''))
        fc3, fc4 = st.columns(2)
        telefono   = fc3.text_input("Telefono", value=cfg.get('telefono',''))
        correo     = fc4.text_input("Correo", value=cfg.get('correo',''))
        fc5, fc6 = st.columns(2)
        gerente    = fc5.text_input("Gerente de Planta", value=cfg.get('gerente_planta',''))
        jefe_mant  = fc6.text_input("Jefe de Mantenimiento", value=cfg.get('jefe_mantenimiento',''))

        st.markdown("**Logo de la Empresa** (se muestra en el encabezado del PDF)")
        logo_file = st.file_uploader("Seleccionar logo (PNG/JPG recomendado, fondo transparente)",
                                     type=['png','jpg','jpeg','bmp'])
        if cfg.get('logo_blob'):
            try:
                st.image(Image.open(io.BytesIO(cfg['logo_blob'])), width=200,
                         caption="Logo actual")
            except Exception:
                st.caption("Logo actual (no se puede previsualizar)")

        st.markdown("**Texto de Encabezado** (aparece debajo del logo en cada pagina del PDF)")
        texto_enc = st.text_area("Encabezado personalizado",
            value=cfg.get('texto_encabezado','SISTEMA DE GESTION DE MANTENIMIENTO\nDEPARTAMENTO DE MANTENIMIENTO E INGENIERIA'),
            height=80)

        st.markdown("**Texto de Pie de Pagina** (aparece al final de cada pagina del PDF)")
        texto_pie = st.text_area("Pie de pagina personalizado",
            value=cfg.get('texto_pie_pagina',
                          'Documento Controlado — Prohibida su reproduccion sin autorizacion | '
                          'Normativa: ISO 9001 / ISO 14224 / TPM / RCM'),
            height=80)

        submitted = st.form_submit_button("💾 GUARDAR CONFIGURACION", type="primary")

    if submitted:
        logo_b = None
        if logo_file:
            logo_b = logo_file.read()
        elif cfg.get('logo_blob'):
            logo_b = cfg['logo_blob']

        if cfg.get('id'):
            db_run("""UPDATE configuracion_empresa SET
                nombre_empresa=?,direccion=?,telefono=?,correo=?,
                gerente_planta=?,jefe_mantenimiento=?,logo_blob=?,
                texto_encabezado=?,texto_pie_pagina=?
                WHERE id=?""",
                   (nombre_emp,direccion,telefono,correo,gerente,jefe_mant,
                    logo_b,texto_enc,texto_pie,cfg['id']))
        else:
            db_run("""INSERT INTO configuracion_empresa
                (nombre_empresa,direccion,telefono,correo,gerente_planta,
                 jefe_mantenimiento,logo_blob,texto_encabezado,texto_pie_pagina)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                   (nombre_emp,direccion,telefono,correo,gerente,jefe_mant,
                    logo_b,texto_enc,texto_pie))
        st.success("✅ Configuracion guardada. Los cambios se aplicaran en los proximos PDFs.")
        st.rerun()

# ── Pagina: Configuracion IA ──────────────────────────────────────────────────
def page_config_ia():
    show_header()
    st.markdown("## 🤖 Configuracion de Inteligencia Artificial")
    st.markdown("Configure la API de Gemini y los parametros de generacion de texto.")

    ia_cfg = get_ia_cfg()
    # Asegurar que el modelo guardado sea valido
    modelo_guardado = ia_cfg.get('modelo', 'gemini-3.5-flash')
    modelo_guardado = _mapear_modelo_a_v3(modelo_guardado)
    if modelo_guardado != ia_cfg.get('modelo', ''):
        ia_cfg['modelo'] = modelo_guardado
        db_run("UPDATE config_ia SET modelo=? WHERE id=?", (modelo_guardado, ia_cfg['id']))

    with st.form("form_ia"):
        st.markdown("**API Key de Gemini**")
        api_key = st.text_input("API Key de Gemini *", 
            value=ia_cfg.get('api_key',''),
            type="password",
            help="Obtenga su API Key en https://aistudio.google.com/app/apikey")

        st.markdown("**Parametros del Modelo**")
        c1, c2, c3 = st.columns(3)

        # Lista de modelos disponibles con indicador de tier
        opciones_modelo = [
            'gemini-3.5-flash',
            'gemini-3.1-flash-lite',
            'gemini-3.1-pro',
            'gemini-2.5-flash',
            'gemini-2.5-flash-lite',
            'gemini-2.5-pro',
            'gemini-2.0-flash',
            'gemini-2.0-pro',
            'gemini-1.5-flash',
            'gemini-1.5-pro',
        ]
        modelo_idx = 0
        if modelo_guardado in opciones_modelo:
            modelo_idx = opciones_modelo.index(modelo_guardado)

        modelo = c1.selectbox("Modelo Gemini", opciones_modelo, index=modelo_idx)

        temperatura = c2.slider("Temperatura (creatividad)", 0.0, 1.0, 
            float(ia_cfg.get('temperatura',0.3)), 0.1,
            help="0 = muy preciso, 1 = muy creativo")
        max_tokens = c3.number_input("Max Tokens", 512, 8192,
            int(ia_cfg.get('max_tokens',4096)), 512,
            help="Limite de tokens por respuesta")

        st.markdown("**Estilo de Redaccion**")
        c4, c5, c6 = st.columns(3)
        estilo = c4.selectbox("Estilo de redaccion",
            ['tecnico_profesional', 'academico', 'ejecutivo', 'conversacional'],
            index=['tecnico_profesional', 'academico', 'ejecutivo', 'conversacional'].index(
                ia_cfg.get('estilo_redaccion','tecnico_profesional')) if ia_cfg.get('estilo_redaccion') in ['tecnico_profesional', 'academico', 'ejecutivo', 'conversacional'] else 0)
        detalle = c5.selectbox("Nivel de detalle",
            ['resumido', 'estandar', 'detallado', 'exhaustivo'],
            index=['resumido', 'estandar', 'detallado', 'exhaustivo'].index(
                ia_cfg.get('nivel_detalle','detallado')) if ia_cfg.get('nivel_detalle') in ['resumido', 'estandar', 'detallado', 'exhaustivo'] else 2)
        idioma = c6.selectbox("Idioma de salida",
            ['es', 'en'],
            index=0 if ia_cfg.get('idioma','es') == 'es' else 1)

        st.markdown("**Opciones de Procesamiento**")
        c7, c8, c9 = st.columns(3)
        activar_correccion = c7.checkbox("Activar correccion ortografica automatica",
            value=bool(ia_cfg.get('activar_correccion',1)))
        activar_humanizar = c8.checkbox("Activar humanizacion de textos IA",
            value=bool(ia_cfg.get('activar_humanizar',1)))
        fallback_automatico = c9.checkbox("Activar fallback automatico a modelos gratuitos",
            value=bool(ia_cfg.get('fallback_automatico',1)),
            help="Si el modelo seleccionado agota cuota, el sistema cambiara automaticamente a un modelo gratuito")

        st.markdown("**Prompt Personalizado (opcional)**")
        prompt_personalizado = st.text_area("Instrucciones adicionales para la IA",
            value=ia_cfg.get('prompt_personalizado',''),
            height=100,
            help="Agregue instrucciones especificas que la IA debe seguir al generar documentos")

        submitted = st.form_submit_button("💾 GUARDAR CONFIGURACION IA", type="primary")

    if submitted:
        save_ia_cfg({
            'api_key': api_key,
            'modelo': modelo,
            'temperatura': temperatura,
            'max_tokens': max_tokens,
            'idioma': idioma,
            'estilo_redaccion': estilo,
            'nivel_detalle': detalle,
            'activar_correccion': 1 if activar_correccion else 0,
            'activar_humanizar': 1 if activar_humanizar else 0,
            'fallback_automatico': 1 if fallback_automatico else 0,
            'prompt_personalizado': prompt_personalizado
        })
        st.success("✅ Configuracion de IA guardada correctamente.")
        st.rerun()

    # Probar conexion
    st.markdown("---")
    col_test1, col_test2 = st.columns([1, 2])
    with col_test1:
        if st.button("🧪 Probar Conexion con Gemini", type="secondary"):
            if not api_key:
                st.error("❌ Ingrese una API Key primero.")
            else:
                with st.spinner("Probando conexion con cadena de fallback..."):
                    gemini = GeminiEngine(api_key, modelo)
                    ok, msg = gemini.probar_conexion()
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

    with col_test2:
        st.markdown("""
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px;font-size:.82rem;">
            <b>📋 Cadena de Fallback Automatico:</b><br>
            1️⃣ <code>gemini-3.5-flash</code> (Free Tier - Default)<br>
            2️⃣ <code>gemini-3.1-flash-lite</code> (Free Tier - Alto throughput)<br>
            3️⃣ <code>gemini-2.5-flash</code> (Legacy)<br>
            4️⃣ <code>gemini-2.5-flash-lite</code> (Legacy Budget)
        </div>
        """, unsafe_allow_html=True)

# ── Pagina: Listado de documentos ─────────────────────────────────────────────
def page_listado():
    show_header()
    st.markdown("## 📋 Todos los Documentos")

    fc1, fc2, fc3 = st.columns(3)
    f_tipo   = fc1.selectbox("Tipo", ['TODOS','ACR','AFA'])
    f_estado = fc2.selectbox("Estado", ['TODOS','BORRADOR','EN_ANALISIS','REVISADO','APROBADO','RECHAZADO','CERRADO'])
    f_busq   = fc3.text_input("Buscar (codigo, descripcion, responsable)...")

    sql = "SELECT * FROM documentos WHERE es_historico=0 AND 1=1"
    params = []
    if f_tipo != 'TODOS':
        sql += " AND tipo_documento=?"; params.append(f_tipo)
    if f_estado != 'TODOS':
        sql += " AND estado=?"; params.append(f_estado)
    if f_busq:
        sql += " AND (codigo LIKE ? OR desc_problema_inicial LIKE ? OR responsables LIKE ? OR reportado_por LIKE ?)"
        b = "%" + f_busq + "%"
        params.extend([b,b,b,b])
    sql += " ORDER BY fecha_registro DESC"
    docs = db_query(sql, tuple(params))

    st.markdown("**" + str(len(docs)) + " documento(s) encontrado(s)**")

    if not docs:
        st.info("No hay documentos que coincidan con los filtros.")
        return

    import pandas as pd
    tabla_data = []
    for d in docs:
        tabla_data.append({
            "Codigo": d['codigo'],
            "Tipo": d['tipo_documento'],
            "Estado": d['estado'],
            "Prioridad": d['prioridad'],
            "Reportado por": d['reportado_por'],
            "Area": d['area_equipo'] or '—',
            "Fecha": d['fecha_reporte'],
            "Descripcion": (d['desc_problema_inicial'] or '')[:60]
        })
    st.dataframe(pd.DataFrame(tabla_data), use_container_width=True, hide_index=True)

    st.markdown("---")
    sel_cod = st.selectbox("Seleccionar documento para acciones:",
                           options=['']+[d['codigo'] for d in docs],
                           format_func=lambda x: x if x else "— Seleccionar —")
    if sel_cod:
        ba, bb, bc = st.columns(3)
        if ba.button("✏️ Editar", type="primary"):
            d_sel = next(d for d in docs if d['codigo']==sel_cod)
            st.session_state['pagina'] = 'form'
            st.session_state['doc_codigo'] = sel_cod
            st.session_state['doc_tipo'] = d_sel['tipo_documento']
            st.rerun()
        if bb.button("📄 Exportar PDF"):
            d_sel = next(d for d in docs if d['codigo']==sel_cod)
            with st.spinner("Generando PDF..."):
                pdf_b = exportar_pdf(sel_cod, d_sel['tipo_documento']=='ACR')
            bb.download_button("⬇️ Descargar", pdf_b,
                               file_name=sel_cod + ".pdf",
                               mime="application/pdf",
                               key="dl_list")
        if bc.button("🗑 Eliminar"):
            db_run("DELETE FROM documentos WHERE codigo=?", (sel_cod,))
            st.success("Documento " + sel_cod + " eliminado.")
            st.rerun()

# ── Pagina: Historico ─────────────────────────────────────────────────────────
def page_historico():
    show_header()
    st.markdown("## 📚 Historico de Documentos")
    st.markdown("Documentos archivados para referencia y analisis de problemas recurrentes.")

    stats = obtener_estadisticas_historico()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📄 Documentos Activos", stats['total_activos'])
    c2.metric("📚 Documentos Archivados", stats['total_historico'])
    c3.metric("✅ Acciones Completadas", stats['acciones_cerradas'])
    c4.metric("📊 Total Acciones", stats['acciones_totales'])

    st.markdown("---")
    st.markdown("### 🔍 Buscar en Historico")

    fh1, fh2 = st.columns([1, 3])
    f_tipo_hist = fh1.selectbox("Tipo", ['TODOS','ACR','AFA'], key="hist_tipo")
    f_busq_hist = fh2.text_input("Buscar (codigo, motivo, descripcion)...", key="hist_busq")

    historicos = obtener_historico(f_tipo_hist, f_busq_hist)

    st.markdown("**" + str(len(historicos)) + " documento(s) en historico**")

    if not historicos:
        st.info("No hay documentos archivados. Los documentos cerrados/aprobados pueden archivarse desde el Dashboard.")
        return

    for h in historicos:
        datos = json.loads(h['datos_json'])
        with st.expander(
            "📚 **" + h['codigo_original'] + "** → " + h['codigo_historico'] + " | " + h['tipo_documento'] + " | " +
            "Archivado: " + h['fecha_archivado'][:10] + " | Estado final: " + h['estado_final'],
            expanded=False
        ):
            c1, c2, c3 = st.columns(3)
            c1.write("**Motivo:** " + h['motivo_archivado'])
            c1.write("**Acciones completadas:** " + str(h['acciones_completadas']) + "/" + str(h['acciones_totales']))
            c2.write("**Descripcion:** " + (datos.get('desc_problema_inicial',''))[:100] + "...")
            c2.write("**Area:** " + datos.get('area_equipo','—'))
            c3.write("**Causa raiz:** " + (datos.get('causa_raiz_identificada',''))[:80] + "...")

            ba, bb = st.columns(2)
            if ba.button("🔄 Restaurar como Nuevo Documento", key="rest_" + h['codigo_historico']):
                nuevo_cod = restaurar_documento(h['codigo_historico'])
                if nuevo_cod:
                    st.success("✅ Documento restaurado como `" + nuevo_cod + "`. Puede editarlo en el formulario.")
                    st.session_state['pagina'] = 'form'
                    st.session_state['doc_codigo'] = nuevo_cod
                    st.session_state['doc_tipo'] = h['tipo_documento']
                    st.rerun()
            if bb.button("📄 Ver Datos Completos", key="ver_" + h['codigo_historico']):
                st.json(datos)

# ── Pagina: Plan de Accion ─────────────────────────────────────────────────────
def page_plan_accion():
    show_header()
    st.markdown("## 📊 Plan de Accion — Control y Seguimiento Gerencial")
    st.caption("Gestion centralizada de todas las acciones ACR/AFA. Vista ejecutiva para Gerencias de Produccion, Mantenimiento y SHES.")

    today = datetime.date.today().isoformat()

    all_acc = db_query("""
        SELECT ai.*, d.tipo_documento, d.area_equipo, d.prioridad as doc_prioridad,
               d.estado as doc_estado
        FROM acciones_inmediatas ai
        JOIN documentos d ON ai.codigo_acr = d.codigo
        WHERE d.es_historico=0
        ORDER BY ai.fecha ASC
    """)
    all_why = db_query("""
        SELECT ww.*, d.tipo_documento, d.area_equipo, d.prioridad as doc_prioridad,
               d.estado as doc_estado
        FROM why_why ww
        JOIN documentos d ON ww.codigo_documento = d.codigo
        WHERE d.es_historico=0 AND ww.accion_causa_raiz IS NOT NULL AND ww.accion_causa_raiz != ''
        ORDER BY ww.fecha ASC
    """)

    todas_acc = []
    for a in all_acc:
        todas_acc.append({
            'origen': a['codigo_acr'],
            'tipo_doc': a['tipo_documento'],
            'tipo_accion': 'Inmediata / Contencion',
            'accion': a['accion'],
            'responsable': a['responsable'] or '—',
            'fecha': a['fecha'] or '',
            'estado': a['estado'] or 'PENDIENTE',
            'eficacia': a['eficacia'] or 'POR_VERIFICAR',
            'area': a['area_equipo'] or '—',
            'prioridad': a['doc_prioridad'] or 'MEDIA',
            'id_ref': "AI-" + str(a['id']),
        })
    for w in all_why:
        todas_acc.append({
            'origen': w['codigo_documento'],
            'tipo_doc': w['tipo_documento'],
            'tipo_accion': 'Causa Raiz / Why-Why',
            'accion': w['accion_causa_raiz'],
            'responsable': w['responsable'] or '—',
            'fecha': w['fecha'] or '',
            'estado': (w['estatus'] or 'PENDIENTE').strip().upper() if (w['estatus'] or 'PENDIENTE').strip().upper() in ['PENDIENTE','EN_PROCESO','CERRADO'] else 'PENDIENTE',
            'eficacia': '—',
            'area': w['area_equipo'] or '—',
            'prioridad': (w['prioridad'] or 'MEDIA').strip().upper() if (w['prioridad'] or 'MEDIA').strip().upper() in ['BAJA','MEDIA','ALTA','CRITICA'] else 'MEDIA',
            'id_ref': "WW-" + str(w['id']),
        })

    total    = len(todas_acc)
    pend     = sum(1 for a in todas_acc if a['estado'] == 'PENDIENTE')
    en_proc  = sum(1 for a in todas_acc if a['estado'] == 'EN_PROCESO')
    cerradas = sum(1 for a in todas_acc if a['estado'] == 'CERRADO')
    vencidas = sum(1 for a in todas_acc
                   if a['fecha'] and a['fecha'] < today and a['estado'] not in ('CERRADO',))
    porc_avance = round(cerradas / total * 100, 1) if total > 0 else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.markdown("""<div class="kpi-card kpi-total">
        <div class="kpi-label">Total Acciones</div>
        <div class="kpi-num">""" + str(total) + """</div></div>""", unsafe_allow_html=True)
    k2.markdown("""<div class="kpi-card kpi-pend">
        <div class="kpi-label">Pendientes</div>
        <div class="kpi-num">""" + str(pend) + """</div></div>""", unsafe_allow_html=True)
    k3.markdown("""<div class="kpi-card kpi-proc">
        <div class="kpi-label">En Proceso</div>
        <div class="kpi-num">""" + str(en_proc) + """</div></div>""", unsafe_allow_html=True)
    k4.markdown("""<div class="kpi-card kpi-cerr">
        <div class="kpi-label">Cerradas</div>
        <div class="kpi-num">""" + str(cerradas) + """</div></div>""", unsafe_allow_html=True)
    k5.markdown("""<div class="kpi-card kpi-venc">
        <div class="kpi-label">Vencidas</div>
        <div class="kpi-num">""" + str(vencidas) + """</div></div>""", unsafe_allow_html=True)

    st.markdown("")
    st.markdown("**Avance global de cierre: " + str(porc_avance) + "%**")
    st.progress(porc_avance / 100)

    if total == 0:
        st.info("No hay acciones registradas en el sistema aun.")
        return

    st.markdown("---")
    st.markdown("### 🔍 Filtros")
    ff1, ff2, ff3, ff4 = st.columns(4)
    f_estado_pa = ff1.selectbox("Estado", ['TODOS','PENDIENTE','EN_PROCESO','CERRADO'], key="pa_est")
    f_tipo_pa   = ff2.selectbox("Tipo documento", ['TODOS','ACR','AFA'], key="pa_tipo")
    f_prio_pa   = ff3.selectbox("Prioridad", ['TODAS','CRITICA','ALTA','MEDIA','BAJA'], key="pa_prio")
    f_venc_pa   = ff4.checkbox("Solo vencidas", key="pa_venc")

    acc_filtradas = todas_acc
    if f_estado_pa != 'TODOS':
        acc_filtradas = [a for a in acc_filtradas if a['estado'] == f_estado_pa]
    if f_tipo_pa != 'TODOS':
        acc_filtradas = [a for a in acc_filtradas if a['tipo_doc'] == f_tipo_pa]
    if f_prio_pa != 'TODAS':
        acc_filtradas = [a for a in acc_filtradas if a['prioridad'] == f_prio_pa]
    if f_venc_pa:
        acc_filtradas = [a for a in acc_filtradas
                        if a['fecha'] and a['fecha'] < today and a['estado'] != 'CERRADO']

    st.markdown("**" + str(len(acc_filtradas)) + " accion(es) mostrada(s)**")

    st.markdown("---")
    st.markdown("### 📋 Tabla de Acciones")

    ESTADO_ICON = {'PENDIENTE':'🔴','EN_PROCESO':'🟡','CERRADO':'🟢'}
    PRIO_ICON   = {'CRITICA':'🔴','ALTA':'🟠','MEDIA':'🟡','BAJA':'🟢'}

    import pandas as pd
    df_acc = pd.DataFrame([{
        "Ref":          a['id_ref'],
        "Documento":    a['origen'],
        "Tipo Doc":     a['tipo_doc'],
        "Tipo Accion":  a['tipo_accion'],
        "Accion":       a['accion'][:80] + ('...' if len(a['accion'])>80 else ''),
        "Responsable":  a['responsable'],
        "Fecha Limite": a['fecha'],
        "Estado":       ESTADO_ICON.get(a['estado'],'⚪') + " " + a['estado'],
        "Prioridad":    PRIO_ICON.get(a['prioridad'],'⚪') + " " + a['prioridad'],
        "Area":         a['area'],
        "Eficacia":     a['eficacia'],
    } for a in acc_filtradas])

    st.dataframe(df_acc, use_container_width=True, hide_index=True,
                 column_config={
                     "Accion": st.column_config.TextColumn(width="large"),
                     "Fecha Limite": st.column_config.DateColumn(format="DD/MM/YYYY"),
                 })

    st.markdown("---")
    st.markdown("### ✏️ Actualizar Estado de Accion")

    acc_ids_inm = [a for a in acc_filtradas if a['id_ref'].startswith('AI-')]
    if acc_ids_inm:
        sel_ref = st.selectbox("Seleccionar accion inmediata:",
            options=[''] + [a['id_ref'] for a in acc_ids_inm],
            format_func=lambda x: x if not x else
                x + " | " + next((a['accion'][:60] for a in acc_ids_inm if a['id_ref']==x), ''),
            key="pa_sel_ref")

        if sel_ref:
            id_num = int(sel_ref.replace('AI-',''))
            acc_sel = next((a for a in acc_ids_inm if a['id_ref'] == sel_ref), None)
            if acc_sel:
                with st.form("form_update_pa_" + sel_ref):
                    st.markdown("**Accion:** " + acc_sel['accion'])
                    uc1, uc2, uc3 = st.columns(3)
                    nuevo_est = uc1.selectbox("Nuevo Estado",
                        ['PENDIENTE','EN_PROCESO','CERRADO'],
                        index=['PENDIENTE','EN_PROCESO','CERRADO'].index(
                            acc_sel['estado'].replace('🔴 ','').replace('🟡 ','').replace('🟢 ','')),
                        key="nest_" + sel_ref)
                    nueva_efic = uc2.selectbox("Eficacia",
                        ['POR_VERIFICAR','EFICAZ','NO_EFICAZ'],
                        index=['POR_VERIFICAR','EFICAZ','NO_EFICAZ'].index(
                            acc_sel['eficacia'] if acc_sel['eficacia'] in ['POR_VERIFICAR','EFICAZ','NO_EFICAZ'] else 'POR_VERIFICAR'),
                        key="nefic_" + sel_ref)
                    fecha_cierre_pa = uc3.date_input("Fecha de Cierre Real",
                        value=datetime.date.today(), key="nfech_" + sel_ref)
                    obs_pa = st.text_area("Observaciones de cierre / evidencia", height=70,
                                         key="nobs_" + sel_ref)

                    if st.form_submit_button("✅ ACTUALIZAR ACCION", type="primary"):
                        db_run("""UPDATE acciones_inmediatas SET estado=?,eficacia=?,fecha_cierre=?
                            WHERE id=?""", (nuevo_est, nueva_efic, str(fecha_cierre_pa), id_num))
                        st.success("✅ Accion " + sel_ref + " actualizada a estado: **" + nuevo_est + "**")
                        st.rerun()

    st.markdown("---")
    st.markdown("### 📈 Indicadores de Avance")

    gc1, gc2 = st.columns(2)

    with gc1:
        st.markdown("**Distribucion por Estado**")
        estados_count = {'PENDIENTE': pend, 'EN_PROCESO': en_proc, 'CERRADO': cerradas}
        df_est = pd.DataFrame(list(estados_count.items()), columns=['Estado','Cantidad'])
        st.bar_chart(df_est.set_index('Estado'), color=['#dc3545'])

    with gc2:
        st.markdown("**Distribucion por Prioridad**")
        prio_count = {}
        for a in todas_acc:
            p = a['prioridad']
            prio_count[p] = prio_count.get(p, 0) + 1
        df_prio = pd.DataFrame(list(prio_count.items()), columns=['Prioridad','Cantidad'])
        st.bar_chart(df_prio.set_index('Prioridad'))

    st.markdown("**Avance por Documento (% cerrado)**")
    docs_uniq = {}
    for a in todas_acc:
        k = a['origen']
        if k not in docs_uniq:
            docs_uniq[k] = {'total':0,'cerrado':0,'tipo':a['tipo_doc'],'area':a['area']}
        docs_uniq[k]['total'] += 1
        if a['estado'] == 'CERRADO':
            docs_uniq[k]['cerrado'] += 1

    df_docs_avance = pd.DataFrame([{
        'Documento': k,
        'Tipo': v['tipo'],
        'Area': v['area'],
        'Total Acciones': v['total'],
        'Cerradas': v['cerrado'],
        'Pendientes': v['total'] - v['cerrado'],
        '% Avance': round(v['cerrado']/v['total']*100, 1) if v['total']>0 else 0
    } for k, v in docs_uniq.items()])

    if not df_docs_avance.empty:
        st.dataframe(
            df_docs_avance.sort_values('% Avance'),
            use_container_width=True, hide_index=True,
            column_config={
                "% Avance": st.column_config.ProgressColumn(
                    "% Avance", min_value=0, max_value=100, format="%.1f%%")
            }
        )

# ==============================================================================
# NAVEGACION PRINCIPAL
# ==============================================================================
def main():
    if 'pagina' not in st.session_state:
        st.session_state['pagina'] = 'dashboard'
    if 'doc_codigo' not in st.session_state:
        st.session_state['doc_codigo'] = None
    if 'doc_tipo' not in st.session_state:
        st.session_state['doc_tipo'] = 'ACR'

    with st.sidebar:
        cfg = get_empresa_cfg()
        logo_b = cfg.get('logo_blob')
        if logo_b:
            try:
                st.image(Image.open(io.BytesIO(logo_b)), use_container_width=True)
            except Exception:
                pass

        st.markdown("### " + (cfg.get('nombre_empresa','SISTEMA ACR/AFA')))
        st.markdown("**Gestion Documental de Mantenimiento**")
        st.markdown("---")

        st.markdown("#### 📋 Navegacion")
        if st.button("🏠 Dashboard", use_container_width=True):
            st.session_state['pagina'] = 'dashboard'
            st.session_state['doc_codigo'] = None
            st.rerun()

        if st.button("📋 Todos los Documentos", use_container_width=True):
            st.session_state['pagina'] = 'listado'
            st.rerun()

        if st.button("📊 Plan de Accion", use_container_width=True):
            st.session_state['pagina'] = 'plan_accion'
            st.rerun()

        if st.button("📚 Historico", use_container_width=True):
            st.session_state['pagina'] = 'historico'
            st.rerun()

        st.markdown("#### ➕ Nuevo Documento")
        if st.button("🔍 Nuevo ACR", use_container_width=True, type="primary"):
            st.session_state['pagina'] = 'form'
            st.session_state['doc_codigo'] = None
            st.session_state['doc_tipo'] = 'ACR'
            st.rerun()

        if st.button("⚠️ Nuevo AFA", use_container_width=True, type="primary"):
            st.session_state['pagina'] = 'form'
            st.session_state['doc_codigo'] = None
            st.session_state['doc_tipo'] = 'AFA'
            st.rerun()

        st.markdown("---")
        if st.button("⚙️ Configuracion Empresa", use_container_width=True):
            st.session_state['pagina'] = 'config'
            st.rerun()

        if st.button("🤖 Configuracion IA", use_container_width=True):
            st.session_state['pagina'] = 'config_ia'
            st.rerun()

        st.markdown("---")
        st.markdown("""
        <small style='color:#adb5bd'>
        v13.0.0 | Gemini v3.x | ISO 9001 · ISO 14224<br>
        TPM · RCM · ORICA Standards<br>
        CAVA — Roger Huamani
        </small>""", unsafe_allow_html=True)

    pagina = st.session_state.get('pagina', 'dashboard')
    if pagina == 'dashboard':
        page_dashboard()
    elif pagina == 'form':
        page_form()
    elif pagina == 'listado':
        page_listado()
    elif pagina == 'config':
        page_config_empresa()
    elif pagina == 'config_ia':
        page_config_ia()
    elif pagina == 'plan_accion':
        page_plan_accion()
    elif pagina == 'historico':
        page_historico()
    else:
        page_dashboard()

if __name__ == "__main__":
    main()

