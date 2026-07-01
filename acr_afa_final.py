#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SISTEMA INSTITUCIONAL DE GESTION DOCUMENTAL ACR / AFA — STREAMLIT WEB
Analisis de Causa Raiz (ACR) y Analisis de Fallas y Acciones (AFA)
Version: 10.0.0 | Normativa: ISO 9001, ISO 14224, TPM, RCM
================================================================================
"""

import streamlit as st
import sqlite3
import io
import os
import datetime
import base64
import tempfile
import uuid
import hashlib
import secrets as pysecrets
import shutil
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
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Reset y tipografia base ── */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* ── Sidebar institucional ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a2f4a 0%, #1e3a5f 60%, #162d47 100%) !important;
    border-right: 3px solid #1e60a8;
}
[data-testid="stSidebar"] * {
    color: #e8edf2 !important;
}
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

/* ── Encabezado principal ── */
.inst-header-main {
    background: linear-gradient(135deg, #1e3a5f 0%, #1e60a8 100%);
    color: white; padding: 18px 28px; border-radius: 10px;
    margin-bottom: 20px; border-left: 5px solid #4a90d9;
    box-shadow: 0 4px 16px rgba(30,58,95,.2);
}
.inst-title  { font-size: 1.5rem; font-weight: 700; letter-spacing: .4px; margin: 0; }
.inst-sub    { font-size: .82rem; opacity: .82; margin-top: 4px; }

/* ── Bandas de seccion ── */
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

/* ── Tarjetas de metricas ── */
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

/* ── Botones ── */
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

/* ── Inputs y selects ── */
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

/* ── Labels de campos ── */
.stTextInput label, .stTextArea label, .stSelectbox label,
.stRadio label, .stDateInput label, .stNumberInput label {
    font-weight: 600 !important; color: #2c3e50 !important;
    font-size: .85rem !important; letter-spacing: .2px;
}

/* ── Tabs ── */
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

/* ── Expanders ── */
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

/* ── Dataframes / tablas ── */
[data-testid="stDataFrame"] {
    border: 1px solid #dee2e6 !important; border-radius: 8px;
    overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.06);
}

/* ── Mensajes de alerta ── */
[data-testid="stAlert"] {
    border-radius: 8px !important; border-left-width: 4px !important;
    font-weight: 500 !important;
}

/* ── Badges de estado ── */
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

/* ── Badges de prioridad ── */
.prio-chip {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: .76rem; font-weight: 700;
}
.prio-BAJA    { background:#d1f2eb; color:#0e6655; }
.prio-MEDIA   { background:#fef9c3; color:#7d6608; }
.prio-ALTA    { background:#fde8c8; color:#9c4221; }
.prio-CRITICA { background:#fcd0d0; color:#7b1818; border: 1px solid #e74c3c; }

/* ── KPI Cards para Plan de Accion ── */
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

/* ── Formularios (contenedor) ── */
[data-testid="stForm"] {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 16px 20px !important;
}

/* ── Dividers ── */
hr { border: none; border-top: 1px solid #e9ecef; margin: 16px 0; }

/* ── Progress bars ── */
[data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, #1e60a8, #4a90d9) !important;
    border-radius: 4px !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f1f1f1; }
::-webkit-scrollbar-thumb { background: #adb5bd; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #1e60a8; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# BASE DE DATOS — Conexion por sesion, ligada a la carpeta de almacenamiento
# ==============================================================================
# IMPORTANTE: cada usuario/sesion de Streamlit elige su propia "carpeta de
# almacenamiento" (workspace). Toda la data (documentos ACR/AFA, historico,
# evidencias, usuarios) vive en un unico archivo SQLite dentro de esa carpeta:
#   <carpeta_elegida>/acr_afa_system.db
# Esto permite: (1) que el historico persista entre sesiones si la carpeta es
# una ruta local/red persistente, y (2) que el usuario pueda respaldar/restaurar
# ese archivo .db manualmente (boton de Backup) cuando la app corre en un
# entorno efimero como Streamlit Community Cloud, donde el disco se reinicia
# al reiniciar/redesplegar la app.
DB_FILENAME = "acr_afa_system.db"

def workspace_db_path():
    wp = st.session_state.get('workspace_path')
    if not wp:
        return None
    return os.path.join(wp, DB_FILENAME)

def get_db():
    """Devuelve la conexion SQLite de la carpeta de almacenamiento activa.
    La conexion se guarda en session_state (no en cache_resource) porque cada
    sesion/usuario puede tener una carpeta distinta."""
    path = workspace_db_path()
    if not path:
        raise RuntimeError("No hay una carpeta de almacenamiento configurada todavia.")
    conn = st.session_state.get('_db_conn')
    conn_path = st.session_state.get('_db_conn_path')
    if conn is None or conn_path != path:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        conn = sqlite3.connect(path, check_same_thread=False, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
        _crear_tablas(conn)
        st.session_state['_db_conn'] = conn
        st.session_state['_db_conn_path'] = path
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
        """CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            nombre_completo TEXT,
            rol TEXT CHECK(rol IN ('admin','usuario')) DEFAULT 'usuario',
            area TEXT,
            activo INTEGER DEFAULT 1,
            creado_por TEXT,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultimo_acceso TIMESTAMP
        )""",
    ]
    for s in stmts:
        try:
            conn.execute(s)
        except Exception:
            pass
    # Migracion suave: agrega columnas nuevas a tablas ya existentes (creadas
    # con versiones anteriores del sistema) sin perder la data historica.
    for alter_sql in [
        "ALTER TABLE documentos ADD COLUMN creado_por TEXT",
    ]:
        try:
            conn.execute(alter_sql)
        except Exception:
            pass
    conn.commit()

# ==============================================================================
# AUTENTICACION Y GESTION DE USUARIOS (por carpeta / workspace)
# ==============================================================================
def _hash_password(password, salt=None):
    if salt is None:
        salt = pysecrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return h, salt

def existe_algun_usuario():
    row = db_one("SELECT COUNT(*) c FROM usuarios")
    return bool(row and row["c"] > 0)

def crear_usuario(username, password, nombre_completo="", rol="usuario", area="", creado_por=""):
    username = (username or "").strip().lower()
    if not username or not password:
        raise ValueError("Usuario y contraseña son obligatorios.")
    if db_one("SELECT id FROM usuarios WHERE username=?", (username,)):
        raise ValueError(f"El usuario '{username}' ya existe.")
    h, salt = _hash_password(password)
    db_run("""INSERT INTO usuarios (username,password_hash,salt,nombre_completo,rol,area,creado_por)
              VALUES(?,?,?,?,?,?,?)""",
           (username, h, salt, nombre_completo.strip(), rol, area.strip(), creado_por))

def autenticar_usuario(username, password):
    row = db_one("SELECT * FROM usuarios WHERE username=?", ((username or "").strip().lower(),))
    if not row or not row["activo"]:
        return None
    h, _ = _hash_password(password, row["salt"])
    if h != row["password_hash"]:
        return None
    db_run("UPDATE usuarios SET ultimo_acceso=CURRENT_TIMESTAMP WHERE id=?", (row["id"],))
    return dict(row)

def listar_usuarios():
    return db_query("SELECT * FROM usuarios ORDER BY rol DESC, fecha_creacion")

def cambiar_password(username, nueva_password):
    h, salt = _hash_password(nueva_password)
    db_run("UPDATE usuarios SET password_hash=?, salt=? WHERE username=?",
           (h, salt, (username or "").strip().lower()))

def contar_admins_activos():
    row = db_one("SELECT COUNT(*) c FROM usuarios WHERE rol='admin' AND activo=1")
    return row["c"] if row else 0

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
                Sistema de Gestión Documental — ACR / AFA | ISO 9001 · ISO 14224 · TPM · RCM
            </div>
        </div>""", unsafe_allow_html=True)
    st.markdown("---")

