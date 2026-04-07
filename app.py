import io
import os
import base64
from datetime import date
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from pypdf import PdfWriter, PdfReader

app = Flask(__name__)
CORS(app)

LOGO_B64 = os.environ.get('LOGO_B64', '')

MESES = ['enero','febrero','marzo','abril','mayo','junio',
         'julio','agosto','septiembre','octubre','noviembre','diciembre']

def fecha_es(d):
    return f'{d.day} de {MESES[d.month-1]} de {d.year}'

# ── Colors ──────────────────────────────────────────────────
NAVY    = colors.HexColor('#0f1d40')
NAVY2   = colors.HexColor('#1a2d5a')
NAVY3   = colors.HexColor('#223468')
GOLD    = colors.HexColor('#C9A84C')
GOLD_LT = colors.HexColor('#F5EDD0')
WHITE   = colors.white
ROW_ALT = colors.HexColor('#F4F7FC')
BORDER  = colors.HexColor('#C8D3E8')
LGRAY   = colors.HexColor('#DDE4F0')
GRAY    = colors.HexColor('#6B7385')
RED     = colors.HexColor('#C0392B')
GREEN   = colors.HexColor('#1A7A4A')
AMBER   = colors.HexColor('#946A00')
NFT_BG  = colors.HexColor('#EBF0FA')
COMP_GRP= colors.HexColor('#EEF1F9')
LIGHT_BG= colors.HexColor('#F0F4FB')

PESOS       = {'ac': 0.35, 'ai': 0.35, 'em': 0.10, 'ep': 0.10, 'ef': 0.20}
COMP_LABELS = {'ac': 'AC', 'ai': 'AI', 'em': 'EM', 'ep': 'EP', 'ef': 'EF'}
PESOS_LABEL = {'ac': '35%', 'ai': '35%', 'em': '10%', 'ep': '10%', 'ef': '20%'}

COMPETENCIAS_CONFIG = {
    'primera_infancia': [
        ('EDUCACIÓN CRISTIANA', [
            'Apertura al plan de formación cristiana',
            'Participación activa en el plan de formación cristiana',
        ]),
    ],
    'primaria': [
        ('DISEÑO ORIGINAL', [
            'Atiende con respeto las temáticas abordadas',
            'Participación activa en el plan de diseño original',
        ]),
        ('EDUCACIÓN CRISTIANA', [
            'Apertura al plan de formación cristiana',
            'Participación activa en el plan de formación cristiana',
        ]),
    ],
    'secundaria': [
        ('EDUCACIÓN CRISTIANA', [
            'Apertura al plan de formación cristiana',
            'Participación activa en el plan de formación cristiana',
        ]),
    ],
    'bachillerato': [],
}

def nota_color(n):
    if n is None: return GRAY
    if n < 5:     return RED
    if n < 7:     return AMBER
    return GREEN

def calc_nft(notas_map, comps):
    vals = [notas_map.get(c) for c in comps]
    if any(v is None for v in vals):
        return None
    return sum(notas_map[c] * PESOS[c] for c in comps)

def sty(name, **kw):
    d = dict(fontSize=7.5, textColor=NAVY, leading=10, fontName='Helvetica')
    d.update(kw)
    return ParagraphStyle(name, **d)

def nota_p(v, fs=7.5, big=False):
    return Paragraph(
        f'{v:.2f}' if v is not None else '—',
        ParagraphStyle(f'np', fontSize=fs + (0.5 if big else 0),
                       textColor=nota_color(v),
                       fontName='Helvetica-Bold' if v is not None else 'Helvetica',
                       alignment=TA_CENTER, leading=int(fs) + 2))

