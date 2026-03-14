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

app = Flask(__name__)
CORS(app)

# ── Logo — embedded as base64 so no file dependency ──────────
LOGO_B64 = os.environ.get('LOGO_B64', '')

MESES = ['enero','febrero','marzo','abril','mayo','junio',
         'julio','agosto','septiembre','octubre','noviembre','diciembre']

def fecha_es(d):
    return f'{d.day} de {MESES[d.month-1]} de {d.year}'

# ── Colors ────────────────────────────────────────────────────
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

PESOS = {'ac': 0.35, 'ai': 0.35, 'em': 0.10, 'ep': 0.10, 'ef': 0.20}
PESOS_LABEL = {'ac': '35%', 'ai': '35%', 'em': '10%', 'ep': '10%', 'ef': '20%'}
COMP_LABELS = {'ac': 'AC', 'ai': 'AI', 'em': 'EM', 'ep': 'EP', 'ef': 'EF'}

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

def sty(name, **kw):
    d = dict(fontSize=7.5, textColor=NAVY, leading=10, fontName='Helvetica')
    d.update(kw)
    return ParagraphStyle(name, **d)

def calc_nft(notas_map, comps):
    vals = [notas_map.get(c) for c in comps]
    if any(v is None for v in vals):
        return None
    return sum(notas_map[c] * PESOS[c] for c in comps)

def nota_p(v, fs=7.5, big=False):
    return Paragraph(
        f'{v:.2f}' if v is not None else '—',
        ParagraphStyle('np', fontSize=fs + (0.5 if big else 0),
                       textColor=nota_color(v),
                       fontName='Helvetica-Bold' if v is not None else 'Helvetica',
                       alignment=TA_CENTER, leading=int(fs) + 2))