def estado_color(estado):
    m = {'BORRADOR':'🔘','EN_ANALISIS':'🔵','REVISADO':'🟡',
         'APROBADO':'🟢','CERRADO':'⚫','RECHAZADO':'🔴'}
    return m.get(estado, '⚪')

# ==============================================================================
# PAGINAS PRINCIPALES
# ==============================================================================

# ── Página: Dashboard ─────────────────────────────────────────────────────────
def page_dashboard():
    show_header()
    st.markdown("## 📊 Panel Principal")

    docs = db_query("SELECT * FROM documentos ORDER BY fecha_registro DESC")
    total = len(docs)
    acrs  = sum(1 for d in docs if d['tipo_documento']=='ACR')
    afas  = total - acrs
    abiertos = sum(1 for d in docs if d['estado'] not in ('CERRADO','APROBADO'))
    cerrados = sum(1 for d in docs if d['estado'] in ('CERRADO','APROBADO'))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📄 Total Documentos", total)
    c2.metric("🔍 ACR", acrs)
    c3.metric("⚠️ AFA", afas)
    c4.metric("✅ Cerrados / Aprobados", cerrados)

    st.markdown("---")
    st.markdown("### 📋 Documentos Recientes")

    if not docs:
        st.info("No hay documentos registrados. Cree su primer ACR o AFA desde el menú lateral.")
        return

    for d in docs[:15]:
        with st.expander(
            f"{estado_color(d['estado'])} **{d['codigo']}** — {d['tipo_documento']} | "
            f"{d['desc_problema_inicial'][:70] if d['desc_problema_inicial'] else 'Sin descripcion'}...",
            expanded=False
        ):
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Tipo:** {d['tipo_documento']}")
            c1.write(f"**Estado:** {d['estado']}")
            c2.write(f"**Reportado por:** {d['reportado_por']}")
            c2.write(f"**Area:** {d['area_equipo'] or '—'}")
            c3.write(f"**Prioridad:** {d['prioridad']}")
            c3.write(f"**Fecha:** {d['fecha_reporte']}")

            bc1, bc2, bc3 = st.columns([1,1,2])
            if bc1.button("✏️ Editar", key=f"edit_{d['codigo']}"):
                st.session_state['pagina'] = 'form'
                st.session_state['doc_codigo'] = d['codigo']
                st.session_state['doc_tipo'] = d['tipo_documento']
                st.rerun()
            if bc2.button("📄 Exportar PDF", key=f"pdf_{d['codigo']}"):
                with st.spinner("Generando PDF..."):
                    pdf_bytes = exportar_pdf(d['codigo'], d['tipo_documento']=='ACR')
                bc2.download_button("⬇️ Descargar", pdf_bytes,
                                    file_name=f"{d['codigo']}.pdf",
                                    mime="application/pdf",
                                    key=f"dl_{d['codigo']}")

# ── Página: Nuevo / Editar Documento ─────────────────────────────────────────
def page_form():
    show_header()
    tipo = st.session_state.get('doc_tipo', 'ACR')
    codigo = st.session_state.get('doc_codigo')
    es_nuevo = codigo is None

    icon = "🔍" if tipo == 'ACR' else "⚠️"
    titulo_tipo = "ANALISIS DE CAUSA RAIZ" if tipo == 'ACR' else "ANALISIS DE FALLAS"
    st.markdown(f"## {icon} {titulo_tipo} ({tipo})")

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
        st.info(f"**Codigo generado:** `{codigo}`")
    else:
        st.info(f"**Editando:** `{codigo}`")

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
            _usr_actual = st.session_state.get('usuario') or {}
            _rp_default = d.get('reportado_por','') or (_usr_actual.get('nombre_completo') or _usr_actual.get('username') or '')
            reportado_por   = st.text_input("Reportado por *", value=_rp_default, key="rp")
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
                index=['BAJA','MEDIA','ALTA','CRITICA'].index(d.get('prioridad','MEDIA')), key="prio")
        with c4:
            aprobado_por = st.text_input("Aprobado por", value=d.get('aprobado_por',''), key="ap")
            costo_estimado = st.number_input("Costo estimado (S/.)", min_value=0.0,
                value=float(d.get('costo_estimado') or 0), step=100.0, key="ce")

        # Impactos
        st.markdown("**Impactos**")
        ci1, ci2, ci3 = st.columns(3)
        imp_prod = ci1.text_input("Impacto en Produccion", value=d.get('impacto_produccion',''), key="ip")
        imp_seg  = ci2.text_input("Impacto en Seguridad", value=d.get('impacto_seguridad',''), key="is")
        imp_amb  = ci3.text_input("Impacto Ambiental", value=d.get('impacto_ambiental',''), key="ia")

        # Sesiones (solo ACR)
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

        # GUARDAR datos generales
        if st.button("💾 Guardar Datos Generales", type="primary", key="save_gen"):
            _save_doc_general(codigo, tipo, es_nuevo, locals())
            st.session_state['doc_codigo'] = codigo
            st.session_state['es_nuevo_guardado'] = False
            st.success(f"✅ Guardado correctamente. Codigo: `{codigo}`")
            st.rerun()

    # ── TAB 2: Problema / 5W+2H ───────────────────────────────────────────────
    with tabs[1]:
        _tab_problema(codigo, d, tipo, es_nuevo)

    # ── TAB 3: Condiciones 6M (ACR) o Analisis WW (AFA) ─────────────────────
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

    # ── Exportar PDF ─────────────────────────────────────────────────────────
    st.markdown("---")
    if not es_nuevo or st.session_state.get('doc_codigo'):
        cod_actual = st.session_state.get('doc_codigo', codigo)
        st.markdown("### 📥 Exportar Documento")
        if st.button("📄 Generar PDF Institucional", type="primary"):
            with st.spinner("Generando PDF con orientacion inteligente (retrato + paisaje)..."):
                pdf_b = exportar_pdf(cod_actual, tipo=='ACR')
            st.download_button("⬇️ Descargar PDF", pdf_b,
                               file_name=f"{cod_actual}.pdf",
                               mime="application/pdf")