def generar_boleta(data):
    est          = data['estudiante']
    year         = data['year']
    periodo_label= data['periodo_label']
    num_periodos = data['num_periodos']
    periodo_term = data['periodo_term']
    componentes  = [c.lower() for c in data['componentes']]
    materias     = data['materias']
    ingles       = data.get('ingles')
    nivel        = est['nivel']
    competencias = COMPETENCIAS_CONFIG.get(nivel, [])
    comp_valores = data.get('competencias_valores', {})  # {comp_id: {periodo: valor}}

    fs_grade = 7.5
    fs_comp  = 7
    pad      = 3

    buf = io.BytesIO()
    PAGE = landscape(letter)
    ML, MR, MT, MB = 1.4*cm, 1.4*cm, 0.9*cm, 1.1*cm
    doc = SimpleDocTemplate(buf, pagesize=PAGE,
        leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB)
    story = []

    # ── LOGO ──────────────────────────────────
    logo_b64 = LOGO_B64
    if logo_b64:
        logo_bytes = base64.b64decode(logo_b64)
        logo_img = Image(io.BytesIO(logo_bytes), width=1.8*cm, height=1.8*cm)
    else:
        logo_img = Spacer(1.8*cm, 1.8*cm)

    # ── HEADER ────────────────────────────────
    hdr_tbl = Table([[
        logo_img,
        [
            Paragraph('Colegio Bautista Internacional de Sonsonate',
                       sty('HT', fontSize=13, fontName='Helvetica-Bold', textColor=NAVY,
                           alignment=TA_CENTER, leading=16)),
            Paragraph('Fe, Cultura, Innovación y Disciplina',
                       sty('HL', fontSize=8, textColor=GOLD, alignment=TA_CENTER,
                           leading=11, fontName='Helvetica-Oblique')),
            Spacer(1, 2),
            Paragraph(f'Boleta de Calificaciones · Año {year}',
                       sty('HS', fontSize=8.5, textColor=GRAY, alignment=TA_CENTER, leading=11)),
        ],
        ''
    ]], colWidths=[2.2*cm, None, 2.2*cm])
    hdr_tbl.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(hdr_tbl)
    story.append(Table([['']], colWidths=[None], style=TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 2, GOLD),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ])))
    story.append(Spacer(1, 5))

    # ── STUDENT INFO ──────────────────────────
    LBL = sty('LBL', fontSize=6.5, textColor=GOLD, fontName='Helvetica-Bold', leading=9)
    VAL = sty('VAL', fontSize=9, textColor=NAVY, fontName='Helvetica-Bold', leading=12)

    info_tbl = Table([
        [Paragraph('Estudiante', LBL), Paragraph('Grado', LBL),
         Paragraph('Período', LBL),    Paragraph('Fecha de emisión', LBL)],
        [Paragraph(f'{est["apellido"]}, {est["nombre"]}', VAL),
         Paragraph(est['grado'], VAL),
         Paragraph(periodo_label, VAL),
         Paragraph(fecha_es(date.today()), VAL)],
    ], colWidths=[None, 4.5*cm, 3.6*cm, 3.8*cm])
    info_tbl.setStyle(TableStyle([
        ('LINEBELOW', (0,1), (-1,1), 0.8, GOLD),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('LINEBEFORE', (1,0), (-1,-1), 0.4, LGRAY),
        ('LEFTPADDING', (1,0), (-1,-1), 8),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 5))

    # ── GRADES TABLE ──────────────────────────
    N      = len(componentes)
    nota_w = 1.0*cm
    nft_w  = 1.2*cm
    acu_w  = 1.3*cm

    TH_S  = sty('THS', textColor=WHITE, fontName='Helvetica-Bold',
                alignment=TA_CENTER, fontSize=fs_grade, leading=int(fs_grade)+2)
    TH2_S = sty('TH2S', textColor=GOLD_LT, fontName='Helvetica',
                alignment=TA_CENTER, fontSize=fs_grade-1.5, leading=int(fs_grade))
    TDL_S = sty('TDLS', alignment=TA_LEFT, fontSize=fs_grade, textColor=NAVY,
                leading=int(fs_grade)+2)
    NFT_H = sty('NFTH', textColor=GOLD_LT, fontName='Helvetica-Bold',
                alignment=TA_CENTER, fontSize=fs_grade, leading=int(fs_grade)+2)
    ACU_H = sty('ACUH', textColor=GOLD_LT, fontName='Helvetica-Bold',
                alignment=TA_CENTER, fontSize=fs_grade, leading=int(fs_grade)+2)

    h1 = [Paragraph('ASIGNATURAS', TH_S)]
    for i in range(num_periodos):
        h1.append(Paragraph(f'{periodo_term} {i+1}', TH_S))
        for _ in range(N):
            h1.append('')
    h1.append(Paragraph('ACU', ACU_H))

    h2 = [Paragraph('', TH2_S)]
    for _ in range(num_periodos):
        for c in componentes:
            h2.append(Paragraph(PESOS_LABEL[c], TH2_S))
        h2.append(Paragraph('NFT', sty('NFTH2', textColor=GOLD_LT, fontName='Helvetica-Bold',
                  alignment=TA_CENTER, fontSize=fs_grade-1, leading=int(fs_grade))))
    h2.append(Paragraph('', TH2_S))

    rows = [h1, h2]
    for m in materias:
        notas_pp = m.get('notas_por_periodo', {})
        row = [Paragraph(m['nombre'], TDL_S)]
        nfts_periodo = []
        for p in range(1, num_periodos + 1):
            notas = notas_pp.get(str(p), {})
            for c in componentes:
                v = notas.get(c)
                row.append(nota_p(v, fs=fs_grade))
            nft = calc_nft(notas, componentes)
            nfts_periodo.append(nft)
            row.append(nota_p(nft, fs=fs_grade, big=True))
        validos = [n for n in nfts_periodo if n is not None]
        acu = sum(validos) / len(validos) if validos else None
        row.append(nota_p(acu, fs=fs_grade+0.5, big=True))
        rows.append(row)

    fixed_w = (N * nota_w + nft_w) * num_periodos + acu_w
    PAGE_W  = landscape(letter)[0]
    mat_w   = PAGE_W - ML - MR - fixed_w
    cw = [mat_w]
    for _ in range(num_periodos):
        cw += [nota_w] * N + [nft_w]
    cw += [acu_w]

    grade_tbl = Table(rows, colWidths=cw, repeatRows=2)
    ts = [
        ('BACKGROUND', (0,0), (-1,0), NAVY2),
        ('BACKGROUND', (0,1), (-1,1), NAVY3),
        ('LINEABOVE', (0,0), (-1,0), 2, GOLD),
        ('ROWBACKGROUNDS', (0,2), (-1,-1), [WHITE, ROW_ALT]),
        ('LINEBELOW', (0,1), (-1,-1), 0.3, LGRAY),
        ('BOX', (0,0), (-1,-1), 0.8, NAVY),
        ('TOPPADDING', (0,0), (-1,-1), pad),
        ('BOTTOMPADDING', (0,0), (-1,-1), pad),
        ('LEFTPADDING', (0,0), (0,-1), 8),
        ('LEFTPADDING', (1,0), (-1,-1), 1), ('RIGHTPADDING', (0,0), (-1,-1), 1),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (-1,2), (-1,-1), NFT_BG),
        ('LINEAFTER', (-2,0), (-2,-1), 1, BORDER),
    ]
    col = 1
    for i in range(num_periodos):
        end_col = col + N
        ts.append(('SPAN', (col, 0), (end_col, 0)))
        ts.append(('ALIGN', (col, 0), (end_col, 0), 'CENTER'))
        ts.append(('LINEBEFORE', (col, 0), (col, -1), 0.8, BORDER))
        ts.append(('BACKGROUND', (end_col, 2), (end_col, -1), colors.HexColor('#edf1fb')))
        col = end_col + 1
    grade_tbl.setStyle(TableStyle(ts))
    story.append(grade_tbl)

    # ── CURSOS COMPLEMENTARIOS ────────────────
    if ingles:
        story.append(Spacer(1, 3))
        comp_hdr = Table([[Paragraph('CURSOS COMPLEMENTARIOS', TH_S)]], colWidths=[None])
        comp_hdr.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), NAVY2),
            ('LINEABOVE', (0,0), (-1,-1), 2, GOLD),
            ('BOX', (0,0), (-1,-1), 0.8, NAVY),
            ('TOPPADDING', (0,0), (-1,-1), pad), ('BOTTOMPADDING', (0,0), (-1,-1), pad),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(comp_hdr)

        ING_TH = sty('ITH', textColor=WHITE, fontName='Helvetica-Bold',
                     alignment=TA_CENTER, fontSize=fs_grade-0.5, leading=int(fs_grade)+1)
        notas_pp = ingles.get('notas_por_periodo', {})

        ing_h1 = [Paragraph('CURSO COMPLEMENTARIO', ING_TH)]
        for i in range(num_periodos):
            ing_h1.append(Paragraph(f'{periodo_term} {i+1}', ING_TH))
            for _ in range(N):
                ing_h1.append('')
        ing_h1.append(Paragraph('PROMEDIO', ING_TH))

        ing_h2 = [Paragraph('', TH2_S)]
        for _ in range(num_periodos):
            for c in componentes:
                ing_h2.append(Paragraph(PESOS_LABEL[c], TH2_S))
            ing_h2.append(Paragraph('NFT', TH2_S))
        ing_h2.append(Paragraph('', TH2_S))

        ing_row = [Paragraph(ingles.get('nombre_curso', 'English'), TDL_S)]
        nfts = []
        for p in range(1, num_periodos + 1):
            notas = notas_pp.get(str(p), {})
            for c in componentes:
                ing_row.append(nota_p(notas.get(c), fs=fs_grade))
            nft = calc_nft(notas, componentes)
            nfts.append(nft)
            ing_row.append(nota_p(nft, fs=fs_grade, big=True))
        validos = [n for n in nfts if n is not None]
        prom = sum(validos)/len(validos) if validos else None
        ing_row.append(nota_p(prom, fs=fs_grade+0.5, big=True))

        ing_rows = [ing_h1, ing_h2, ing_row]
        ing_tbl = Table(ing_rows, colWidths=cw)
        ing_ts = [
            ('BACKGROUND', (0,0), (-1,0), NAVY3),
            ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#2a3e70')),
            ('LINEABOVE', (0,0), (-1,0), 2, GOLD),
            ('ROWBACKGROUNDS', (0,2), (-1,-1), [WHITE]),
            ('LINEBELOW', (0,0), (-1,-1), 0.3, LGRAY),
            ('BOX', (0,0), (-1,-1), 0.8, NAVY),
            ('TOPPADDING', (0,0), (-1,-1), pad), ('BOTTOMPADDING', (0,0), (-1,-1), pad),
            ('LEFTPADDING', (0,0), (0,-1), 8),
            ('LEFTPADDING', (1,0), (-1,-1), 1), ('RIGHTPADDING', (0,0), (-1,-1), 1),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (-1,2), (-1,-1), NFT_BG),
            ('LINEAFTER', (-2,0), (-2,-1), 1, BORDER),
        ]
        col2 = 1
        for i in range(num_periodos):
            end_col2 = col2 + N
            ing_ts.append(('SPAN', (col2, 0), (end_col2, 0)))
            ing_ts.append(('ALIGN', (col2, 0), (end_col2, 0), 'CENTER'))
            ing_ts.append(('LINEBEFORE', (col2, 0), (col2, -1), 0.8, BORDER))
            col2 = end_col2 + 1
        ing_tbl.setStyle(TableStyle(ing_ts))
        story.append(ing_tbl)

    story.append(Spacer(1, 6))

    # ── ESCALA + COMPETENCIAS CIUDADANAS ──────
    if competencias:
        ESC_TH = sty('ET', fontSize=fs_comp, textColor=WHITE, fontName='Helvetica-Bold',
                     alignment=TA_CENTER, leading=int(fs_comp)+2)
        ESC_V  = sty('EV', fontSize=fs_comp+0.5, textColor=NAVY, leading=int(fs_comp)+3)

        esc_tbl = Table([
            [Paragraph('ESCALA CONCEPTUAL', ESC_TH)],
            [Paragraph('<b>E</b>  — Excelente &nbsp;9 – 10', ESC_V)],
            [Paragraph('<b>MB</b> — Muy Bueno &nbsp;7 – 8',  ESC_V)],
            [Paragraph('<b>B</b>  — Bueno &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 – 6', ESC_V)],
        ], colWidths=[3.8*cm])
        esc_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), NAVY2),
            ('LINEABOVE', (0,0), (0,0), 2, GOLD),
            ('BACKGROUND', (0,1), (0,-1), LIGHT_BG),
            ('BOX', (0,0), (-1,-1), 0.7, BORDER),
            ('TOPPADDING', (0,0), (-1,-1), pad), ('BOTTOMPADDING', (0,0), (-1,-1), pad),
            ('LEFTPADDING', (0,0), (-1,-1), 8), ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))

        t_labels = [f'{periodo_term} {i+1}' for i in range(num_periodos)]
        COMP_TH2 = sty('CTH2', fontSize=fs_comp, textColor=WHITE,
                        fontName='Helvetica-Bold', alignment=TA_CENTER, leading=int(fs_comp)+2)
        COMP_GH2 = sty('CGH2', fontSize=fs_comp+0.5, fontName='Helvetica-Bold',
                        textColor=NAVY2, leading=int(fs_comp)+3)
        COMP_IT2 = sty('CIT2', fontSize=fs_comp, textColor=GRAY, leading=int(fs_comp)+2)

        n_extra = num_periodos + 1
        comp_rows = [[Paragraph('COMPETENCIAS CIUDADANAS', COMP_TH2)] +
                     [Paragraph(t, COMP_TH2) for t in t_labels] +
                     [Paragraph('PROM', COMP_TH2)]]
        # Mapeo label → id de competencia para buscar valores
        COMP_LABEL_MAP = {
            'Apertura al plan de formación cristiana':          'ed_cristiana_1',
            'Participación activa en el plan de formación cristiana': 'ed_cristiana_2',
            'Atiende con respeto las temáticas abordadas':      'diseño_original_1',
            'Participación activa en el plan de diseño original': 'diseño_original_2',
        }
        COMP_VAL_ST = ParagraphStyle('CV', fontSize=fs_comp+0.5, fontName='Helvetica-Bold',
                                      alignment=TA_CENTER, leading=int(fs_comp)+3)
        def val_color(v):
            if v == 'E':  return colors.HexColor('#16a34a')
            if v == 'MB': return colors.HexColor('#a16207')
            if v == 'B':  return colors.HexColor('#5B2D8E')
            return colors.HexColor('#9ca3af')
        def comp_p(v):
            c = val_color(v)
            st = ParagraphStyle('cpv', fontSize=fs_comp+0.5, fontName='Helvetica-Bold',
                                 textColor=c, alignment=TA_CENTER, leading=int(fs_comp)+3)
            return Paragraph(v if v else '—', st)

        for grupo, items in competencias:
            comp_rows.append([Paragraph(grupo, COMP_GH2)] + ['']*n_extra)
            for item in items:
                comp_id = COMP_LABEL_MAP.get(item, '')
                vals_item = comp_valores.get(comp_id, {})
                periodos_vals = [comp_p(vals_item.get(str(p))) for p in range(1, num_periodos+1)]
                # Promedio conceptual: E>MB>B, mayoría gana
                all_vals = [vals_item.get(str(p)) for p in range(1, num_periodos+1) if vals_item.get(str(p))]
                if all_vals:
                    rank = {'E': 3, 'MB': 2, 'B': 1}
                    avg = sum(rank.get(v, 0) for v in all_vals) / len(all_vals)
                    prom_val = 'E' if avg >= 2.5 else 'MB' if avg >= 1.5 else 'B'
                else:
                    prom_val = ''
                comp_rows.append([Paragraph(item, COMP_IT2)] + periodos_vals + [comp_p(prom_val)])

        p_cw = 2.2*cm
        comp_cw2 = [None] + [p_cw]*num_periodos + [1.6*cm]
        comp_ts = [
            ('BACKGROUND', (0,0), (-1,0), NAVY2),
            ('LINEABOVE', (0,0), (-1,0), 2, GOLD),
            ('BOX', (0,0), (-1,-1), 0.7, BORDER),
            ('LINEBELOW', (0,0), (-1,-1), 0.3, LGRAY),
            ('LINEBEFORE', (1,0), (-1,-1), 0.3, LGRAY),
            ('TOPPADDING', (0,0), (-1,-1), pad), ('BOTTOMPADDING', (0,0), (-1,-1), pad),
            ('LEFTPADDING', (0,0), (0,-1), 8),
            ('LEFTPADDING', (1,0), (-1,-1), 3), ('RIGHTPADDING', (0,0), (-1,-1), 3),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]
        row_idx = 1
        for grupo, items in competencias:
            comp_ts += [('BACKGROUND', (0,row_idx), (-1,row_idx), COMP_GRP),
                        ('SPAN', (1,row_idx), (-1,row_idx))]
            row_idx += 1
            for _ in items:
                comp_ts.append(('BACKGROUND', (0,row_idx), (-1,row_idx), WHITE))
                row_idx += 1
        comp_tbl2 = Table(comp_rows, colWidths=comp_cw2)
        comp_tbl2.setStyle(TableStyle(comp_ts))

        bottom = Table([[esc_tbl, comp_tbl2]], colWidths=[4.0*cm, None])
        bottom.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (0,0), 8),
            ('RIGHTPADDING', (1,0), (1,0), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(bottom)

    # ── Nota mínima ───────────────────────────
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        'Rogamos que pueda leer detenidamente el presente informe de calificaciones. '
        '<b>Nota mínima de aprobación: 7.0</b>',
        sty('NM', fontSize=7, textColor=GRAY, alignment=TA_RIGHT, leading=10)))
    story.append(Spacer(1, 12))

    # ── FIRMAS ────────────────────────────────
    SIGN_B3  = sty('SB3', fontSize=8.5, textColor=NAVY, fontName='Helvetica-Bold',
                   alignment=TA_CENTER, leading=12)
    SIGN_SM2 = sty('SS2', fontSize=7.5, textColor=GRAY, alignment=TA_CENTER, leading=10)

    LINE_T = lambda: Table([[''], ['']], colWidths=[6.5*cm], style=TableStyle([
        ('LINEBELOW', (0,1), (-1,1), 0.7, NAVY2),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('ROWHEIGHT', (0,0), (-1,0), 28),
        ('ROWHEIGHT', (0,1), (-1,1), 2),
    ]))

    firma_tbl = Table([
        [LINE_T(), LINE_T()],
        [Paragraph('Silvia del Carmen Rodríguez Pineda', SIGN_B3),
         Paragraph(est.get('encargado', ''), SIGN_B3)],
        [Paragraph('Directora', SIGN_SM2), Paragraph('Docente guía', SIGN_SM2)],
    ], colWidths=[None, None])
    firma_tbl.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(firma_tbl)

    doc.build(story)
    return buf.getvalue()


