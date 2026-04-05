#!/usr/bin/env python3
"""
Generate professional Japanese legal documents for Suhana Restaurant acquisition.
Three contracts:
1. 事業譲渡契約書 (Business Transfer Agreement)
2. 営業許可名義変更に関する合意書 (Business License Transfer Agreement)
3. 賃貸借権譲渡に関する合意書 (Lease Assignment Agreement)
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.colors import black, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

OUTPUT_DIR = '/Users/pk/Downloads/suhana/contracts'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Register Japanese CID fonts
# HeiseiMin-W3 = Mincho (serif) - formal/legal
# HeiseiKakuGo-W5 = Gothic (sans) - headings
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))

# Aliases for readability
MINCHO = 'HeiseiMin-W3'
GOTHIC = 'HeiseiKakuGo-W5'
GOTHIC_BOLD = 'HeiseiKakuGo-W5'  # CID has no separate bold; we fake with size

# Colors
DARK = HexColor('#1a1a1a')
ACCENT = HexColor('#2c3e50')
LINE_COLOR = HexColor('#333333')
LIGHT_GRAY = HexColor('#f5f5f5')

# Styles
def get_styles():
    return {
        'title': ParagraphStyle(
            'Title', fontName=GOTHIC_BOLD, fontSize=18, leading=28,
            alignment=TA_CENTER, textColor=DARK, spaceAfter=6*mm,
        ),
        'subtitle': ParagraphStyle(
            'Subtitle', fontName=GOTHIC, fontSize=10, leading=16,
            alignment=TA_CENTER, textColor=ACCENT, spaceAfter=8*mm,
        ),
        'heading': ParagraphStyle(
            'Heading', fontName=GOTHIC_BOLD, fontSize=12, leading=20,
            textColor=DARK, spaceBefore=6*mm, spaceAfter=3*mm,
            borderPadding=(0, 0, 2, 0),
        ),
        'article_title': ParagraphStyle(
            'ArticleTitle', fontName=GOTHIC_BOLD, fontSize=11, leading=18,
            textColor=DARK, spaceBefore=5*mm, spaceAfter=2*mm,
        ),
        'body': ParagraphStyle(
            'Body', fontName=MINCHO, fontSize=10, leading=18,
            alignment=TA_JUSTIFY, textColor=DARK, spaceAfter=2*mm,
            firstLineIndent=10*mm,
        ),
        'body_no_indent': ParagraphStyle(
            'BodyNoIndent', fontName=MINCHO, fontSize=10, leading=18,
            alignment=TA_LEFT, textColor=DARK, spaceAfter=2*mm,
        ),
        'small': ParagraphStyle(
            'Small', fontName=MINCHO, fontSize=8, leading=12,
            alignment=TA_LEFT, textColor=HexColor('#666666'),
        ),
        'signature_label': ParagraphStyle(
            'SigLabel', fontName=GOTHIC, fontSize=9, leading=14,
            textColor=ACCENT,
        ),
        'signature_line': ParagraphStyle(
            'SigLine', fontName=MINCHO, fontSize=10, leading=16,
            textColor=DARK,
        ),
        'right': ParagraphStyle(
            'Right', fontName=MINCHO, fontSize=10, leading=18,
            alignment=TA_RIGHT, textColor=DARK, spaceAfter=2*mm,
        ),
        'center': ParagraphStyle(
            'Center', fontName=MINCHO, fontSize=10, leading=18,
            alignment=TA_CENTER, textColor=DARK, spaceAfter=2*mm,
        ),
        'footer': ParagraphStyle(
            'Footer', fontName=GOTHIC, fontSize=7, leading=10,
            alignment=TA_CENTER, textColor=HexColor('#999999'),
        ),
    }

def add_header_line(story):
    story.append(HRFlowable(width="100%", thickness=1.5, color=LINE_COLOR,
                             spaceAfter=3*mm, spaceBefore=1*mm))

def add_thin_line(story):
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor('#cccccc'),
                             spaceAfter=3*mm, spaceBefore=3*mm))

def add_signature_block(story, styles):
    """Add professional signature block for both parties."""
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph('以上、本契約の成立を証するため、本書2通を作成し、甲乙各1通を保有する。', styles['body']))
    story.append(Spacer(1, 10*mm))

    # Date line
    story.append(Paragraph('契約締結日：　令和8年4月15日', styles['body_no_indent']))
    story.append(Spacer(1, 12*mm))

    # Party A (Buyer)
    sig_data_a = [
        [Paragraph('<b>【甲】　譲受人</b>', styles['signature_label']), ''],
        [Paragraph('商号：', styles['signature_line']),
         Paragraph('eMoment Japan合同会社', styles['signature_line'])],
        [Paragraph('所在地：', styles['signature_line']),
         Paragraph('東京都江戸川区南葛西2-6-16', styles['signature_line'])],
        [Paragraph('代表社員：', styles['signature_line']),
         Paragraph('Dipikaranimishra Sahoo　　　　　　印', styles['signature_line'])],
    ]
    t = Table(sig_data_a, colWidths=[30*mm, 120*mm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LINEBELOW', (1, 3), (1, 3), 0.5, LINE_COLOR),
    ]))
    story.append(t)
    story.append(Spacer(1, 10*mm))

    # Party B (Seller)
    sig_data_b = [
        [Paragraph('<b>【乙】　譲渡人</b>', styles['signature_label']), ''],
        [Paragraph('商号：', styles['signature_line']),
         Paragraph('RIONA株式会社', styles['signature_line'])],
        [Paragraph('所在地：', styles['signature_line']),
         Paragraph('（登記事項証明書確認後記入）', styles['signature_line'])],
        [Paragraph('代表者：', styles['signature_line']),
         Paragraph('Lamichhane Dilli Raj　　　　　　　　印', styles['signature_line'])],
    ]
    t = Table(sig_data_b, colWidths=[30*mm, 120*mm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LINEBELOW', (1, 2), (1, 2), 0.5, LINE_COLOR),
        ('LINEBELOW', (1, 3), (1, 3), 0.5, LINE_COLOR),
    ]))
    story.append(t)

def add_doc_footer(story, styles, doc_number):
    story.append(Spacer(1, 8*mm))
    add_thin_line(story)
    story.append(Paragraph(
        f'文書番号：EMT-SUHANA-{doc_number}　｜　本契約書は2通作成し、甲乙各1通を保有するものとする。',
        styles['footer']))


# ============================================================
# DOCUMENT 1: 事業譲渡契約書 (Business Transfer Agreement)
# ============================================================
def generate_business_transfer():
    styles = get_styles()
    filepath = os.path.join(OUTPUT_DIR, '01_事業譲渡契約書.pdf')
    doc = SimpleDocTemplate(filepath, pagesize=A4,
        topMargin=25*mm, bottomMargin=25*mm,
        leftMargin=22*mm, rightMargin=22*mm)
    story = []

    # Header
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('事　業　譲　渡　契　約　書', styles['title']))
    story.append(Paragraph('Business Transfer Agreement', styles['subtitle']))
    add_header_line(story)

    # Preamble
    story.append(Paragraph(
        'eMoment Japan合同会社（以下「甲」という。）とRIONA株式会社（以下「乙」という。）は、'
        '乙が営む飲食事業の譲渡に関し、以下のとおり契約（以下「本契約」という。）を締結する。',
        styles['body']))

    # Article 1
    story.append(Paragraph('第１条（事業譲渡）', styles['article_title']))
    story.append(Paragraph(
        '乙は、乙が営む下記飲食事業（以下「本事業」という。）を、本契約に定める条件に従い、甲に譲渡し、甲はこれを譲り受けるものとする。',
        styles['body']))
    story.append(Spacer(1, 2*mm))

    biz_data = [
        ['事業の名称', 'SUHANA Indian Nepal Restaurant'],
        ['事業の所在地', '東京都北区上十条五丁目14番6号'],
        ['事業の種類', '飲食店営業'],
        ['営業許可番号', '7北健生食き第168号'],
        ['営業許可有効期限', '令和7年7月15日から令和13年7月31日まで'],
    ]
    t = Table(biz_data, colWidths=[45*mm, 115*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 9),
        ('FONT', (0, 0), (0, -1), GOTHIC, 9),
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

    # Article 2
    story.append(Paragraph('第２条（譲渡の範囲）', styles['article_title']))
    story.append(Paragraph(
        '本契約に基づく事業譲渡の範囲は、以下の各号に掲げるものとする。',
        styles['body']))
    items = [
        '（１）本事業に係る営業権（のれん）',
        '（２）本事業に使用する什器、備品、厨房設備その他の動産一切（別紙「資産目録」記載のとおり）',
        '（３）本事業に係る営業許可その他の許認可（承継が法令上可能なものに限る）',
        '（４）本事業に係る仕入先、取引先との取引関係',
        '（５）本事業に関する顧客情報及びレシピ等の営業秘密',
        '（６）本事業に係る店舗の賃借権（賃貸人の同意を条件とする）',
    ]
    for item in items:
        story.append(Paragraph(item, styles['body_no_indent']))

    # Article 3
    story.append(Paragraph('第３条（譲渡対価）', styles['article_title']))
    story.append(Paragraph(
        '本事業の譲渡対価は、金1,850,000円（百八十五万円）（消費税別途）とする。',
        styles['body']))

    story.append(Paragraph('２　甲は、乙に対し、前項の譲渡対価を以下のとおり支払うものとする。', styles['body']))
    story.append(Paragraph('３　甲が残代金の支払いを遅延した場合、甲は乙に対し、年14.6％の割合による遅延損害金を支払うものとする。', styles['body']))

    pay_data = [
        ['支払区分', '支払日', '金額', '支払方法', '状態'],
        ['手付金', '令和8年3月18日', '¥100,000', 'Wise銀行振込', '支払済'],
        ['中間金①', '令和8年3月24日', '¥500,000', 'Wise銀行振込', '支払済'],
        ['中間金②', '令和8年4月1日', '¥500,000', '楽天銀行振込', '支払済'],
        ['残代金', '令和8年4月30日迄', '¥750,000', '銀行振込', '未払'],
    ]
    t = Table(pay_data, colWidths=[25*mm, 35*mm, 30*mm, 35*mm, 20*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 9),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 9),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('BACKGROUND', (0, 1), (-1, -1), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(Spacer(1, 2*mm))
    story.append(t)

    # Article 4
    story.append(Paragraph('第４条（譲渡日）', styles['article_title']))
    story.append(Paragraph(
        '本事業の譲渡日（以下「譲渡日」という。）は、令和8年5月1日とする。ただし、甲乙協議の上、これを変更することができる。',
        styles['body']))

    # Article 5
    story.append(Paragraph('第５条（従業員の取扱い）', styles['article_title']))
    story.append(Paragraph(
        '乙の従業員のうち、本事業に従事する者の雇用関係については、甲乙協議の上、甲が希望する者について甲が新たに雇用契約を締結するものとする。',
        styles['body']))

    # Article 6
    story.append(Paragraph('第６条（競業避止義務）', styles['article_title']))
    story.append(Paragraph(
        '乙は、譲渡日から2年間、東京都北区および隣接する区において、本事業と同種または類似の飲食事業を行ってはならないものとする。',
        styles['body']))

    # Article 7
    story.append(Paragraph('第７条（表明及び保証）', styles['article_title']))
    story.append(Paragraph(
        '乙は、甲に対し、本契約の締結日及び譲渡日において、以下の事項が真実かつ正確であることを表明し、保証する。',
        styles['body']))
    reps = [
        '（１）乙は、本事業に関し、法令に違反する行為を行っておらず、第三者との間で訴訟その他の紛争が生じていないこと',
        '（２）乙は、本事業の譲渡について必要な一切の社内手続を完了していること',
        '（３）譲渡対象資産について、担保権その他の第三者の権利が設定されていないこと',
        '（４）本事業に係る税金、社会保険料その他の公租公課について滞納がないこと',
        '（５）乙が甲に提供した本事業に関する情報は、重要な点において真実かつ正確であること',
    ]
    for r in reps:
        story.append(Paragraph(r, styles['body_no_indent']))

    # Article 8
    story.append(Paragraph('第８条（届出等の手続）', styles['article_title']))
    story.append(Paragraph(
        '乙は、譲渡日までに、本事業の譲渡に関し必要となる行政機関への届出その他の手続について、甲に協力するものとする。甲は、譲渡日以降速やかに、自己の名義による営業許可の取得その他の必要な手続を行うものとする。',
        styles['body']))

    # Article 9
    story.append(Paragraph('第９条（引渡し）', styles['article_title']))
    story.append(Paragraph(
        '乙は、譲渡日において、譲渡対象資産を現状有姿にて甲に引き渡すものとする。乙は、甲に対し、本事業の運営に必要な情報及び資料を引き渡し、合理的な範囲で業務の引継ぎに協力するものとする。',
        styles['body']))

    # Article 9-2
    story.append(Paragraph('２　乙は、譲渡日から14日間、甲からの求めに応じ、本事業の運営に関する助言及び引継ぎ支援を行うものとする。', styles['body']))

    # Article 10
    story.append(Paragraph('第１０条（秘密保持）', styles['article_title']))
    story.append(Paragraph(
        '甲及び乙は、本契約の内容及び本契約に関連して知り得た相手方の秘密情報を、事前の書面による承諾なく第三者に開示してはならない。ただし、法令又は裁判所の命令により開示が求められる場合はこの限りでない。',
        styles['body']))

    # Article 11
    story.append(Paragraph('第１１条（解除）', styles['article_title']))
    story.append(Paragraph(
        '甲又は乙は、相手方が本契約に定める義務に違反し、相当の期間を定めて催告したにもかかわらず当該違反が是正されない場合、本契約を解除することができる。',
        styles['body']))

    # Article 12
    story.append(Paragraph('第１２条（損害賠償）', styles['article_title']))
    story.append(Paragraph(
        '甲又は乙が本契約に定める義務に違反したことにより相手方に損害が生じた場合、当該違反した当事者は、相手方に対し、直接かつ通常の損害を賠償するものとする。',
        styles['body']))

    # Article 13
    story.append(Paragraph('第１３条（反社会的勢力の排除）', styles['article_title']))
    story.append(Paragraph(
        '甲及び乙は、自己又はその役員、従業員が、暴力団、暴力団員、暴力団関係企業その他の反社会的勢力に該当しないことを相互に表明し、保証する。',
        styles['body']))

    # Article 14
    story.append(Paragraph('第１４条（合意管轄）', styles['article_title']))
    story.append(Paragraph(
        '本契約に関する一切の紛争については、東京地方裁判所を第一審の専属的合意管轄裁判所とする。',
        styles['body']))

    # Article 15
    story.append(Paragraph('第１５条（協議事項）', styles['article_title']))
    story.append(Paragraph(
        '本契約に定めのない事項または本契約の解釈に疑義が生じた場合は、甲乙誠意をもって協議の上、解決するものとする。',
        styles['body']))

    # Signatures
    add_signature_block(story, styles)
    add_doc_footer(story, styles, '2026-001')

    doc.build(story)
    print(f"Generated: {filepath}")
    return filepath


# ============================================================
# DOCUMENT 2: 営業許可名義変更に関する合意書
# ============================================================
def generate_license_transfer():
    styles = get_styles()
    filepath = os.path.join(OUTPUT_DIR, '02_営業許可名義変更合意書.pdf')
    doc = SimpleDocTemplate(filepath, pagesize=A4,
        topMargin=25*mm, bottomMargin=25*mm,
        leftMargin=22*mm, rightMargin=22*mm)
    story = []

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('営業許可名義変更に関する合意書', styles['title']))
    story.append(Paragraph('Agreement on Transfer of Business License', styles['subtitle']))
    add_header_line(story)

    # Preamble
    story.append(Paragraph(
        'eMoment Japan合同会社（以下「甲」という。）とRIONA株式会社（以下「乙」という。）は、'
        '乙が保有する飲食店営業許可の名義変更に関し、以下のとおり合意する。',
        styles['body']))

    # Article 1
    story.append(Paragraph('第１条（目的）', styles['article_title']))
    story.append(Paragraph(
        '本合意書は、乙が保有する下記営業許可について、事業譲渡に伴い、甲が新たに営業許可を取得するために必要な手続に関し、甲乙間の権利義務関係を定めることを目的とする。',
        styles['body']))

    license_data = [
        ['許可の種類', '飲食店営業'],
        ['許可番号', '7北健生食き第168号'],
        ['許可名義人', '尾本 光洋（RIONA株式会社）'],
        ['営業所の名称', 'SUHANA Indian Nepal Restaurant'],
        ['営業所の所在地', '東京都北区上十条五丁目14番6号'],
        ['許可年月日', '令和7年（2025年）7月15日'],
        ['有効期限', '令和13年（2031年）7月31日'],
        ['発行機関', '東京都北区保健所長'],
    ]
    t = Table(license_data, colWidths=[40*mm, 120*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 9),
        ('FONT', (0, 0), (0, -1), GOTHIC, 9),
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(Spacer(1, 2*mm))
    story.append(t)

    # Article 2
    story.append(Paragraph('第２条（乙の義務）', styles['article_title']))
    story.append(Paragraph('乙は、甲による新たな営業許可の取得に関し、以下の義務を負うものとする。', styles['body']))
    items = [
        '（１）甲が営業許可の申請を行うために必要な一切の資料及び情報を速やかに提供すること',
        '（２）管轄保健所への届出及び手続に際し、甲に対し合理的な範囲で協力すること',
        '（３）甲が新たな営業許可を取得するまでの間、現行の営業許可を維持し、これを取り消されるような行為を行わないこと',
        '（４）廃業届の提出時期について、甲と事前に協議し、甲の新規許可取得に支障をきたさないよう配慮すること',
    ]
    for item in items:
        story.append(Paragraph(item, styles['body_no_indent']))

    # Article 3
    story.append(Paragraph('第３条（甲の義務）', styles['article_title']))
    story.append(Paragraph('甲は、以下の義務を負うものとする。', styles['body']))
    items = [
        '（１）速やかに食品衛生責任者の資格を取得または選任すること',
        '（２）管轄保健所（東京都北区保健所）に対し、新規の飲食店営業許可申請を行うこと',
        '（３）施設基準の適合に必要な改修がある場合は、自己の費用負担にて行うこと',
        '（４）新規許可取得に要する申請手数料その他の費用を負担すること',
    ]
    for item in items:
        story.append(Paragraph(item, styles['body_no_indent']))

    # Article 4
    story.append(Paragraph('第４条（手続の流れ）', styles['article_title']))
    story.append(Paragraph('甲乙は、営業許可の名義変更に関し、以下の手順に従い手続を進めるものとする。', styles['body']))

    proc_data = [
        ['順序', '手続内容', '目標時期', '担当'],
        ['①', '甲が北区保健所に事前相談を行い、必要書類を確認する', '契約締結後1週間以内', '甲'],
        ['②', '甲が食品衛生責任者を選任する', '契約締結後2週間以内', '甲'],
        ['③', '甲が新規の飲食店営業許可を申請する', '②完了後速やかに', '甲'],
        ['④', '保健所による施設検査の実施', '③から約2週間', '甲（乙協力）'],
        ['⑤', '甲に対する新規営業許可証の交付', '④完了後', '保健所'],
        ['⑥', '乙が現行営業許可に係る廃業届を提出する', '⑤確認後', '乙'],
    ]
    t = Table(proc_data, colWidths=[13*mm, 85*mm, 35*mm, 25*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 9),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 9),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(Spacer(1, 2*mm))
    story.append(t)

    # Article 5
    story.append(Paragraph('第５条（費用負担）', styles['article_title']))
    story.append(Paragraph(
        '営業許可の新規取得に要する費用（申請手数料、施設改修費用等）は、甲の負担とする。ただし、乙の責めに帰すべき事由により追加費用が発生した場合は、乙の負担とする。',
        styles['body']))

    # Article 6
    story.append(Paragraph('第６条（空白期間の取扱い）', styles['article_title']))
    story.append(Paragraph(
        '甲乙は、営業許可の空白期間（乙の廃業届提出から甲の新規許可取得まで）が生じないよう、最大限の努力を払うものとする。やむを得ず空白期間が生じる場合は、甲はその期間中の営業を行わないものとする。',
        styles['body']))

    # Article 7
    story.append(Paragraph('第７条（損害賠償）', styles['article_title']))
    story.append(Paragraph(
        '乙の責めに帰すべき事由により甲が営業許可を取得できない場合、または取得が著しく遅延した場合、乙は甲に対し、これにより甲が被った損害を賠償するものとする。',
        styles['body']))

    # Article 8
    story.append(Paragraph('第８条（有効期間）', styles['article_title']))
    story.append(Paragraph(
        '本合意書は、締結日から甲が新たな営業許可を取得し、かつ乙が廃業届を提出した日まで効力を有するものとする。',
        styles['body']))

    # Article 9
    story.append(Paragraph('第９条（準拠法及び管轄）', styles['article_title']))
    story.append(Paragraph(
        '本合意書は、日本法に準拠するものとし、本合意書に関する紛争については、東京地方裁判所を第一審の専属的合意管轄裁判所とする。',
        styles['body']))

    add_signature_block(story, styles)
    add_doc_footer(story, styles, '2026-002')

    doc.build(story)
    print(f"Generated: {filepath}")
    return filepath


# ============================================================
# DOCUMENT 3: 賃貸借権譲渡に関する合意書
# ============================================================
def generate_lease_transfer():
    styles = get_styles()
    filepath = os.path.join(OUTPUT_DIR, '03_賃貸借権譲渡合意書.pdf')
    doc = SimpleDocTemplate(filepath, pagesize=A4,
        topMargin=25*mm, bottomMargin=25*mm,
        leftMargin=22*mm, rightMargin=22*mm)
    story = []

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('賃貸借権譲渡に関する合意書', styles['title']))
    story.append(Paragraph('Agreement on Assignment of Lease Rights', styles['subtitle']))
    add_header_line(story)

    # Preamble
    story.append(Paragraph(
        'eMoment Japan合同会社（以下「甲」という。）とRIONA株式会社（以下「乙」という。）は、'
        '下記物件に係る賃貸借権の譲渡に関し、以下のとおり合意する。',
        styles['body']))

    # Article 1
    story.append(Paragraph('第１条（物件の表示）', styles['article_title']))
    story.append(Paragraph(
        '本合意書の対象となる物件（以下「本物件」という。）は、以下のとおりとする。',
        styles['body']))

    prop_data = [
        ['物件所在地', '東京都北区上十条五丁目14番6号'],
        ['用途', '飲食店（SUHANA Indian Nepal Restaurant）'],
        ['現賃借人', 'RIONA株式会社（代表：Lamichhane Dilli Raj）'],
        ['賃貸人（家主）', '（　　　　　　　　　　　　　　　）'],
        ['現行賃料', '月額　　　　　　　円（税込/税別）'],
        ['敷金/保証金', '金　　　　　　　円'],
        ['新規契約期間', '令和8年5月1日 ～ 令和11年4月30日（3年間）'],
    ]
    t = Table(prop_data, colWidths=[40*mm, 120*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 9),
        ('FONT', (0, 0), (0, -1), GOTHIC, 9),
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(Spacer(1, 2*mm))
    story.append(t)

    # Article 2
    story.append(Paragraph('第２条（賃貸借権の譲渡）', styles['article_title']))
    story.append(Paragraph(
        '乙は、本物件に係る賃貸借契約上の賃借人としての地位（以下「賃貸借権」という。）を甲に譲渡し、甲はこれを譲り受けるものとする。ただし、本条に基づく賃貸借権の譲渡は、賃貸人の書面による承諾を得ることを停止条件とする。',
        styles['body']))

    # Article 3
    story.append(Paragraph('第３条（賃貸人の承諾取得）', styles['article_title']))
    story.append(Paragraph(
        '乙は、本合意書締結後速やかに、賃貸人に対し、賃貸借権の譲渡について書面による承諾を求めるものとする。甲は、賃貸人が求める場合には、甲の信用情報その他の資料を提供し、承諾取得に協力するものとする。',
        styles['body']))
    story.append(Paragraph(
        '２　賃貸人の承諾が得られない場合、甲乙は協議の上、賃貸人との間で甲を賃借人とする新たな賃貸借契約の締結を試みるものとする。',
        styles['body']))

    # Article 4
    story.append(Paragraph('第４条（譲渡の条件）', styles['article_title']))
    story.append(Paragraph('賃貸借権の譲渡は、以下の条件を全て充足した時点で効力を生じるものとする。', styles['body']))
    items = [
        '（１）賃貸人の書面による承諾が得られること',
        '（２）事業譲渡契約書（文書番号：EMT-SUHANA-2026-001）に基づく事業譲渡の効力が生じること',
        '（３）甲が飲食店営業許可を取得すること、または取得の見込みが確実であること',
    ]
    for item in items:
        story.append(Paragraph(item, styles['body_no_indent']))

    # Article 5
    story.append(Paragraph('第５条（敷金・保証金の取扱い）', styles['article_title']))
    story.append(Paragraph(
        '本物件に係る敷金及び保証金の返還請求権は、賃貸借権の譲渡に伴い、乙から甲に移転するものとする。甲は、乙に対し、敷金及び保証金相当額を別途支払うものとし、その金額及び支払時期については甲乙協議の上決定する。',
        styles['body']))

    # Article 6
    story.append(Paragraph('第６条（賃貸借条件）', styles['article_title']))
    story.append(Paragraph(
        '甲は、原則として、現行の賃貸借契約と同一の条件にて賃貸借を継続するものとする。ただし、賃貸人との合意により条件が変更される場合はこの限りでない。',
        styles['body']))

    # Article 7
    story.append(Paragraph('第７条（原状回復義務）', styles['article_title']))
    story.append(Paragraph(
        '譲渡日以前に生じた本物件の原状回復義務は乙が負担し、譲渡日以降に生じた原状回復義務は甲が負担するものとする。',
        styles['body']))

    # Article 8
    story.append(Paragraph('第８条（物件の引渡し）', styles['article_title']))
    story.append(Paragraph(
        '乙は、譲渡日において、本物件を現状有姿にて甲に引き渡すものとする。乙は、引渡し時に本物件の鍵一切を甲に交付する。',
        styles['body']))

    # Article 9
    story.append(Paragraph('第９条（乙の表明保証）', styles['article_title']))
    story.append(Paragraph('乙は、甲に対し、以下の事項を表明し、保証する。', styles['body']))
    items = [
        '（１）乙は、本物件の賃貸借契約上の義務を履行しており、賃料の滞納その他の債務不履行がないこと',
        '（２）本物件について、第三者による転貸、占有その他の権利の設定がないこと',
        '（３）本物件について、建物の構造・設備に関し、乙が知り得る重大な瑕疵がないこと',
        '（４）賃貸人との間で、未解決の紛争または係争がないこと',
    ]
    for item in items:
        story.append(Paragraph(item, styles['body_no_indent']))

    # Article 10
    story.append(Paragraph('第１０条（費用負担）', styles['article_title']))
    story.append(Paragraph(
        '賃貸借権の譲渡に関して賃貸人に支払う承諾料その他の費用が発生する場合は、甲乙折半にて負担するものとする。ただし、甲乙協議の上、別段の定めをすることができる。',
        styles['body']))

    # Article 11
    story.append(Paragraph('第１１条（契約不成立の場合）', styles['article_title']))
    story.append(Paragraph(
        '賃貸人の承諾が得られず、かつ新たな賃貸借契約の締結もできない場合は、本合意書は効力を失うものとする。この場合、甲乙はそれぞれ相手方に対し、損害賠償その他の請求を行わないものとする。',
        styles['body']))

    # Article 12
    story.append(Paragraph('第１２条（準拠法及び管轄）', styles['article_title']))
    story.append(Paragraph(
        '本合意書は、日本法に準拠するものとし、本合意書に関する紛争については、東京地方裁判所を第一審の専属的合意管轄裁判所とする。',
        styles['body']))

    add_signature_block(story, styles)
    add_doc_footer(story, styles, '2026-003')

    doc.build(story)
    print(f"Generated: {filepath}")
    return filepath


# ============================================================
# Main
# ============================================================
if __name__ == '__main__':
    print("=== Generating Suhana Legal Documents ===\n")
    f1 = generate_business_transfer()
    f2 = generate_license_transfer()
    f3 = generate_lease_transfer()
    print(f"\n=== All documents generated in {OUTPUT_DIR} ===")
    print(f"1. {f1}")
    print(f"2. {f2}")
    print(f"3. {f3}")