def _save_doc_general(codigo, tipo, es_nuevo, local_vars):
    """Guarda o actualiza los datos generales del documento."""
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
        usr = st.session_state.get('usuario') or {}
        creado_por = usr.get('nombre_completo') or usr.get('username') or ''
        db_run("""INSERT OR IGNORE INTO documentos
            (tipo_documento,codigo,fecha_reporte,estado,reportado_por,cargo_reportante,
             area_reportante,lider_afa,area_equipo,responsables,fecha_inicio_analisis,
             aprobado_por,prioridad,costo_estimado,impacto_produccion,impacto_seguridad,impacto_ambiental,
             creado_por)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (tipo,codigo,fr,est,rp,cr,ar,la,ae,resp,fi,ap,prio,ce,ip,is_,ia,creado_por))
    else:
        db_run("""UPDATE documentos SET
            fecha_reporte=?,estado=?,reportado_por=?,cargo_reportante=?,
            area_reportante=?,lider_afa=?,area_equipo=?,responsables=?,
            fecha_inicio_analisis=?,aprobado_por=?,prioridad=?,costo_estimado=?,
            impacto_produccion=?,impacto_seguridad=?,impacto_ambiental=?,
            ultima_modificacion=CURRENT_TIMESTAMP
            WHERE codigo=?""",
               (fr,est,rp,cr,ar,la,ae,resp,fi,ap,prio,ce,ip,is_,ia,codigo))

def _tab_problema(codigo, d, tipo, es_nuevo):
    st.markdown('<div class="seccion-band">2. DESCRIPCION DEL PROBLEMA</div>', unsafe_allow_html=True)

    desc_inicial = st.text_area("1. Descripcion del problema inicial",
        value=d.get('desc_problema_inicial',''), height=100, key="dpi")

    st.markdown('<div class="seccion-band">3. QUE? — Contexto (Fotos, Graficas, Flujos)</div>',
                unsafe_allow_html=True)
    que_ctx = st.text_area("Que fue lo que vio? Que tarea fallo? Que debio pasar?",
        value=d.get('que_contexto',''), height=100, key="qc")

    # Imagenes inline para QUE?
    _upload_imagenes_inline(codigo, 'que', es_nuevo)

    st.markdown('<div class="seccion-band">4. COMO? — Entienda como ocurre el problema</div>',
                unsafe_allow_html=True)
    como_oc = st.text_area("Como ocurrio? Como se ejecuto el trabajo?",
        value=d.get('como_ocurre',''), height=100, key="co")
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
    with st.expander(f"📷 Imagenes / Evidencias de esta seccion ({seccion.upper()})", expanded=False):
        c1, c2 = st.columns([3,1])
        desc_img = c1.text_input("Descripcion breve", key=f"desc_img_{seccion}")
        tipo_evi = c2.selectbox("Tipo", ['FALLA','CAUSA','ACCION','VERIFICACION','REFERENCIA','OTRO'],
                                key=f"tipo_evi_{seccion}")
        uploaded = st.file_uploader("Seleccionar imagen",
            type=['png','jpg','jpeg','bmp','gif'],
            key=f"uploader_{seccion}")
        if st.button("+ Agregar imagen", key=f"btn_img_{seccion}") and uploaded:
            img_b = uploaded.read()
            fmt = "." + uploaded.name.split('.')[-1].lower()
            db_run("""INSERT INTO evidencias
                (codigo_documento,nombre_archivo,tipo_evidencia,descripcion,imagen_blob,tamano_bytes,formato,seccion)
                VALUES(?,?,?,?,?,?,?,?)""",
                   (codigo, uploaded.name, tipo_evi, desc_img or uploaded.name,
                    img_b, len(img_b), fmt, seccion))
            st.success(f"Imagen '{uploaded.name}' agregada.")
            st.rerun()

        # Galeria de imagenes de esta seccion
        evis = db_query("SELECT * FROM evidencias WHERE codigo_documento=? AND seccion=? ORDER BY fecha_registro",
                        (codigo, seccion)) if not es_nuevo else []
        if evis:
            cols = st.columns(min(len(evis), 4))
            for i, evi in enumerate(evis):
                with cols[i % 4]:
                    if evi['imagen_blob']:
                        try:
                            img = Image.open(io.BytesIO(evi['imagen_blob']))
                            st.image(img, caption=f"Fig. {i+1} — {evi['descripcion'] or evi['nombre_archivo']}",
                                     use_container_width=True)
                        except Exception:
                            st.caption(f"Fig. {i+1}: {evi['nombre_archivo']}")
                    if st.button("🗑 Eliminar", key=f"del_evi_{evi['id']}"):
                        db_run("DELETE FROM evidencias WHERE id=?", (evi['id'],))
                        st.rerun()

def _seccion_acciones_inmediatas(codigo, es_nuevo):
    if es_nuevo and not st.session_state.get('doc_codigo'):
        st.caption("_Guarda primero los datos generales._")
        return

    # Tabla de acciones existentes
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

    # Eliminar accion
    if accs:
        id_del = st.selectbox("Eliminar accion con ID:",
                              options=[0]+[a['id'] for a in accs],
                              format_func=lambda x: "Seleccionar..." if x==0 else
                              f"ID {x}: {next((a['accion'][:50] for a in accs if a['id']==x), '')}",
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

    # Condiciones ideales segun formato ORICA MAN-F-054 Ed.02
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
        st.markdown(f"""
        <div style="background:#1e3a5f;color:white;font-weight:700;padding:8px 14px;
                    border-radius:6px;margin:14px 0 8px 0;font-size:.95rem;">
            {ICONO_CAT.get(cat,'')} {cat}
        </div>""", unsafe_allow_html=True)

        for (item, condicion_ideal_default) in items:
            key = f"{cat}|{item}"
            existing = conds_db.get(key, {})
            aplica_val = existing.get('aplica', 'SI')
            diferencia_val = existing.get('diferencia', 'NO')

            # Color de borde segun estado
            if aplica_val == 'SI' and diferencia_val == 'SI':
                border_color = "#dc3545"  # rojo = diferencia detectada
                estado_icon = "🔴"
            elif aplica_val == 'NO':
                border_color = "#6c757d"  # gris = no aplica
                estado_icon = "⚫"
            else:
                border_color = "#198754"  # verde = OK
                estado_icon = "🟢"

            with st.expander(f"{estado_icon} **{item}**", expanded=(diferencia_val=='SI')):
                # Condicion ideal (pre-rellenada, editable)
                st.markdown("**📌 Condicion Ideal:**")
                ideal = st.text_area("",
                    value=existing.get('condicion_ideal', condicion_ideal_default),
                    height=90, key=f"ci_{key}",
                    help="Esta es la condicion que deberia existir segun el estandar.")

                # Condicion actual (hallazgo)
                st.markdown("**🔍 Condicion Actual — Hallazgo o Causa Inmediata:**")
                actual = st.text_area("",
                    value=existing.get('condicion_actual',''),
                    height=80, key=f"ca_{key}",
                    placeholder="Describa lo que encontro en campo...",
                    help="Describa la condicion real encontrada durante la inspeccion.")

                cr1, cr2 = st.columns(2)
                aplica = cr1.radio(f"¿Aplica esta condicion?",
                    ['SI','NO'],
                    index=0 if aplica_val == 'SI' else 1,
                    horizontal=True, key=f"ap_{key}")
                diferencia = cr2.radio(f"¿Existe diferencia respecto al ideal?",
                    ['NO','SI'],
                    index=0 if diferencia_val == 'NO' else 1,
                    horizontal=True, key=f"df_{key}")

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

    # Resumen de condiciones con diferencia
    conds_actuales = db_query("SELECT * FROM condiciones_basicas WHERE codigo_acr=? AND diferencia='SI'", (codigo,))
    if conds_actuales:
        col_info.info(f"⚠️ **{len(conds_actuales)} condicion(es) con diferencia detectada** — deben incluirse en el análisis Why-Why.")

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

    # Mostrar ramas existentes
    for i, w in enumerate(whys):
        with st.expander(
            f"**Rama {w['rama_id']}** {PRIO_COLS.get(w['prioridad'],'⚪')} "
            f"| Def: {(w['definicion'] or '—')[:50]}...",
            expanded=False
        ):
            # Visualizacion horizontal con flechas
            st.markdown("**Cadena causal:**")
            chain_cols = st.columns([3,0.3,2,0.3,2,0.3,2,0.3,2,0.3,2,0.3,3])
            chain_cols[0].markdown(f"**Definicion**<br><small>{w['definicion'] or '—'}</small>",
                                   unsafe_allow_html=True)
            for ci, (pq, label) in enumerate([(w['pq1'],'PQ1'),(w['pq2'],'PQ2'),(w['pq3'],'PQ3'),
                                               (w['pq4'],'PQ4'),(w['pq5'],'PQ5'),(w['causa_raiz'],'Causa')]):
                chain_cols[ci*2+1].markdown('<div style="color:#1e60a8;font-size:1.5rem;text-align:center">→</div>',
                                            unsafe_allow_html=True)
                chain_cols[ci*2+2].markdown(f"**{label}**<br><small>{pq or '—'}</small>",
                                            unsafe_allow_html=True)

            st.markdown("---")
            wc1, wc2 = st.columns(2)
            new_def = wc1.text_area("Definicion del problema", value=w['definicion'] or '', height=60, key=f"wdef_{w['id']}")
            new_pq1 = wc2.text_area("Por que 1?", value=w['pq1'] or '', height=60, key=f"wp1_{w['id']}")
            wc3, wc4 = st.columns(2)
            new_pq2 = wc3.text_area("Por que 2?", value=w['pq2'] or '', height=60, key=f"wp2_{w['id']}")
            new_pq3 = wc4.text_area("Por que 3?", value=w['pq3'] or '', height=60, key=f"wp3_{w['id']}")
            wc5, wc6 = st.columns(2)
            new_pq4 = wc5.text_area("Por que 4?", value=w['pq4'] or '', height=60, key=f"wp4_{w['id']}")
            new_pq5 = wc6.text_area("Por que 5?", value=w['pq5'] or '', height=60, key=f"wp5_{w['id']}")
            wc7, wc8 = st.columns(2)
            new_cr   = wc7.text_area("Causa Raiz", value=w['causa_raiz'] or '', height=60, key=f"wcr_{w['id']}")
            new_acc  = wc8.text_area("Accion sobre Causa Raiz", value=w['accion_causa_raiz'] or '', height=60, key=f"wacc_{w['id']}")
            wc9, wc10, wc11 = st.columns(3)
            new_resp = wc9.text_input("Responsable", value=w['responsable'] or '', key=f"wresp_{w['id']}")
            new_prio = wc10.selectbox("Prioridad", ['BAJA','MEDIA','ALTA','CRITICA'],
                index=['BAJA','MEDIA','ALTA','CRITICA'].index(w['prioridad'] or 'MEDIA'),
                key=f"wprio_{w['id']}")
            new_fech = wc11.date_input("Fecha",
                value=datetime.date.fromisoformat(w['fecha']) if w['fecha'] else datetime.date.today(),
                key=f"wfech_{w['id']}")

            ba, bb = st.columns(2)
            if ba.button("💾 Actualizar Rama", key=f"wupd_{w['id']}"):
                db_run("""UPDATE why_why SET definicion=?,pq1=?,pq2=?,pq3=?,pq4=?,pq5=?,
                    causa_raiz=?,accion_causa_raiz=?,responsable=?,prioridad=?,fecha=?
                    WHERE id=?""",
                       (new_def,new_pq1,new_pq2,new_pq3,new_pq4,new_pq5,
                        new_cr,new_acc,new_resp,new_prio,str(new_fech),w['id']))
                st.success(f"Rama {w['rama_id']} actualizada.")
                st.rerun()
            if bb.button("🗑 Eliminar Rama", key=f"wdel_{w['id']}"):
                db_run("DELETE FROM why_why WHERE id=?", (w['id'],))
                st.success("Rama eliminada.")
                st.rerun()

    # Nueva rama
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
        nr_fech = rc11.date_input("Fecha", value=datetime.date.today())
        if st.form_submit_button("+ AGREGAR RAMA", type="primary"):
            if nr_def.strip():
                db_run("""INSERT INTO why_why
                    (codigo_documento,rama_id,definicion,pq1,pq2,pq3,pq4,pq5,
                     causa_raiz,accion_causa_raiz,responsable,prioridad,fecha)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (codigo, str(rama_num), nr_def, nr_pq1, nr_pq2, nr_pq3, nr_pq4, nr_pq5,
                        nr_cr, nr_acc, nr_resp, nr_prio, str(nr_fech)))
                st.success(f"Rama {rama_num} agregada.")
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

    with st.form("form_anx", clear_on_submit=True):
        ac1, ac2 = st.columns([3,1])
        desc_anx = ac1.text_input("Descripcion breve de la evidencia")
        tipo_anx = ac2.selectbox("Tipo", ['FALLA','CAUSA','ACCION','VERIFICACION','REFERENCIA','SESION','OTRO'])
        uploaded_anx = st.file_uploader("Seleccionar archivo",
            type=['png','jpg','jpeg','bmp','gif','pdf'])
        if st.form_submit_button("+ Agregar Evidencia", type="primary"):
            if uploaded_anx:
                img_b = uploaded_anx.read()
                fmt = "." + uploaded_anx.name.split('.')[-1].lower()
                db_run("""INSERT INTO evidencias
                    (codigo_documento,nombre_archivo,tipo_evidencia,descripcion,imagen_blob,tamano_bytes,formato,seccion)
                    VALUES(?,?,?,?,?,?,?,?)""",
                       (codigo, uploaded_anx.name, tipo_anx, desc_anx or uploaded_anx.name,
                        img_b, len(img_b), fmt, 'GENERAL'))
                st.success(f"Evidencia '{uploaded_anx.name}' agregada.")
                st.rerun()

    # Galeria completa
    evis = db_query("SELECT * FROM evidencias WHERE codigo_documento=? ORDER BY fecha_registro", (codigo,))
    if evis:
        st.markdown(f"**{len(evis)} evidencia(s) registrada(s):**")
        cols = st.columns(3)
        for i, evi in enumerate(evis):
            with cols[i % 3]:
                if evi['imagen_blob'] and evi['formato'] in ['.jpg','.jpeg','.png','.bmp','.gif']:
                    try:
                        img = Image.open(io.BytesIO(evi['imagen_blob']))
                        st.image(img, caption=f"Fig. {i+1} [{evi['tipo_evidencia']}] {evi['descripcion'] or evi['nombre_archivo']}",
                                 use_container_width=True)
                    except Exception:
                        st.caption(f"Fig. {i+1}: {evi['nombre_archivo']}")
                else:
                    st.caption(f"📎 {evi['nombre_archivo']} ({evi['tipo_evidencia']})")
                if st.button(f"🗑 Eliminar Fig.{i+1}", key=f"del_anx_{evi['id']}"):
                    db_run("DELETE FROM evidencias WHERE id=?", (evi['id'],))
                    st.rerun()
    else:
        st.info("No hay evidencias registradas aun.")