# ── Routes ──────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'cbis-boleta-api'})

@app.route('/generar-boleta', methods=['POST'])
def generar():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        pdf_bytes = generar_boleta(data)
        est = data['estudiante']
        filename = (
            f"boleta_{est['apellido'].replace(' ', '_')}_"
            f"{data.get('periodo_label', 'boleta').replace(' ', '_')}.pdf"
        )
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/generar-boletas-lote', methods=['POST'])
def generar_lote():
    """
    Recibe un array de estudiantes y devuelve un único PDF con todas las boletas.
    Body: { grado: str, year: int, boletas: [ { ...mismo formato que /generar-boleta } ] }
    """
    try:
        data = request.get_json()
        if not data or 'boletas' not in data:
            return jsonify({'error': 'Se requiere array "boletas"'}), 400

        boletas = data['boletas']
        if not boletas:
            return jsonify({'error': 'Array de boletas vacío'}), 400

        # Generar cada boleta y concatenar con pypdf
        writer = PdfWriter()

        for item in boletas:
            pdf_bytes = generar_boleta(item)
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                writer.add_page(page)

        # Serializar PDF combinado
        out = io.BytesIO()
        writer.write(out)
        out.seek(0)

        grado   = data.get('grado', 'grado').replace(' ', '_')
        year    = data.get('year', date.today().year)
        filename = f"boletas_finales_{grado}_{year}.pdf"

        return send_file(
            out,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
