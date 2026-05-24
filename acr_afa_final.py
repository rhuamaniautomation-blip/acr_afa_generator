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
/* Encabezado institucional */
.inst-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #2a5a8c 100%);
    color: white; padding: 16px 24px; border-radius: 8px;
    margin-bottom: 18px; display: flex; align-items: center; gap: 16px;
}
.inst-title { font-size: 1.45rem; font-weight: 700; letter-spacing: .5px; }
.inst-subtitle { font-size: .85rem; opacity: .85; }

/* Secciones */
.seccion-band {
    background: #1e60a8; color: white; font-weight: 700;
    padding: 6px 14px; border-radius: 4px; margin: 14px 0 6px 0;
    font-size: .95rem;
}
/* Tarjetas de documento */
.doc-card {
    border: 1px solid #dee2e6; border-radius: 8px;
    padding: 14px 18px; margin-bottom: 10px;
    background: #f8f9fa;
    transition: box-shadow .15s;
}
.doc-card:hover { box-shadow: 0 4px 12px rgba(30,58,95,.15); }

/* Badge de estado */
.badge-BORRADOR     { background:#6c757d; color:white; border-radius:4px; padding:2px 8px; font-size:.78rem; }
.badge-EN_ANALISIS  { background:#0d6efd; color:white; border-radius:4px; padding:2px 8px; font-size:.78rem; }
.badge-REVISADO     { background:#ffc107; color:#212529; border-radius:4px; padding:2px 8px; font-size:.78rem; }
.badge-APROBADO     { background:#198754; color:white; border-radius:4px; padding:2px 8px; font-size:.78rem; }
.badge-CERRADO      { background:#212529; color:white; border-radius:4px; padding:2px 8px; font-size:.78rem; }
.badge-RECHAZADO    { background:#dc3545; color:white; border-radius:4px; padding:2px 8px; font-size:.78rem; }

/* Tabla WW */
.ww-arrow { color: #1e60a8; font-weight: bold; font-size: 1.1rem; }

/* Prioridad */
.prio-BAJA    { background:#d1f2eb; border-radius:3px; padding:2px 6px; font-size:.8rem; }
.prio-MEDIA   { background:#fef9c3; border-radius:3px; padding:2px 6px; font-size:.8rem; }
.prio-ALTA    { background:#fde8c8; border-radius:3px; padding:2px 6px; font-size:.8rem; }
.prio-CRITICA { background:#fcd0d0; border-radius:3px; padding:2px 6px; font-size:.8rem; font-weight:bold; }

/* Botones de accion */
div.stButton > button {
    border-radius: 6px; font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# BASE DE DATOS — Singleton con caché de sesión
# ==============================================================================
DB_PATH = "acr_afa_system.db"

@st.cache_resource
def get_db():
    """Crea y cachea la conexión a SQLite."""
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

    CATEGORIAS_6M = {
        "MAQUINA": ["Lubricacion","Ajuste","Limpieza","Confiabilidad","Operatividad","Instalacion","Fabricacion"],
        "MATERIAL": ["Seleccion correcta de componentes","Materiales","Especificacion"],
        "MANO DE OBRA": ["Gente","Operador/mantenedor"],
        "METODO": ["Proceso","Estándares de operacion","Diseño"],
        "MEDICION": ["Confiabilidad de datos"],
        "MEDIO AMBIENTE": ["Ambientales"],
    }

    conds_db = {f"{r['categoria_6m']}|{r['item']}": dict(r)
                for r in db_query("SELECT * FROM condiciones_basicas WHERE codigo_acr=?", (codigo,))}

    cambios = []
    for cat, items in CATEGORIAS_6M.items():
        st.markdown(f"**{cat}**")
        for item in items:
            key = f"{cat}|{item}"
            existing = conds_db.get(key, {})
            with st.expander(f"  {item}", expanded=False):
                cc1, cc2 = st.columns(2)
                ideal   = cc1.text_area("Condicion Ideal",  value=existing.get('condicion_ideal',''),  key=f"ci_{key}")
                actual  = cc2.text_area("Condicion Actual (Hallazgo)", value=existing.get('condicion_actual',''), key=f"ca_{key}")
                cr1, cr2 = st.columns(2)
                aplica  = cr1.selectbox("Aplica", ['SI','NO'],
                    index=0 if existing.get('aplica','SI')=='SI' else 1, key=f"ap_{key}")
                diferencia = cr2.selectbox("Existe Diferencia", ['NO','SI'],
                    index=0 if existing.get('diferencia','NO')=='NO' else 1, key=f"df_{key}")
                cambios.append((cat, item, ideal, actual, aplica, diferencia, existing.get('id')))

    if st.button("💾 Guardar Condiciones 6M", type="primary", key="save_6m"):
        for cat, item, ideal, actual, aplica, diferencia, id_exist in cambios:
            if id_exist:
                db_run("""UPDATE condiciones_basicas SET condicion_ideal=?,condicion_actual=?,aplica=?,diferencia=?
                    WHERE id=?""", (ideal, actual, aplica, diferencia, id_exist))
            else:
                db_run("""INSERT INTO condiciones_basicas
                    (codigo_acr,categoria_6m,item,condicion_ideal,condicion_actual,aplica,diferencia)
                    VALUES(?,?,?,?,?,?,?)""", (codigo, cat, item, ideal, actual, aplica, diferencia))
        st.success("✅ Condiciones 6M guardadas.")
        st.rerun()

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
    f_busq   = fc3.text_input("Buscar (codigo, descripcion, responsable)...")

    sql = "SELECT * FROM documentos WHERE 1=1"
    params = []
    if f_tipo != 'TODOS':
        sql += " AND tipo_documento=?"; params.append(f_tipo)
    if f_estado != 'TODOS':
        sql += " AND estado=?"; params.append(f_estado)
    if f_busq:
        sql += " AND (codigo LIKE ? OR desc_problema_inicial LIKE ? OR responsables LIKE ? OR reportado_por LIKE ?)"
        b = f"%{f_busq}%"
        params.extend([b,b,b,b])
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
                               file_name=f"{sel_cod}.pdf",
                               mime="application/pdf",
                               key="dl_list")
        if bc.button("🗑 Eliminar"):
            db_run("DELETE FROM documentos WHERE codigo=?", (sel_cod,))
            st.success(f"Documento {sel_cod} eliminado.")
            st.rerun()

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

    # Sidebar
    with st.sidebar:
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

        st.markdown("---")
        st.markdown("""
        <small style='color:#6c757d'>
        v10.0.0 | ISO 9001 · ISO 14224<br>
        TPM · RCM · ORICA Standards<br>
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
    else:
        page_dashboard()

if __name__ == "__main__":
    main()