# ── Página: Configuracion Empresa ─────────────────────────────────────────────
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

# ── Página: Listado de documentos ─────────────────────────────────────────────
def page_listado():
    show_header()
    st.markdown("## 📋 Todos los Documentos")

    # Filtros
    fc1, fc2, fc3 = st.columns(3)
    f_tipo   = fc1.selectbox("Tipo", ['TODOS','ACR','AFA'])
    f_estado = fc2.selectbox("Estado", ['TODOS','BORRADOR','EN_ANALISIS','REVISADO','APROBADO','RECHAZADO','CERRADO'])
    f_busq   = fc3.text_input("Buscar (codigo, descripcion, causa raiz, area, responsable)...")
    st.caption("💡 Use este buscador para revisar si un problema ya ocurrió antes: busque por equipo, "
               "área o palabras clave de la causa raíz y compare con la causa identificada en cada caso.")

    sql = "SELECT * FROM documentos WHERE 1=1"
    params = []
    if f_tipo != 'TODOS':
        sql += " AND tipo_documento=?"; params.append(f_tipo)
    if f_estado != 'TODOS':
        sql += " AND estado=?"; params.append(f_estado)
    if f_busq:
        sql += """ AND (codigo LIKE ? OR desc_problema_inicial LIKE ? OR responsables LIKE ?
                        OR reportado_por LIKE ? OR area_equipo LIKE ? OR causa_raiz_identificada LIKE ?)"""
        b = f"%{f_busq}%"
        params.extend([b,b,b,b,b,b])
    sql += " ORDER BY fecha_registro DESC"
    docs = db_query(sql, tuple(params))

    st.markdown(f"**{len(docs)} documento(s) encontrado(s)**")

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
            "Descripcion": (d['desc_problema_inicial'] or '')[:60],
            "Causa Raiz": (d['causa_raiz_identificada'] or '—')[:60] if 'causa_raiz_identificada' in d.keys() else '—',
            "Creado por": d['creado_por'] if 'creado_por' in d.keys() and d['creado_por'] else '—',
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
                               file_name=f"{sel_cod}.pdf",
                               mime="application/pdf",
                               key="dl_list")
        if bc.button("🗑 Eliminar"):
            db_run("DELETE FROM documentos WHERE codigo=?", (sel_cod,))
            st.success(f"Documento {sel_cod} eliminado.")
            st.rerun()