def generar_boleta(data):
    """
    data = {
        estudiante: { nombre, apellido, grado, nivel, encargado },
        year: int,
        periodo: int (1-4, or 0 for anual),
        periodo_label: str,
        num_periodos: int,
        periodo_term: str,
        componentes: ['ac','ai','em','ef'],
        materias: [{ nombre, notas: {ac,ai,em,ef} }],
        ingles: { nombre_curso, notas: {ac,ai,...} } | null,
        competencias_valores: { 'diseño_original_1': 'E', ... } | null,
    }
    """
    est         = data['estudiante']
    year        = data['year']
    periodo_label = data['periodo_label']
    num_periodos  = data['num_periodos']
    periodo_term  = data['periodo_term']
    componentes   = [c.lower() for c in data['componentes']]
    materias      = data['materias']
    ingles        = data.get('ingles')
    comp_valores  = data.get('competencias_valores', {}) or {}
    nivel         = est['nivel']
    competencias  = COMPETENCIAS_CONFIG.get(nivel, [])

    comp_labels_upper = [COMP_LABELS[c] for c in componentes]
    pesos_labels_list = [PESOS_LABEL[c] for c in componentes]

    fs_grade = 7.5
    fs_comp  = 7
    pad      = 3

    buf = io.BytesIO()
    PAGE = landscape(letter)
    ML, MR, MT, MB = 1.4*cm, 1.4*cm, 0.9*cm, 1.1*cm
    doc = SimpleDocTemplate(buf, pagesize=PAGE,
        leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB)
    story = []

    # ── LOGO ─────────────────────────────────────────────────
    logo_b64 = LOGO_B64
    if logo_b64:
        logo_bytes = base64.b64decode(logo_b64)
        logo_img = Image(io.BytesIO(logo_bytes), width=1.8*cm, height=1.8*cm)
    else:
        logo_img = Spacer(1.8*cm, 1.8*cm)

    # ── HEADER ───────────────────────────────────────────────
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

    # ── STUDENT INFO ─────────────────────────────────────────
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

    # ── GRADES TABLE ─────────────────────────────────────────
    cw = [None] + [1.22*cm]*len(componentes) + [1.45*cm]
    TH_S  = sty('THS', textColor=WHITE, fontName='Helvetica-Bold',
                alignment=TA_CENTER, fontSize=fs_grade, leading=int(fs_grade)+2)
    TH2_S = sty('TH2S', textColor=GOLD_LT, fontName='Helvetica',
                alignment=TA_CENTER, fontSize=fs_grade-1.5, leading=int(fs_grade))
    TDL_S = sty('TDLS', alignment=TA_LEFT, fontSize=fs_grade, textColor=NAVY,
                leading=int(fs_grade)+2)
    NFT_H = sty('NFTH', textColor=GOLD_LT, fontName='Helvetica-Bold',
                alignment=TA_CENTER, fontSize=fs_grade, leading=int(fs_grade)+2)

    rows = [
        [Paragraph('ASIGNATURAS', TH_S)] +
        [Paragraph(c, TH_S) for c in comp_labels_upper] +
        [Paragraph('NFT', NFT_H)],
        [Paragraph('', TH2_S)] +
        [Paragraph(p, TH2_S) for p in pesos_labels_list] +
        [Paragraph('', TH2_S)],
    ]
    for m in materias:
        notas = {k.lower(): v for k, v in (m.get('notas') or {}).items()}
        nft   = calc_nft(notas, componentes)
        row   = [Paragraph(m['nombre'], TDL_S)]
        for c in componentes:
            row.append(nota_p(notas.get(c), fs=fs_grade))
        row.append(nota_p(nft, fs=fs_grade, big=True))
        rows.append(row)

    grade_tbl = Table(rows, colWidths=cw, repeatRows=2)
    grade_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY2),
        ('BACKGROUND', (0,1), (-1,1), NAVY3),
        ('LINEABOVE', (0,0), (-1,0), 2, GOLD),
        ('ROWBACKGROUNDS', (0,2), (-1,-1), [WHITE, ROW_ALT]),
        ('LINEBELOW', (0,1), (-1,-1), 0.3, LGRAY),
        ('LINEBEFORE', (1,0), (-1,-1), 0.3, colors.HexColor('#ccd4e8')),
        ('LINEAFTER', (-2,0), (-2,-1), 1, BORDER),
        ('BACKGROUND', (-1,2), (-1,-1), NFT_BG),
        ('BOX', (0,0), (-1,-1), 0.8, NAVY),
        ('TOPPADDING', (0,0), (-1,-1), pad),
        ('BOTTOMPADDING', (0,0), (-1,-1), pad),
        ('LEFTPADDING', (0,0), (0,-1), 8),
        ('LEFTPADDING', (1,0), (-1,-1), 2), ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(grade_tbl)

    # ── CURSOS COMPLEMENTARIOS (inglés, secundaria/bachillerato) ──
    if ingles:
        story.append(Spacer(1, 3))
        comp_hdr = Table([[Paragraph('CURSOS COMPLEMENTARIOS', TH_S)]], colWidths=[None])
        comp_hdr.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), NAVY2),
            ('LINEABOVE', (0,0), (-1,-1), 2, GOLD),
            ('TOPPADDING', (0,0), (-1,-1), pad), ('BOTTOMPADDING', (0,0), (-1,-1), pad),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(comp_hdr)

        ing_notas = {k.lower(): v for k, v in (ingles.get('notas') or {}).items()}
        ing_nft   = calc_nft(ing_notas, componentes)
        ING_TH = sty('ITH', textColor=WHITE, fontName='Helvetica-Bold',
                     alignment=TA_CENTER, fontSize=fs_grade-0.5, leading=int(fs_grade)+1)
        ing_rows = [
            [Paragraph('CURSO COMPLEMENTARIO', ING_TH)] +
            [Paragraph(c, ING_TH) for c in comp_labels_upper] +
            [Paragraph('PROMEDIO', ING_TH)],
            [Paragraph(ingles.get('nombre_curso', 'English'), TDL_S)] +
            [nota_p(ing_notas.get(c), fs=fs_grade) for c in componentes] +
            [nota_p(ing_nft, fs=fs_grade, big=True)],
        ]
        ing_tbl = Table(ing_rows, colWidths=cw)
        ing_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), NAVY3),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE]),
            ('LINEBELOW', (0,0), (-1,-1), 0.3, LGRAY),
            ('LINEBEFORE', (1,0), (-1,-1), 0.3, colors.HexColor('#ccd4e8')),
            ('LINEAFTER', (-2,0), (-2,-1), 1, BORDER),
            ('BOX', (0,0), (-1,-1), 0.8, NAVY),
            ('TOPPADDING', (0,0), (-1,-1), pad), ('BOTTOMPADDING', (0,0), (-1,-1), pad),
            ('LEFTPADDING', (0,0), (0,-1), 8),
            ('LEFTPADDING', (1,0), (-1,-1), 2), ('RIGHTPADDING', (0,0), (-1,-1), 2),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(ing_tbl)

    story.append(Spacer(1, 6))

    # ── ESCALA + COMPETENCIAS CIUDADANAS ─────────────────────
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
        COMP_VAL = sty('CVAL', fontSize=fs_comp, textColor=NAVY, fontName='Helvetica-Bold',
                        alignment=TA_CENTER, leading=int(fs_comp)+2)

        # Map competencia key → valor (E/MB/B)
        COMP_KEY_MAP = {
            'diseño_original_1': 0, 'diseño_original_2': 1,
            'ed_cristiana_1': 0,    'ed_cristiana_2': 1,
        }

        n_extra = num_periodos + 1
        comp_rows = [[Paragraph('COMPETENCIAS CIUDADANAS', COMP_TH2)] +
                     [Paragraph(t, COMP_TH2) for t in t_labels] +
                     [Paragraph('PROM', COMP_TH2)]]

        for grupo, items in competencias:
            comp_rows.append([Paragraph(grupo, COMP_GH2)] + ['']*n_extra)
            for item in items:
                # Empty cells for E/MB/B marking
                comp_rows.append(
                    [Paragraph(item, COMP_IT2)] +
                    [Paragraph('', COMP_VAL)]*num_periodos +
                    [Paragraph('', COMP_VAL)]
                )

        p_cw = 2.2*cm
        comp_cw2 = [None] + [p_cw]*num_periodos + [1.6*cm]
        ts = [
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
            ts += [('BACKGROUND', (0,row_idx), (-1,row_idx), COMP_GRP),
                   ('SPAN', (1,row_idx), (-1,row_idx))]
            row_idx += 1
            for _ in items:
                ts.append(('BACKGROUND', (0,row_idx), (-1,row_idx), WHITE))
                row_idx += 1

        comp_tbl2 = Table(comp_rows, colWidths=comp_cw2)
        comp_tbl2.setStyle(TableStyle(ts))

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

    # ── "Rogamos" ────────────────────────────────────────────
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        'Rogamos que pueda leer detenidamente el presente informe de calificaciones. '
        '<b>Nota mínima de aprobación: 7.0</b>',
        sty('NM', fontSize=7, textColor=GRAY, alignment=TA_RIGHT, leading=10)))
    story.append(Spacer(1, 12))

    # ── FIRMAS ───────────────────────────────────────────────
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


# ── Routes ────────────────────────────────────────────────────

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
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