# ── Página: Plan de Acción ─────────────────────────────────────────────────────
def page_plan_accion():
    show_header()
    st.markdown("## 📊 Plan de Acción — Control y Seguimiento Gerencial")
    st.caption("Gestión centralizada de todas las acciones ACR/AFA. Vista ejecutiva para Gerencias de Producción, Mantenimiento y SHES.")

    # ── KPIs principales ──────────────────────────────────────────────────────
    today = datetime.date.today().isoformat()

    all_acc = db_query("""
        SELECT ai.*, d.tipo_documento, d.area_equipo, d.prioridad as doc_prioridad,
               d.estado as doc_estado
        FROM acciones_inmediatas ai
        JOIN documentos d ON ai.codigo_acr = d.codigo
        ORDER BY ai.fecha ASC
    """)
    all_why = db_query("""
        SELECT ww.*, d.tipo_documento, d.area_equipo, d.prioridad as doc_prioridad,
               d.estado as doc_estado
        FROM why_why ww
        JOIN documentos d ON ww.codigo_documento = d.codigo
        WHERE ww.accion_causa_raiz IS NOT NULL AND ww.accion_causa_raiz != ''
        ORDER BY ww.fecha ASC
    """)

    # Combinar todas las acciones en una vista unificada
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
            'id_ref': f"AI-{a['id']}",
        })
    for w in all_why:
        todas_acc.append({
            'origen': w['codigo_documento'],
            'tipo_doc': w['tipo_documento'],
            'tipo_accion': 'Causa Raiz / Why-Why',
            'accion': w['accion_causa_raiz'],
            'responsable': w['responsable'] or '—',
            'fecha': w['fecha'] or '',
            'estado': w['estatus'] or 'PENDIENTE',
            'eficacia': '—',
            'area': w['area_equipo'] or '—',
            'prioridad': w['prioridad'] or 'MEDIA',
            'id_ref': f"WW-{w['id']}",
        })

    total    = len(todas_acc)
    pend     = sum(1 for a in todas_acc if a['estado'] == 'PENDIENTE')
    en_proc  = sum(1 for a in todas_acc if a['estado'] == 'EN_PROCESO')
    cerradas = sum(1 for a in todas_acc if a['estado'] == 'CERRADO')
    vencidas = sum(1 for a in todas_acc
                   if a['fecha'] and a['fecha'] < today and a['estado'] not in ('CERRADO',))
    porc_avance = round(cerradas / total * 100, 1) if total > 0 else 0

    # KPI Cards
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.markdown(f"""<div class="kpi-card kpi-total">
        <div class="kpi-label">Total Acciones</div>
        <div class="kpi-num">{total}</div></div>""", unsafe_allow_html=True)
    k2.markdown(f"""<div class="kpi-card kpi-pend">
        <div class="kpi-label">Pendientes</div>
        <div class="kpi-num">{pend}</div></div>""", unsafe_allow_html=True)
    k3.markdown(f"""<div class="kpi-card kpi-proc">
        <div class="kpi-label">En Proceso</div>
        <div class="kpi-num">{en_proc}</div></div>""", unsafe_allow_html=True)
    k4.markdown(f"""<div class="kpi-card kpi-cerr">
        <div class="kpi-label">Cerradas</div>
        <div class="kpi-num">{cerradas}</div></div>""", unsafe_allow_html=True)
    k5.markdown(f"""<div class="kpi-card kpi-venc">
        <div class="kpi-label">Vencidas</div>
        <div class="kpi-num">{vencidas}</div></div>""", unsafe_allow_html=True)

    st.markdown("")
    st.markdown(f"**Avance global de cierre: {porc_avance}%**")
    st.progress(porc_avance / 100)

    if total == 0:
        st.info("No hay acciones registradas en el sistema aun.")
        return

    # ── Filtros ───────────────────────────────────────────────────────────────
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

    st.markdown(f"**{len(acc_filtradas)} accion(es) mostrada(s)**")

    # ── Tabla de acciones ─────────────────────────────────────────────────────
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
        "Estado":       f"{ESTADO_ICON.get(a['estado'],'⚪')} {a['estado']}",
        "Prioridad":    f"{PRIO_ICON.get(a['prioridad'],'⚪')} {a['prioridad']}",
        "Area":         a['area'],
        "Eficacia":     a['eficacia'],
    } for a in acc_filtradas])

    st.dataframe(df_acc, use_container_width=True, hide_index=True,
                 column_config={
                     "Accion": st.column_config.TextColumn(width="large"),
                     "Fecha Limite": st.column_config.DateColumn(format="DD/MM/YYYY"),
                 })

    # ── Actualizar estado de accion inmediata ─────────────────────────────────
    st.markdown("---")
    st.markdown("### ✏️ Actualizar Estado de Accion")

    acc_ids_inm = [a for a in acc_filtradas if a['id_ref'].startswith('AI-')]
    if acc_ids_inm:
        sel_ref = st.selectbox("Seleccionar accion inmediata:",
            options=[''] + [a['id_ref'] for a in acc_ids_inm],
            format_func=lambda x: x if not x else
                f"{x} | {next((a['accion'][:60] for a in acc_ids_inm if a['id_ref']==x), '')}",
            key="pa_sel_ref")

        if sel_ref:
            id_num = int(sel_ref.replace('AI-',''))
            acc_sel = next((a for a in acc_ids_inm if a['id_ref'] == sel_ref), None)
            if acc_sel:
                with st.form(f"form_update_pa_{sel_ref}"):
                    st.markdown(f"**Accion:** {acc_sel['accion']}")
                    uc1, uc2, uc3 = st.columns(3)
                    nuevo_est = uc1.selectbox("Nuevo Estado",
                        ['PENDIENTE','EN_PROCESO','CERRADO'],
                        index=['PENDIENTE','EN_PROCESO','CERRADO'].index(
                            acc_sel['estado'].replace('🔴 ','').replace('🟡 ','').replace('🟢 ','')),
                        key=f"nest_{sel_ref}")
                    nueva_efic = uc2.selectbox("Eficacia",
                        ['POR_VERIFICAR','EFICAZ','NO_EFICAZ'],
                        index=['POR_VERIFICAR','EFICAZ','NO_EFICAZ'].index(
                            acc_sel['eficacia'] if acc_sel['eficacia'] in ['POR_VERIFICAR','EFICAZ','NO_EFICAZ'] else 'POR_VERIFICAR'),
                        key=f"nefic_{sel_ref}")
                    fecha_cierre_pa = uc3.date_input("Fecha de Cierre Real",
                        value=datetime.date.today(), key=f"nfech_{sel_ref}")
                    obs_pa = st.text_area("Observaciones de cierre / evidencia", height=70,
                                         key=f"nobs_{sel_ref}")

                    if st.form_submit_button("✅ ACTUALIZAR ACCION", type="primary"):
                        db_run("""UPDATE acciones_inmediatas SET estado=?,eficacia=?,fecha_cierre=?
                            WHERE id=?""", (nuevo_est, nueva_efic, str(fecha_cierre_pa), id_num))
                        st.success(f"✅ Accion {sel_ref} actualizada a estado: **{nuevo_est}**")
                        st.rerun()

    # ── Graficos de avance ────────────────────────────────────────────────────
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

    # Avance por documento
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

    # ── Exportar plan a PDF ───────────────────────────────────────────────────
    st.markdown("---")
    if st.button("📄 Exportar Plan de Accion en PDF (Informe Gerencial)", type="primary"):
        with st.spinner("Generando informe gerencial..."):
            pdf_b = _exportar_plan_accion_pdf(todas_acc, docs_uniq, today)
        st.download_button("⬇️ Descargar Informe Gerencial PDF",
                           pdf_b, file_name="Plan_Acciones_Gerencial.pdf",
                           mime="application/pdf")


def _exportar_plan_accion_pdf(todas_acc, docs_uniq, today):
    """Genera PDF gerencial del plan de acciones."""
    from reportlab.lib import colors as rc
    from reportlab.lib.pagesizes import A4, landscape as rl_land
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame,
                                    Table, TableStyle, Paragraph, Spacer,
                                    PageBreak, HRFlowable)
    import io as _io

    A4_L = rl_land(A4)
    M = 15 * mm
    AW = A4_L[0] - 2*M

    buf = _io.BytesIO()
    cfg = get_empresa_cfg()
    nombre_emp = cfg.get('nombre_empresa') or 'EMPRESA INDUSTRIAL S.A.'
    texto_pie  = cfg.get('texto_pie_pagina') or 'Documento Controlado | ISO 9001 / ISO 14224'

    fr = Frame(M, M, AW, A4_L[1]-2*M, id='f')
    def _pie(c, d):
        c.saveState()
        c.setFont('Helvetica', 7)
        c.setFillColor(rc.HexColor('#6c757d'))
        c.drawCentredString(A4_L[0]/2, M-5*mm, f'Pag. {d.page} | Plan de Accion | {nombre_emp}')
        c.restoreState()

    tpl = PageTemplate(id='land', frames=[fr], pagesize=A4_L, onPage=_pie)
    doc = BaseDocTemplate(buf, pageTemplates=[tpl], pagesize=A4_L)

    base = getSampleStyleSheet()
    E = {
        'h': ParagraphStyle('H', parent=base['Normal'], fontSize=11,
                            fontName='Helvetica-Bold', textColor=rc.white, alignment=TA_CENTER),
        'c': ParagraphStyle('C', parent=base['Normal'], fontSize=7, leading=9, fontName='Helvetica'),
        'cb': ParagraphStyle('CB', parent=base['Normal'], fontSize=7, leading=9, fontName='Helvetica-Bold'),
        'p': ParagraphStyle('P', parent=base['Normal'], fontSize=7, fontName='Helvetica-Oblique',
                            textColor=rc.HexColor('#6c757d'), alignment=TA_CENTER),
    }
    AZ = rc.HexColor('#1e3a5f')
    BL = rc.HexColor('#ffffff')
    GC = rc.HexColor('#f8f9fa')
    BO = rc.HexColor('#adb5bd')

    EL = []

    # Portada / Encabezado
    EL.append(Table([[
        Paragraph(f'<b>{nombre_emp}</b>', ParagraphStyle('T', parent=base['Normal'],
            fontSize=16, fontName='Helvetica-Bold', textColor=AZ, alignment=TA_CENTER)),
    ]], colWidths=[AW]))
    EL.append(Spacer(1, 4))
    EL.append(Table([[
        Paragraph('<b>PLAN DE ACCION — INFORME GERENCIAL ACR / AFA</b>',
            ParagraphStyle('S', parent=base['Normal'], fontSize=12, fontName='Helvetica-Bold',
                          textColor=BL, alignment=TA_CENTER)),
    ]], colWidths=[AW], style=[
        ('BACKGROUND',(0,0),(-1,-1),AZ),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
    ]))
    EL.append(Spacer(1, 4))
    EL.append(Paragraph(f'Fecha de generacion: {today} | Total acciones: {len(todas_acc)}', E['p']))
    EL.append(Spacer(1, 8))

    # Resumen KPI
    pend = sum(1 for a in todas_acc if a['estado']=='PENDIENTE')
    proc = sum(1 for a in todas_acc if a['estado']=='EN_PROCESO')
    cerr = sum(1 for a in todas_acc if a['estado']=='CERRADO')
    venc = sum(1 for a in todas_acc if a['fecha'] and a['fecha']<today and a['estado']!='CERRADO')
    avance = round(cerr/len(todas_acc)*100, 1) if todas_acc else 0

    kpi_data = [[
        Paragraph('<b>TOTAL</b>', E['h']),
        Paragraph('<b>PENDIENTE</b>', E['h']),
        Paragraph('<b>EN PROCESO</b>', E['h']),
        Paragraph('<b>CERRADAS</b>', E['h']),
        Paragraph('<b>VENCIDAS</b>', E['h']),
        Paragraph('<b>% AVANCE</b>', E['h']),
    ],[
        Paragraph(str(len(todas_acc)), ParagraphStyle('KN', parent=base['Normal'],
            fontSize=22, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=AZ)),
        Paragraph(str(pend), ParagraphStyle('KR', parent=base['Normal'],
            fontSize=22, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=rc.HexColor('#dc3545'))),
        Paragraph(str(proc), ParagraphStyle('KO', parent=base['Normal'],
            fontSize=22, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=rc.HexColor('#fd7e14'))),
        Paragraph(str(cerr), ParagraphStyle('KG', parent=base['Normal'],
            fontSize=22, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=rc.HexColor('#198754'))),
        Paragraph(str(venc), ParagraphStyle('KP', parent=base['Normal'],
            fontSize=22, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=rc.HexColor('#6f42c1'))),
        Paragraph(f'{avance}%', ParagraphStyle('KA', parent=base['Normal'],
            fontSize=22, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=AZ)),
    ]]
    t_kpi = Table(kpi_data, colWidths=[AW/6]*6)
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),AZ),
        ('BOX',(0,0),(-1,-1),1,AZ),('INNERGRID',(0,0),(-1,-1),0.5,BO),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('BACKGROUND',(0,1),(-1,1),GC),
    ]))
    EL.append(t_kpi)
    EL.append(Spacer(1, 8))

    # Tabla principal de acciones
    hdr_col = [Paragraph(f'<b>{t}</b>', E['h']) for t in
               ['N','Documento','Tipo','Tipo Accion','Accion','Responsable','Fecha','Estado','Prioridad','Area','Eficacia']]
    rows_pa = [hdr_col]
    col_prio = {'BAJA':rc.HexColor('#d1f2eb'),'MEDIA':rc.HexColor('#fef9c3'),
                'ALTA':rc.HexColor('#fde8c8'),'CRITICA':rc.HexColor('#fcd0d0')}
    col_est  = {'PENDIENTE':rc.HexColor('#fcd0d0'),'EN_PROCESO':rc.HexColor('#fde8c8'),
                'CERRADO':rc.HexColor('#d1f2eb')}

    sty_pa = TableStyle([
        ('BOX',(0,0),(-1,-1),0.8,AZ),('INNERGRID',(0,0),(-1,-1),0.3,BO),
        ('BACKGROUND',(0,0),(-1,0),AZ),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('FONTSIZE',(0,0),(-1,-1),7),
        ('LEFTPADDING',(0,0),(-1,-1),2),('RIGHTPADDING',(0,0),(-1,-1),2),
        ('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),
    ])

    for i, a in enumerate(todas_acc, 1):
        prio = a['prioridad']
        est  = a['estado']
        venc_flag = a['fecha'] and a['fecha'] < today and est != 'CERRADO'
        row = [
            Paragraph(str(i), E['cb']),
            Paragraph(a['origen'], E['c']),
            Paragraph(a['tipo_doc'], E['c']),
            Paragraph(a['tipo_accion'], E['c']),
            Paragraph((a['accion'] or '')[:70], E['c']),
            Paragraph(a['responsable'], E['c']),
            Paragraph(a['fecha'], E['c']),
            Paragraph(est, ParagraphStyle('Es', parent=E['c'],
                backColor=col_est.get(est, BL))),
            Paragraph(prio, ParagraphStyle('Pr', parent=E['c'],
                backColor=col_prio.get(prio, BL))),
            Paragraph(a['area'], E['c']),
            Paragraph(a['eficacia'], E['c']),
        ]
        rows_pa.append(row)
        bg = GC if i%2==0 else BL
        sty_pa.add('BACKGROUND',(0,i),(-1,i), rc.HexColor('#fff3cd') if venc_flag else bg)

    t_pa = Table(rows_pa,
        colWidths=[8*mm,20*mm,12*mm,28*mm,55*mm,22*mm,18*mm,20*mm,15*mm,18*mm,18*mm],
        repeatRows=1)
    t_pa.setStyle(sty_pa)
    EL.append(t_pa)
    EL.append(Spacer(1,8))
    EL.append(HRFlowable(width='100%', thickness=0.8, color=BO))
    EL.append(Paragraph(f'<i>{nombre_emp} | {texto_pie}</i>', E['p']))

    doc.build(EL)
    buf.seek(0)
    return buf.read()


# ── Página: Selección de carpeta de almacenamiento ───────────────────────────
def page_seleccionar_carpeta():
    st.markdown("""
    <div class="inst-header-main">
        <div class="inst-title">🔧 Sistema ACR / AFA — Gestión Documental de Mantenimiento</div>
        <div class="inst-sub">Paso 1 de 2 · Seleccione su carpeta de almacenamiento</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""
    Toda la información de sus ACR y AFA (formularios, análisis, evidencias e
    histórico) se guarda en **una carpeta que usted elige**. Esa carpeta funciona
    como su "espacio de trabajo": ahí vivirán la base de datos, los usuarios que
    usted registre como administrador, y el historial completo de documentos.
    """)

    with st.form("form_carpeta"):
        carpeta = st.text_input(
            "Ruta de la carpeta de almacenamiento",
            value=st.session_state.get('_ultima_carpeta', str(Path.home() / "ACR_AFA_Data")),
            help="Ejemplo local/Windows: C:\\ACR_AFA\\Data · Ejemplo Linux/servidor: /home/usuario/ACR_AFA_Data. "
                 "Si la carpeta no existe, se creará automáticamente."
        )
        conectar = st.form_submit_button("📂 Conectar / Crear carpeta", type="primary")

    if conectar:
        carpeta = (carpeta or "").strip()
        if not carpeta:
            st.error("Ingrese una ruta de carpeta valida.")
        else:
            try:
                os.makedirs(carpeta, exist_ok=True)
                # Prueba de escritura
                test_file = os.path.join(carpeta, ".write_test")
                with open(test_file, "w") as f:
                    f.write("ok")
                os.remove(test_file)
                st.session_state['workspace_path'] = carpeta
                st.session_state['_ultima_carpeta'] = carpeta
                st.session_state.pop('_db_conn', None)
                st.session_state.pop('_db_conn_path', None)
                st.success(f"Carpeta conectada: `{carpeta}`")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo usar esa carpeta: {e}")

    st.markdown("---")
    st.markdown("#### 📦 ¿Ya tiene un histórico respaldado (archivo .db)?")
    st.caption(
        "Si esta aplicación corre en un servicio en la nube con almacenamiento "
        "temporal (por ejemplo Streamlit Community Cloud), el disco puede "
        "reiniciarse. Para no perder su histórico, descargue periódicamente el "
        "respaldo desde el menú 'Backup / Restaurar' y, si es necesario, "
        "restáurelo aquí antes de continuar."
    )
    restaurar_file = st.file_uploader("Restaurar archivo acr_afa_system.db en la carpeta indicada arriba",
                                       type=["db"], key="restore_upload_inicial")
    if restaurar_file is not None:
        carpeta_dest = (carpeta or st.session_state.get('_ultima_carpeta') or "").strip()
        if not carpeta_dest:
            st.warning("Primero indique y conecte la carpeta arriba.")
        elif st.button("♻️ Restaurar histórico en esa carpeta"):
            try:
                os.makedirs(carpeta_dest, exist_ok=True)
                destino = os.path.join(carpeta_dest, DB_FILENAME)
                with open(destino, "wb") as f:
                    f.write(restaurar_file.read())
                st.session_state['workspace_path'] = carpeta_dest
                st.session_state.pop('_db_conn', None)
                st.session_state.pop('_db_conn_path', None)
                st.success("Histórico restaurado. Conectando...")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo restaurar el archivo: {e}")

# ── Página: Login ─────────────────────────────────────────────────────────────
def page_login():
    cfg = get_empresa_cfg()
    nombre_emp = cfg.get('nombre_empresa') or 'Sistema ACR / AFA'
    st.markdown(f"""
    <div class="inst-header-main">
        <div class="inst-title">🔧 {nombre_emp}</div>
        <div class="inst-sub">Paso 2 de 2 · Inicie sesión · Carpeta activa: {st.session_state.get('workspace_path')}</div>
    </div>""", unsafe_allow_html=True)

    if not existe_algun_usuario():
        st.info(
            "Esta carpeta aún no tiene usuarios. Cree la cuenta de **administrador** "
            "para este espacio de trabajo. Como administrador, podrá luego crear "
            "el acceso de los demás usuarios."
        )
        with st.form("form_primer_admin"):
            c1, c2 = st.columns(2)
            u = c1.text_input("Usuario (sin espacios)")
            n = c2.text_input("Nombre completo")
            c3, c4 = st.columns(2)
            p1 = c3.text_input("Contraseña", type="password")
            p2 = c4.text_input("Confirmar contraseña", type="password")
            crear = st.form_submit_button("👑 Crear administrador", type="primary")
        if crear:
            if not u or not p1:
                st.error("Usuario y contraseña son obligatorios.")
            elif p1 != p2:
                st.error("Las contraseñas no coinciden.")
            elif len(p1) < 4:
                st.error("La contraseña debe tener al menos 4 caracteres.")
            else:
                try:
                    crear_usuario(u, p1, nombre_completo=n, rol="admin", creado_por="sistema")
                    st.success("Administrador creado. Ahora inicie sesión.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        st.markdown("---")
        if st.button("⬅️ Cambiar carpeta de almacenamiento"):
            st.session_state.pop('workspace_path', None)
            st.rerun()
        return

    with st.form("form_login"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        ingresar = st.form_submit_button("🔓 Ingresar", type="primary")
    if ingresar:
        user = autenticar_usuario(u, p)
        if user:
            st.session_state['usuario'] = user
            st.success(f"Bienvenido, {user.get('nombre_completo') or user.get('username')}.")
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos, o el usuario está inactivo.")

    st.markdown("---")
    if st.button("⬅️ Cambiar carpeta de almacenamiento"):
        st.session_state.pop('workspace_path', None)
        st.rerun()

# ── Página: Gestión de Usuarios (solo admin) ─────────────────────────────────
def page_usuarios():
    show_header()
    st.markdown("## 👥 Gestión de Usuarios")
    st.caption("Como administrador, usted otorga el acceso a este espacio de trabajo (carpeta) "
               "a las personas que agregue aquí.")

    usuario_actual = st.session_state.get('usuario') or {}

    st.markdown("### ➕ Agregar nuevo usuario")
    with st.form("form_nuevo_usuario", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nu_user = c1.text_input("Usuario (sin espacios) *")
        nu_nombre = c2.text_input("Nombre completo")
        c3, c4 = st.columns(2)
        nu_pass = c3.text_input("Contraseña *", type="password")
        nu_rol = c4.selectbox("Rol", ["usuario", "admin"])
        nu_area = st.text_input("Área / Cargo (opcional)")
        agregar = st.form_submit_button("💾 Agregar usuario", type="primary")
    if agregar:
        try:
            crear_usuario(nu_user, nu_pass, nombre_completo=nu_nombre, rol=nu_rol,
                          area=nu_area, creado_por=usuario_actual.get('username',''))
            st.success(f"Usuario '{nu_user}' creado correctamente.")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    st.markdown("---")
    st.markdown("### 📋 Usuarios con acceso a esta carpeta")
    usuarios = listar_usuarios()
    if not usuarios:
        st.info("No hay usuarios registrados.")
        return

    for u in usuarios:
        u = dict(u)
        es_yo = u['username'] == usuario_actual.get('username')
        with st.expander(
            f"{'👑' if u['rol']=='admin' else '👤'} **{u['username']}**"
            f"{' (tú)' if es_yo else ''} — {u.get('nombre_completo') or 'sin nombre'}"
            f" — {'🟢 Activo' if u['activo'] else '🔴 Inactivo'}"
        ):
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Rol:** {u['rol']}")
            c1.write(f"**Área:** {u.get('area') or '—'}")
            c2.write(f"**Creado por:** {u.get('creado_por') or '—'}")
            c2.write(f"**Alta:** {u.get('fecha_creacion') or '—'}")
            c3.write(f"**Último acceso:** {u.get('ultimo_acceso') or 'Nunca'}")

            b1, b2, b3, b4 = st.columns(4)
            # Activar / desactivar
            if u['activo']:
                puede_desactivar = not (u['rol'] == 'admin' and contar_admins_activos() <= 1)
                if b1.button("🔴 Desactivar", key=f"deact_{u['id']}", disabled=not puede_desactivar):
                    db_run("UPDATE usuarios SET activo=0 WHERE id=?", (u['id'],))
                    st.rerun()
                if not puede_desactivar:
                    st.caption("No se puede desactivar al único administrador activo.")
            else:
                if b1.button("🟢 Activar", key=f"act_{u['id']}"):
                    db_run("UPDATE usuarios SET activo=1 WHERE id=?", (u['id'],))
                    st.rerun()

            # Cambiar rol
            nuevo_rol = "usuario" if u['rol'] == "admin" else "admin"
            puede_cambiar_rol = not (u['rol'] == 'admin' and contar_admins_activos() <= 1)
            if b2.button(f"↔️ Hacer {nuevo_rol}", key=f"rol_{u['id']}", disabled=not puede_cambiar_rol):
                db_run("UPDATE usuarios SET rol=? WHERE id=?", (nuevo_rol, u['id']))
                st.rerun()

            # Resetear contraseña
            with b3.popover("🔑 Resetear contraseña"):
                np1 = st.text_input("Nueva contraseña", type="password", key=f"np_{u['id']}")
                if st.button("Guardar nueva contraseña", key=f"npbtn_{u['id']}"):
                    if len(np1 or "") < 4:
                        st.error("Mínimo 4 caracteres.")
                    else:
                        cambiar_password(u['username'], np1)
                        st.success("Contraseña actualizada.")

            # Eliminar
            puede_eliminar = not es_yo and not (u['rol'] == 'admin' and contar_admins_activos() <= 1)
            if b4.button("🗑 Eliminar", key=f"del_{u['id']}", disabled=not puede_eliminar):
                db_run("DELETE FROM usuarios WHERE id=?", (u['id'],))
                st.rerun()

# ── Página: Backup / Restaurar histórico ─────────────────────────────────────
def page_backup():
    show_header()
    st.markdown("## 💾 Backup / Restaurar histórico")
    st.markdown(f"**Carpeta de almacenamiento activa:** `{st.session_state.get('workspace_path')}`")

    st.info(
        "Este archivo contiene **todo** el histórico: documentos ACR/AFA, análisis, "
        "planes de acción, evidencias fotográficas y usuarios de esta carpeta. "
        "Descárguelo periódicamente como respaldo, especialmente si la aplicación "
        "corre en un servicio con almacenamiento temporal."
    )

    path = workspace_db_path()
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            data = f.read()
        st.download_button(
            "⬇️ Descargar respaldo completo (.db)",
            data,
            file_name=f"acr_afa_backup_{datetime.date.today().isoformat()}.db",
            mime="application/octet-stream",
            type="primary"
        )
        st.caption(f"Tamaño actual: {len(data)/1024:.1f} KB")
    else:
        st.warning("Aún no hay base de datos generada en esta carpeta.")

    st.markdown("---")
    st.markdown("### ♻️ Restaurar desde un respaldo")
    st.caption(
        "Al restaurar, el archivo subido reemplazará la base de datos actual de "
        "esta carpeta (documentos, usuarios e histórico). Use esto con cuidado."
    )
    up = st.file_uploader("Seleccionar archivo .db de respaldo", type=["db"], key="restore_upload_backup_page")
    if up is not None and st.button("♻️ Restaurar (reemplaza la data actual)"):
        try:
            # Cerrar conexion activa antes de sobrescribir el archivo
            conn = st.session_state.pop('_db_conn', None)
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            st.session_state.pop('_db_conn_path', None)
            with open(path, "wb") as f:
                f.write(up.read())
            st.success("Histórico restaurado correctamente.")
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo restaurar: {e}")

# ==============================================================================
# NAVEGACION PRINCIPAL
# ==============================================================================
def main():
    # Inicializar estado de sesion
    if 'pagina' not in st.session_state:
        st.session_state['pagina'] = 'dashboard'
    if 'doc_codigo' not in st.session_state:
        st.session_state['doc_codigo'] = None
    if 'doc_tipo' not in st.session_state:
        st.session_state['doc_tipo'] = 'ACR'

    # Paso 1: exigir carpeta de almacenamiento antes de mostrar cualquier dato
    if not st.session_state.get('workspace_path'):
        page_seleccionar_carpeta()
        return

    # Paso 2: exigir inicio de sesion (usuarios del espacio de trabajo activo)
    if not st.session_state.get('usuario'):
        page_login()
        return

    usuario_actual = st.session_state['usuario']
    es_admin = usuario_actual.get('rol') == 'admin'

    # Sidebar
    with st.sidebar:
        st.markdown(
            f"**👤 {usuario_actual.get('nombre_completo') or usuario_actual.get('username')}**  \n"
            f"`{usuario_actual.get('username')}` · {'👑 admin' if es_admin else 'usuario'}"
        )
        st.caption(f"📁 {st.session_state.get('workspace_path')}")
        cs1, cs2 = st.columns(2)
        if cs1.button("🚪 Salir", use_container_width=True):
            st.session_state.pop('usuario', None)
            st.rerun()
        if cs2.button("🔁 Cambiar carpeta", use_container_width=True):
            st.session_state.pop('usuario', None)
            st.session_state.pop('workspace_path', None)
            st.session_state.pop('_db_conn', None)
            st.session_state.pop('_db_conn_path', None)
            st.rerun()
        st.markdown("---")
        cfg = get_empresa_cfg()
        logo_b = cfg.get('logo_blob')
        if logo_b:
            try:
                st.image(Image.open(io.BytesIO(logo_b)), use_container_width=True)
            except Exception:
                pass

        st.markdown(f"### {cfg.get('nombre_empresa','SISTEMA ACR/AFA')}")
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

        if es_admin:
            if st.button("👥 Gestión de Usuarios", use_container_width=True):
                st.session_state['pagina'] = 'usuarios'
                st.rerun()

        if st.button("💾 Backup / Restaurar", use_container_width=True):
            st.session_state['pagina'] = 'backup'
            st.rerun()

        st.markdown("---")
        st.markdown("""
        <small style='color:#adb5bd'>
        v12.0.0 | ISO 9001 · ISO 14224<br>
        TPM · RCM · ORICA Standards<br>
        Multiusuario · Histórico por carpeta<br>
        CAVA — Roger Huamani
        </small>""", unsafe_allow_html=True)

    # Enrutador de páginas
    pagina = st.session_state.get('pagina', 'dashboard')
    if pagina == 'dashboard':
        page_dashboard()
    elif pagina == 'form':
        page_form()
    elif pagina == 'listado':
        page_listado()
    elif pagina == 'config':
        page_config_empresa()
    elif pagina == 'plan_accion':
        page_plan_accion()
    elif pagina == 'usuarios':
        if es_admin:
            page_usuarios()
        else:
            st.error("Solo el administrador puede acceder a esta sección.")
            page_dashboard()
    elif pagina == 'backup':
        page_backup()
    else:
        page_dashboard()

if __name__ == "__main__":
    main()
