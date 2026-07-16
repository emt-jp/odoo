#!/usr/bin/env python3
"""
Generate professional Japanese legal documents for Suhana Restaurant acquisition.

Eight documents:
  1. 事業譲渡契約書 (Business Transfer Agreement)
  2. 営業承継及び新規許可申請に関する合意書 (Business License Succession Agreement)
     [Renamed from 名義変更 because 飲食店営業許可 is non-transferable under 食品衛生法]
  3. 賃貸借権譲渡に関する合意書 (Lease Assignment Agreement)
  4. 賃貸人承諾書（雛形） (Landlord Consent Letter — template)
  5. 別紙１_資産目録 (Asset Inventory, attached to Doc 1)
  6. 賃借権譲渡承諾願書 (Request for Landlord Consent to Lease Assignment —
     formal written request from RIONA to landlord, triggers 民法612条 procedure)
  7. 別紙２_在庫品目録 (Stock Inventory, attached to Doc 1)
  8. 別紙３_既払金振込明細書 (Payment Receipts Schedule, attached to Doc 1 —
     lists all transfers made so far with references to Wise/Rakuten証憑)

ITEMS REQUIRING USER VERIFICATION BEFORE SIGNING:
  - Entity form of buyer: script uses "合同会社" (LLC, 代表社員). CLAUDE.md says "KK"
    (株式会社). Confirm against 登記簿謄本.
  - RIONA株式会社 registered address (currently blank)
  - Landlord identity, current rent, deposit (Doc 3 — currently blank)
  - License holder identity: is 営業許可 in RIONA KK's name with 尾本 as 食品衛生
    責任者, or is 尾本 the personal license holder? Confirm against 営業許可書.
  - Payment ledger reconciliation: contract claims ¥1,100,000 already paid across
    3 transfers. tasks/odoo/suhana-acquisition.md only records ¥600,000 paid via
    Wise. Confirm Apr 1 ¥500,000 Rakuten transfer actually occurred before signing.
  - 印紙税 (revenue stamp): Doc 1 is 第7号文書 — affix ¥4,000 印紙 on each original.
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.colors import black, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

OUTPUT_DIR = '/Users/pk/Downloads/suhana/contracts'
os.makedirs(OUTPUT_DIR, exist_ok=True)

pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))

MINCHO = 'HeiseiMin-W3'
GOTHIC = 'HeiseiKakuGo-W5'
GOTHIC_BOLD = 'HeiseiKakuGo-W5'

DARK = HexColor('#1a1a1a')
ACCENT = HexColor('#2c3e50')
LINE_COLOR = HexColor('#333333')
LIGHT_GRAY = HexColor('#f5f5f5')
WARN_BG = HexColor('#fff8e1')
WARN_BORDER = HexColor('#f0c040')

CONTRACT_DATE_JP = '令和8年4月15日'
CONTRACT_DATE_WESTERN = '2026年4月15日'

BUYER_NAME = '株式会社eMoment Japan'
BUYER_ADDR = '東京都江戸川区南葛西2-6-16'
BUYER_REP_TITLE = '代表取締役'
BUYER_REP_NAME = 'Dipikaranimishra Sahoo'

SELLER_NAME = 'RIONA株式会社'
# Verified via National Tax Agency 法人番号公表サイト (gBizINFO) 2026-04-23
# 法人番号 5010601061492
SELLER_ADDR = '東京都墨田区石原１丁目７番１４号　稲垣マンション５０２号室'
SELLER_CORP_NO = '5010601061492'
SELLER_REP_NAME = 'Lamichhane Dilli Raj'


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
        'warn': ParagraphStyle(
            'Warn', fontName=GOTHIC, fontSize=9, leading=14,
            alignment=TA_LEFT, textColor=HexColor('#8a6d00'),
            backColor=WARN_BG, borderColor=WARN_BORDER, borderWidth=0.5,
            borderPadding=4, spaceAfter=3*mm, spaceBefore=2*mm,
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


def add_signature_block(story, styles, with_personal_guarantor=False):
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(
        '以上、本契約の成立を証するため、本書2通を作成し、甲乙各1通を保有する。',
        styles['body']))
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(
        f'契約締結日：　{CONTRACT_DATE_JP}（{CONTRACT_DATE_WESTERN}）',
        styles['body_no_indent']))
    story.append(Spacer(1, 10*mm))

    sig_data_a = [
        [Paragraph('<b>【甲】　譲受人</b>', styles['signature_label']), ''],
        [Paragraph('商号：', styles['signature_line']),
         Paragraph(BUYER_NAME, styles['signature_line'])],
        [Paragraph('所在地：', styles['signature_line']),
         Paragraph(BUYER_ADDR, styles['signature_line'])],
        [Paragraph(f'{BUYER_REP_TITLE}：', styles['signature_line']),
         Paragraph(f'{BUYER_REP_NAME}　　　　　　印', styles['signature_line'])],
    ]
    t = Table(sig_data_a, colWidths=[30*mm, 120*mm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LINEBELOW', (1, 3), (1, 3), 0.5, LINE_COLOR),
    ]))
    story.append(t)
    story.append(Spacer(1, 8*mm))

    sig_data_b = [
        [Paragraph('<b>【乙】　譲渡人</b>', styles['signature_label']), ''],
        [Paragraph('商号：', styles['signature_line']),
         Paragraph(SELLER_NAME, styles['signature_line'])],
        [Paragraph('所在地：', styles['signature_line']),
         Paragraph(SELLER_ADDR, styles['signature_line'])],
        [Paragraph('代表者：', styles['signature_line']),
         Paragraph(f'{SELLER_REP_NAME}　　　　　　　　印（実印）',
                   styles['signature_line'])],
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

    if with_personal_guarantor:
        story.append(Spacer(1, 8*mm))
        sig_data_c = [
            [Paragraph(
                '<b>【丙】　乙代表者個人（競業避止義務及び表明保証の連帯保証人）</b>',
                styles['signature_label']), ''],
            [Paragraph('氏名：', styles['signature_line']),
             Paragraph(f'{SELLER_REP_NAME}　　　　　　　　印（実印）',
                       styles['signature_line'])],
            [Paragraph('生年月日：', styles['signature_line']),
             Paragraph('1985年7月20日', styles['signature_line'])],
            [Paragraph('住所：', styles['signature_line']),
             Paragraph('東京都文京区大塚3丁目11番7-502号',
                       styles['signature_line'])],
        ]
        t = Table(sig_data_c, colWidths=[30*mm, 120*mm])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LINEBELOW', (1, 1), (1, 1), 0.5, LINE_COLOR),
        ]))
        story.append(t)


def add_doc_footer(story, styles, doc_number, stamp_note=None):
    story.append(Spacer(1, 6*mm))
    add_thin_line(story)
    if stamp_note:
        story.append(Paragraph(stamp_note, styles['small']))
    story.append(Paragraph(
        f'文書番号：EMT-SUHANA-{doc_number}　｜　'
        f'本契約書は2通作成し、甲乙各1通を保有するものとする。',
        styles['footer']))


def info_table(data, key_width=45, val_width=115):
    t = Table(data, colWidths=[key_width*mm, val_width*mm])
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
    return t


# ============================================================
# DOCUMENT 1: 事業譲渡契約書
# ============================================================
def generate_business_transfer():
    styles = get_styles()
    filepath = os.path.join(OUTPUT_DIR, '01_事業譲渡契約書.pdf')
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            topMargin=25*mm, bottomMargin=25*mm,
                            leftMargin=22*mm, rightMargin=22*mm)
    story = []

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('事　業　譲　渡　契　約　書', styles['title']))
    story.append(Paragraph('Business Transfer Agreement', styles['subtitle']))
    add_header_line(story)

    # Parties
    story.append(Paragraph(
        f'{BUYER_NAME}（以下「甲」という。）と{SELLER_NAME}（以下「乙」という。）'
        f'並びに乙の代表者である{SELLER_REP_NAME}（以下「丙」という。）は、'
        '乙が営む飲食事業の譲渡に関し、以下のとおり契約（以下「本契約」という。）'
        'を締結する。', styles['body']))

    # Recital (前文) — explains payments preceding execution
    story.append(Paragraph('前　文', styles['article_title']))
    story.append(Paragraph(
        '甲乙は、令和8年3月中旬以降、乙が経営する下記飲食事業の甲への譲渡に関し'
        '誠実に協議を行い、その協議の過程において、譲渡対価の一部に充当することを'
        '前提として甲から乙に対し金銭の授受が行われた。本契約は、当該口頭による'
        '基本合意の内容を書面化し、当事者間の権利義務関係を明確化することを'
        '目的とする。', styles['body']))

    # Article 1
    story.append(Paragraph('第１条（事業譲渡）', styles['article_title']))
    story.append(Paragraph(
        '乙は、乙が営む下記飲食事業（以下「本事業」という。）を、本契約に定める'
        '条件に従い、甲に譲渡し、甲はこれを譲り受けるものとする。', styles['body']))
    story.append(Spacer(1, 2*mm))
    biz_data = [
        ['事業の名称', 'SUHANA Indian Nepal Restaurant'],
        ['事業の所在地', '東京都北区上十条五丁目14番6号'],
        ['事業の種類', '飲食店営業'],
        ['営業許可番号', '7北健生食き第168号'],
        ['営業許可有効期限', '令和7年（2025年）7月15日 ～ 令和13年（2031年）7月31日'],
        ['発行機関', '東京都北区保健所長'],
    ]
    story.append(info_table(biz_data))

    # Article 2
    story.append(Paragraph('第２条（譲渡の範囲）', styles['article_title']))
    story.append(Paragraph(
        '本契約に基づく事業譲渡の範囲は、以下の各号に掲げるものとし、その詳細は'
        '本契約に添付する別紙１「資産目録」のとおりとする。', styles['body']))
    items = [
        '（１）本事業に係る営業権（のれん）',
        '（２）本事業に使用する什器、備品、厨房設備、食器その他の動産一切'
        '（別紙１「資産目録」記載のとおり）',
        '（３）譲渡日時点における本事業の在庫品（食材、飲料、消耗品等）一切'
        '（別紙２「在庫品目録」記載のとおり）',
        '（４）本事業に関する顧客情報、レシピ、メニュー、ブランド使用権及び'
        '営業秘密',
        '（５）本事業に係る店舗の賃借権（賃貸人の書面による承諾を停止条件とする。'
        '詳細は文書番号EMT-SUHANA-2026-003「賃貸借権譲渡に関する合意書」による）',
        '（６）譲渡日時点で稼働中の電話番号、ウェブサイト、SNSアカウント及び'
        '各種オンライン予約・出前サービスに係るアカウント（ログイン情報は譲渡日'
        'に甲乙立会いの上で引渡）',
    ]
    for item in items:
        story.append(Paragraph(item, styles['body_no_indent']))
    story.append(Paragraph(
        '２　飲食店営業許可その他の許認可については、食品衛生法その他関係法令の'
        '定めにより承継できないため、文書番号EMT-SUHANA-2026-002「営業承継及び'
        '新規許可申請に関する合意書」に基づき、甲が新規に取得するものとする。',
        styles['body']))
    story.append(Paragraph(
        '３　本事業に係る売掛金、買掛金、未払債務、従業員に対する未払賃金、'
        '退職金引当金及び公租公課については譲渡の対象に含まれず、譲渡日の前日'
        'までに発生したものは乙の負担及び帰属、譲渡日以後に発生するものは甲の'
        '負担及び帰属とする。', styles['body']))

    # Article 3
    story.append(Paragraph('第３条（譲渡対価）', styles['article_title']))
    story.append(Paragraph(
        '本事業の譲渡対価は、金1,850,000円（百八十五万円）（消費税別途）とする。'
        '消費税相当額（10％、金185,000円）は、残代金の支払時に甲から乙に対し'
        '別途支払うものとする。', styles['body']))
    story.append(Paragraph(
        '２　甲は、乙に対し、前項の譲渡対価を以下のとおり支払うものとし、'
        '既払分については本契約締結をもって譲渡対価の一部に充当することを'
        '甲乙確認する。', styles['body']))
    story.append(Spacer(1, 2*mm))

    pay_data = [
        ['支払区分', '支払期日', '金額（税抜）', '支払方法', '状態'],
        ['手付金', '令和8年3月18日', '¥100,000', 'Wise銀行振込', '支払済'],
        ['中間金①', '令和8年3月24日', '¥500,000', 'Wise銀行振込', '支払済'],
        ['中間金②', '令和8年4月1日', '¥500,000', '楽天銀行振込', '支払済'],
        ['残代金', '令和8年4月30日まで', '¥750,000', '銀行振込', '未払'],
        ['消費税', '残代金支払時', '¥185,000', '銀行振込', '未払'],
        ['合計', '', '¥2,035,000', '', ''],
    ]
    t = Table(pay_data, colWidths=[22*mm, 32*mm, 28*mm, 32*mm, 18*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 9),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 9),
        ('FONT', (0, -1), (-1, -1), GOTHIC, 9),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('ALIGN', (4, 0), (4, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Paragraph(
        '３　甲が残代金の支払いを遅延した場合、甲は乙に対し、支払期日の翌日'
        'から完済日まで、年14.6％の割合による遅延損害金を支払うものとする。',
        styles['body']))
    story.append(Paragraph(
        '４　既払分の振込明細書、Wise取引番号その他の支払証憑は本契約に'
        '別紙３として添付し、甲乙双方が原本を保有するものとする。', styles['body']))

    # Article 4
    story.append(Paragraph('第４条（譲渡日）', styles['article_title']))
    story.append(Paragraph(
        '本事業の譲渡日（以下「譲渡日」という。）は、令和8年（2026年）5月1日と'
        'する。ただし、第１６条に定める前提条件が当該日までに充足されない場合、'
        '甲乙協議の上、譲渡日を変更することができる。', styles['body']))

    # Article 5
    story.append(Paragraph('第５条（従業員の取扱い）', styles['article_title']))
    story.append(Paragraph(
        '乙の従業員のうち、本事業に従事する者の雇用関係は、譲渡日をもって乙との'
        '間で終了するものとし、甲が継続雇用を希望する者については、甲乙及び'
        '当該従業員の三者協議の上、甲が新たに雇用契約を締結するものとする。',
        styles['body']))
    story.append(Paragraph(
        '２　譲渡日前日までの未払賃金、社会保険料、源泉徴収所得税、住民税及び'
        '退職金等の労務関連債務はすべて乙の負担とし、乙はこれらを譲渡日までに'
        '完済するものとする。', styles['body']))

    # Article 6
    story.append(Paragraph('第６条（競業避止義務）', styles['article_title']))
    story.append(Paragraph(
        '乙及び丙は、譲渡日から3年間、東京都北区及びこれに隣接する区'
        '（板橋区、豊島区、足立区、荒川区、文京区）において、本事業と同種'
        'または類似の飲食事業（インド料理、ネパール料理、南アジア系料理を'
        '提供する飲食店をいう。）を、自ら営み、または第三者をして営ませて'
        'はならないものとする。', styles['body']))
    story.append(Paragraph(
        '２　前項の義務に違反した場合、乙及び丙は連帯して、甲に対し違約金として'
        '譲渡対価相当額（金1,850,000円）を支払うほか、甲が被った損害を賠償する'
        'ものとする。', styles['body']))

    # Article 7
    story.append(Paragraph('第７条（表明及び保証）', styles['article_title']))
    story.append(Paragraph(
        '乙及び丙は、甲に対し、本契約の締結日及び譲渡日において、以下の事項が'
        '真実かつ正確であることを表明し、保証する。', styles['body']))
    reps = [
        '（１）乙は、本事業に関し、法令（食品衛生法、消防法、建築基準法、'
        '労働基準法、税法その他関係法令を含む。）に違反する行為を行っておらず、'
        '行政機関から行政処分、是正勧告または指導を受けていないこと',
        '（２）乙は、本事業の譲渡について、会社法その他関係法令上必要な'
        '社内手続（株主総会の決議を含む。）を完了し、または本契約締結後'
        '速やかに完了する見込みであること',
        '（３）譲渡対象資産について、担保権、所有権留保、リース、その他第三者の'
        '権利が設定されておらず、第三者から譲渡禁止または譲渡制限を主張されて'
        'いないこと',
        '（４）本事業に係る税金（法人税、消費税、源泉徴収所得税、住民税、'
        '事業税、固定資産税等）、社会保険料、労働保険料その他の公租公課に'
        'ついて滞納がないこと',
        '（５）本事業に関し、第三者との間で訴訟、仲裁、調停、行政処分その他の'
        '紛争（いずれも開始の蓋然性が高いものを含む。）が生じていないこと',
        '（６）本事業に係るレシピ、ブランド名「SUHANA」その他の知的財産権に'
        'ついて第三者の権利を侵害していないこと',
        '（７）乙が甲に提供した本事業に関する情報（売上、顧客数、原価、人件費、'
        '光熱費、賃料その他財務情報を含む。）は、重要な点において真実かつ正確'
        'であり、誤解を生じさせる記載または重大な事実の遺漏がないこと',
    ]
    for r in reps:
        story.append(Paragraph(r, styles['body_no_indent']))
    story.append(Paragraph(
        '２　甲は、乙に対し、本契約締結に必要な権限を有していること及び本契約の'
        '履行が他の契約に違反しないことを表明し、保証する。', styles['body']))
    story.append(Paragraph(
        '３　前各項の表明保証に違反したことが判明した場合、違反した当事者は、'
        '相手方が被った損害（弁護士費用を含む。）を賠償するものとする。',
        styles['body']))

    # Article 8
    story.append(Paragraph('第８条（届出等の手続）', styles['article_title']))
    story.append(Paragraph(
        '乙は、譲渡日までに、本事業の譲渡に関し必要となる行政機関'
        '（北区保健所、税務署、社会保険事務所、労働基準監督署等）への'
        '届出その他の手続について、甲に対し合理的な範囲で協力するものとする。'
        '甲は、譲渡日以降速やかに、自己の名義による飲食店営業許可の取得'
        'その他の必要な手続を行うものとする。', styles['body']))

    # Article 9
    story.append(Paragraph('第９条（引渡し）', styles['article_title']))
    story.append(Paragraph(
        '乙は、譲渡日において、譲渡対象資産を現状有姿にて甲に引き渡し、'
        '別紙１「資産目録」及び別紙２「在庫品目録」に基づく引渡確認書'
        'に甲乙双方が記名押印するものとする。', styles['body']))
    story.append(Paragraph(
        '２　乙は、譲渡日において、本事業の運営に必要な情報、資料、'
        'レシピ、仕入先連絡先、顧客リスト、各種パスワード及び店舗の'
        '鍵一切を甲に引き渡すものとする。', styles['body']))
    story.append(Paragraph(
        '３　乙は、譲渡日から30日間、甲からの求めに応じ、本事業の運営に'
        '関する助言、調理技術の伝授、仕入先の紹介及び業務引継ぎ支援を'
        '無償で行うものとする。', styles['body']))

    # Article 10 - Utilities
    story.append(Paragraph('第１０条（公共料金等の取扱い）',
                           styles['article_title']))
    story.append(Paragraph(
        '電気、ガス、水道、電話、インターネットその他の公共料金及び役務料金'
        'については、譲渡日の前日までの使用分を乙が、譲渡日以降の使用分を甲が'
        'それぞれ負担するものとし、譲渡日において当該各事業者に対する契約者'
        '名義の変更手続を行うものとする。', styles['body']))
    story.append(Paragraph(
        '２　各公共料金の保証金（電気、ガス、水道等）が乙より各事業者に'
        '差し入れられている場合、当該保証金返還請求権は乙に帰属し、'
        '甲は譲渡日以降、必要に応じ自己名義で新たに保証金を差し入れる'
        'ものとする。', styles['body']))

    # Article 11
    story.append(Paragraph('第１１条（秘密保持）', styles['article_title']))
    story.append(Paragraph(
        '甲、乙及び丙は、本契約の内容及び本契約に関連して知り得た相手方の'
        '秘密情報（本事業のレシピ、顧客情報、財務情報を含むが、これに'
        '限らない。）を、事前の書面による承諾なく第三者に開示してはならない。'
        'ただし、法令、裁判所、税務当局その他の行政機関の命令により開示が'
        '求められる場合はこの限りでない。', styles['body']))
    story.append(Paragraph(
        '２　本条の義務は、本契約の終了後も5年間継続するものとする。',
        styles['body']))

    # Article 12
    story.append(Paragraph('第１２条（解除）', styles['article_title']))
    story.append(Paragraph(
        '甲又は乙は、相手方が本契約に定める義務に違反し、相当の期間'
        '（少なくとも14日間）を定めて書面により催告したにもかかわらず'
        '当該違反が是正されない場合、本契約を解除することができる。',
        styles['body']))
    story.append(Paragraph(
        '２　甲又は乙について、支払停止、破産手続開始、民事再生手続開始、'
        '会社更生手続開始その他類似の手続の申立てがあった場合、相手方は'
        '何らの催告を要せず本契約を解除することができる。', styles['body']))

    # Article 13
    story.append(Paragraph('第１３条（損害賠償）', styles['article_title']))
    story.append(Paragraph(
        '甲、乙又は丙が本契約に定める義務に違反したことにより相手方に'
        '損害が生じた場合、当該違反した当事者は、相手方に対し、直接かつ'
        '通常の損害（弁護士費用を含む。）を賠償するものとする。',
        styles['body']))

    # Article 14 - Anti-social
    story.append(Paragraph('第１４条（反社会的勢力の排除）',
                           styles['article_title']))
    story.append(Paragraph(
        '甲、乙及び丙は、自己又はその役員、従業員、株主、社員その他の'
        '関係者が、暴力団、暴力団員、暴力団準構成員、暴力団関係企業、'
        '総会屋、社会運動等標榜ゴロ、特殊知能暴力集団その他これらに'
        '準ずる者（以下「反社会的勢力」という。）に該当しないこと、'
        'かつ将来にわたり該当しないことを表明し、保証する。',
        styles['body']))
    story.append(Paragraph(
        '２　甲、乙又は丙が前項に違反した場合、相手方は何らの催告を要せず'
        '本契約を直ちに解除することができ、これにより相手方に生じた損害を'
        '違反した当事者が賠償するものとする。', styles['body']))

    # Article 15 - Force majeure
    story.append(Paragraph('第１５条（不可抗力）', styles['article_title']))
    story.append(Paragraph(
        '天災地変、戦争、内乱、テロ、感染症の蔓延、法令の制定改廃、'
        '行政機関の命令その他甲乙の責めに帰すべからざる事由により本契約の'
        '履行が遅滞または不能となった場合、当該当事者は責任を負わないもの'
        'とする。ただし、当該事由が60日を超えて継続する場合、いずれの'
        '当事者も書面による通知により本契約を解除することができる。',
        styles['body']))

    # Article 16 - Conditions precedent
    story.append(Paragraph('第１６条（譲渡の前提条件）', styles['article_title']))
    story.append(Paragraph(
        '本契約に基づく事業譲渡は、譲渡日において以下の各号に掲げる前提条件が'
        '全て充足されていることを条件とする。', styles['body']))
    cps = [
        '（１）甲が新規の飲食店営業許可を取得していること、または保健所'
        'による施設検査を完了し許可取得が確実であること',
        '（２）賃貸人より本物件の賃貸借権譲渡について書面による承諾が'
        '得られていること、または甲を賃借人とする新規賃貸借契約が締結されて'
        'いること',
        '（３）乙が本契約第７条に定める表明保証に重大な違反がないこと',
        '（４）甲が残代金の支払を完了していること',
    ]
    for c in cps:
        story.append(Paragraph(c, styles['body_no_indent']))
    story.append(Paragraph(
        '２　前項の前提条件のいずれかが譲渡日までに充足されない場合、甲乙協議の上、'
        '譲渡日の延期、条件の放棄または本契約の解除を決定するものとする。',
        styles['body']))

    # Article 17
    story.append(Paragraph('第１７条（通知）', styles['article_title']))
    story.append(Paragraph(
        '本契約に関する通知、請求その他の意思表示は、書面（電子メールを含む。）'
        'により、相手方の住所、本店所在地、電子メールアドレス宛に行うものと'
        'する。当事者は、連絡先を変更した場合、速やかに相手方に通知する'
        'ものとする。', styles['body']))

    # Article 18
    story.append(Paragraph('第１８条（契約の譲渡禁止）', styles['article_title']))
    story.append(Paragraph(
        '甲、乙及び丙は、相手方の事前の書面による承諾なく、本契約上の地位'
        'または本契約に基づく権利義務の全部または一部を第三者に譲渡し、または'
        '担保に供してはならない。', styles['body']))

    # Article 19
    story.append(Paragraph('第１９条（分離可能性）', styles['article_title']))
    story.append(Paragraph(
        '本契約のいずれかの条項が法令により無効または執行不能と判断された'
        '場合であっても、その他の条項の効力には影響を及ぼさない。当事者は、'
        '当該無効または執行不能となった条項に最も近い経済的効果を有する'
        '有効な条項に置き換えるよう誠実に協議するものとする。',
        styles['body']))

    # Article 20
    story.append(Paragraph('第２０条（完全合意）', styles['article_title']))
    story.append(Paragraph(
        '本契約は、本契約の主題に関する甲乙丙間の完全な合意を構成し、本契約'
        '締結前における甲乙丙間の口頭または書面による一切の合意、了解、表明'
        'に優先する。', styles['body']))

    # Article 21
    story.append(Paragraph('第２１条（合意管轄）', styles['article_title']))
    story.append(Paragraph(
        '本契約に関する一切の紛争については、東京地方裁判所を第一審の'
        '専属的合意管轄裁判所とする。', styles['body']))

    # Article 22
    story.append(Paragraph('第２２条（協議事項）', styles['article_title']))
    story.append(Paragraph(
        '本契約に定めのない事項または本契約の解釈に疑義が生じた場合は、'
        '甲乙丙誠意をもって協議の上、解決するものとする。', styles['body']))

    # Attachments list
    story.append(Paragraph('別紙一覧', styles['article_title']))
    attach_data = [
        ['別紙１', '資産目録（什器・備品・厨房設備・食器等）'],
        ['別紙２', '在庫品目録（譲渡日時点）'],
        ['別紙３', '既払金の振込明細書（写し）'],
    ]
    t = Table(attach_data, colWidths=[25*mm, 135*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 9),
        ('FONT', (0, 0), (0, -1), GOTHIC, 9),
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

    add_signature_block(story, styles, with_personal_guarantor=True)
    add_doc_footer(story, styles, '2026-001',
                   stamp_note='【印紙】本契約書は印紙税法上の第7号文書（継続的取引の'
                              '基本となる契約書）に該当し、各原本に¥4,000の収入印紙を'
                              '貼付する必要がある。')

    doc.build(story)
    print(f"Generated: {filepath}")
    return filepath


# ============================================================
# DOCUMENT 2: 営業承継及び新規許可申請に関する合意書
# ============================================================
def generate_license_transfer():
    styles = get_styles()
    filepath = os.path.join(
        OUTPUT_DIR, '02_営業承継及び新規許可申請合意書.pdf')
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            topMargin=25*mm, bottomMargin=25*mm,
                            leftMargin=22*mm, rightMargin=22*mm)
    story = []

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(
        '営業承継及び新規許可申請に関する合意書', styles['title']))
    story.append(Paragraph(
        'Agreement on Business Succession and New License Application',
        styles['subtitle']))
    add_header_line(story)

    story.append(Paragraph(
        f'{BUYER_NAME}（以下「甲」という。）と{SELLER_NAME}'
        '（以下「乙」という。）は、乙が現に営む飲食店営業の甲への承継に関し、'
        '飲食店営業許可は食品衛生法第55条の定めにより譲渡できないことから、'
        '乙の廃業届の提出と甲の新規営業許可申請を円滑に行うため、以下のとおり'
        '合意する。', styles['body']))

    # Article 1
    story.append(Paragraph('第１条（目的）', styles['article_title']))
    story.append(Paragraph(
        '本合意書は、乙が保有する下記飲食店営業許可について、文書番号'
        'EMT-SUHANA-2026-001「事業譲渡契約書」に基づく事業譲渡に伴い、甲が'
        '同一店舗において新たに飲食店営業許可を取得し、乙が現許可に係る'
        '廃業届を提出するために必要な手続並びに甲乙間の権利義務関係を定める'
        'ことを目的とする。', styles['body']))
    story.append(Spacer(1, 2*mm))

    license_data = [
        ['許可の種類', '飲食店営業'],
        ['許可番号', '7北健生食き第168号'],
        ['許可名義（被許可者）', f'{SELLER_NAME}（食品衛生責任者：尾本 光洋）'],
        ['営業所の名称', 'SUHANA Indian Nepal Restaurant'],
        ['営業所の所在地', '東京都北区上十条五丁目14番6号'],
        ['許可年月日', '令和7年（2025年）7月15日'],
        ['有効期限', '令和13年（2031年）7月31日'],
        ['発行機関', '東京都北区保健所長'],
    ]
    story.append(info_table(license_data, key_width=42, val_width=118))

    story.append(Paragraph(
        '※ 上記「許可名義」については、現許可証原本に基づき記載するものとし、'
        '記載内容に齟齬がある場合、許可証原本の記載を優先する。', styles['small']))

    # Article 2
    story.append(Paragraph(
        '第２条（飲食店営業許可の非承継性の確認）', styles['article_title']))
    story.append(Paragraph(
        '甲乙は、飲食店営業許可は食品衛生法その他の関係法令上、第三者に対し'
        '譲渡することができず、営業の主体に変更が生じる場合は、現許可者による'
        '廃業届の提出と新営業者による新規許可申請が必要となることを確認する。',
        styles['body']))

    # Article 3
    story.append(Paragraph('第３条（乙の義務）', styles['article_title']))
    story.append(Paragraph(
        '乙は、甲による新たな飲食店営業許可の取得に関し、以下の義務を負う'
        'ものとする。', styles['body']))
    items = [
        '（１）甲が営業許可申請を行うために必要な現営業許可証の写し、施設の'
        '構造設備に関する図面、給排水設備関連書類その他一切の資料及び情報を'
        '速やかに提供すること',
        '（２）東京都北区保健所への届出及び立入検査に際し、甲及び保健所職員に'
        '対し合理的な範囲で協力すること',
        '（３）甲が新たな営業許可を取得するまでの間、現行の営業許可を維持し、'
        '食品衛生法令の遵守に努め、当該許可を取り消されまたは停止されるような'
        '行為を行わないこと',
        '（４）廃業届の提出時期について、甲と事前に書面により協議し、甲の'
        '新規許可取得に支障をきたさないよう配慮すること',
        '（５）保健所による施設の現地確認に立ち会うこと（甲が要請した場合）',
    ]
    for item in items:
        story.append(Paragraph(item, styles['body_no_indent']))

    # Article 4
    story.append(Paragraph('第４条（甲の義務）', styles['article_title']))
    story.append(Paragraph('甲は、以下の義務を負うものとする。', styles['body']))
    items = [
        '（１）契約締結後速やかに、食品衛生責任者の資格を有する者を選任し、'
        'または甲の役員もしくは従業員に食品衛生責任者養成講習会を受講させる'
        'こと',
        '（２）東京都北区保健所に対し、新規の飲食店営業許可申請（食品衛生法'
        '第55条に基づく営業許可申請）を行うこと',
        '（３）施設基準（食品衛生法施行規則別表第19）の適合に必要な改修が'
        'ある場合は、自己の費用負担にて行うこと',
        '（４）新規許可取得に要する申請手数料、施設改修費用、食品衛生責任者'
        '養成講習会受講料その他一切の費用を負担すること',
        '（５）営業許可取得前は、許可なく本店舗において飲食店営業を行わない'
        'こと',
    ]
    for item in items:
        story.append(Paragraph(item, styles['body_no_indent']))

    # Article 5 - Procedure
    story.append(Paragraph('第５条（手続の流れ）', styles['article_title']))
    story.append(Paragraph(
        '甲乙は、営業の承継に関し、以下の手順に従い手続を進めるものとする。',
        styles['body']))

    proc_data = [
        ['順序', '手続内容', '目標時期', '担当'],
        ['①', '甲が東京都北区保健所に事前相談を行い、必要書類を確認する',
         '契約締結後1週間以内', '甲'],
        ['②', '甲が食品衛生責任者を選任（または養成講習を受講）する',
         '契約締結後3週間以内', '甲'],
        ['③', '乙が施設の構造設備図面等の必要資料を甲に提供する',
         '契約締結後1週間以内', '乙'],
        ['④', '甲が新規飲食店営業許可申請を提出する',
         '②③完了後速やかに', '甲'],
        ['⑤', '保健所による施設検査の実施',
         '④から約2週間以内', '甲（乙協力）'],
        ['⑥', '甲に対する新規営業許可証の交付',
         '⑤完了後概ね1週間', '保健所'],
        ['⑦', '乙が現行営業許可に係る廃業届を提出する',
         '⑥確認後3日以内', '乙'],
    ]
    t = Table(proc_data, colWidths=[12*mm, 88*mm, 32*mm, 28*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 9),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 9),
        ('FONT', (0, 1), (0, -1), GOTHIC, 10),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(Spacer(1, 2*mm))
    story.append(t)

    # Article 6
    story.append(Paragraph('第６条（費用負担）', styles['article_title']))
    story.append(Paragraph(
        '営業許可の新規取得に要する費用（申請手数料、施設改修費用、食品衛生'
        '責任者養成講習会受講料等）は、甲の負担とする。ただし、乙の責めに'
        '帰すべき事由（施設基準違反の隠蔽、不実申告等）により追加費用が'
        '発生した場合は、乙の負担とする。', styles['body']))

    # Article 7
    story.append(Paragraph('第７条（営業空白期間の取扱い）',
                           styles['article_title']))
    story.append(Paragraph(
        '甲乙は、営業許可の空白期間（乙の廃業届提出から甲の新規許可取得まで）'
        'が生じないよう、第５条の手順に従い最大限の努力を払うものとする。'
        'やむを得ず空白期間が生じる場合、甲はその期間中、本店舗において'
        '飲食店営業を行わないものとし、これにより甲が被る損害（休業損害、'
        '人件費等）について、乙の責めに帰すべき事由による場合を除き、'
        '乙は責任を負わないものとする。', styles['body']))

    # Article 8 - Damages
    story.append(Paragraph('第８条（損害賠償）', styles['article_title']))
    story.append(Paragraph(
        '乙の責めに帰すべき事由（食品衛生法令違反、施設基準違反、'
        '虚偽情報の提供等）により甲が営業許可を取得できない場合、または'
        '取得が著しく遅延した場合、乙は甲に対し、これにより甲が被った'
        '損害（休業損害、改修費用、申請費用、弁護士費用を含む。）を'
        '賠償するものとする。', styles['body']))

    # Article 9 - Anti-social
    story.append(Paragraph('第９条（反社会的勢力の排除）', styles['article_title']))
    story.append(Paragraph(
        '甲及び乙は、自己又はその役員、従業員、株主、社員その他の関係者が、'
        '暴力団、暴力団員、暴力団準構成員、暴力団関係企業、総会屋その他の'
        '反社会的勢力に該当しないこと、かつ将来にわたり該当しないことを'
        '相互に表明し、保証する。', styles['body']))

    # Article 10
    story.append(Paragraph('第１０条（有効期間）', styles['article_title']))
    story.append(Paragraph(
        '本合意書は、締結日から、甲が新たな営業許可を取得し、かつ乙が'
        '廃業届を提出した日のいずれか遅い日まで効力を有するものとする。'
        'ただし、第８条（損害賠償）及び第９条（反社会的勢力の排除）の規定は、'
        '本合意書の終了後も存続するものとする。', styles['body']))

    # Article 11
    story.append(Paragraph('第１１条（不可抗力）', styles['article_title']))
    story.append(Paragraph(
        '天災地変、感染症の蔓延、行政機関の処理遅延その他甲乙の責めに帰す'
        'べからざる事由により本合意書に定める手続が遅滞した場合、当該当事者'
        'は責任を負わないものとし、甲乙協議の上、目標時期を変更することが'
        'できる。', styles['body']))

    # Article 12
    story.append(Paragraph('第１２条（通知）', styles['article_title']))
    story.append(Paragraph(
        '本合意書に関する通知、請求その他の意思表示は、書面（電子メールを'
        '含む。）により、相手方の住所、本店所在地または電子メールアドレス'
        '宛に行うものとする。', styles['body']))

    # Article 13
    story.append(Paragraph('第１３条（準拠法及び管轄）', styles['article_title']))
    story.append(Paragraph(
        '本合意書は、日本法に準拠するものとし、本合意書に関する紛争に'
        'ついては、東京地方裁判所を第一審の専属的合意管轄裁判所とする。',
        styles['body']))

    # Article 14
    story.append(Paragraph('第１４条（協議事項）', styles['article_title']))
    story.append(Paragraph(
        '本合意書に定めのない事項または本合意書の解釈に疑義が生じた場合は、'
        '甲乙誠意をもって協議の上、解決するものとする。', styles['body']))

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
    story.append(Paragraph(
        'Agreement on Assignment of Lease Rights', styles['subtitle']))
    add_header_line(story)

    story.append(Paragraph(
        '【ご注意】本合意書は甲乙二者間の合意書であり、民法第612条第1項に'
        'より、賃貸借権の譲渡には賃貸人（家主）の承諾が必要です。本合意書'
        'と併せて、別添の「賃貸人承諾書（雛形）」（文書番号'
        'EMT-SUHANA-2026-004）に賃貸人の署名押印を取得してください。',
        styles['warn']))

    story.append(Paragraph(
        f'{BUYER_NAME}（以下「甲」という。）と{SELLER_NAME}'
        '（以下「乙」という。）は、下記物件に係る賃貸借権の譲渡に関し、'
        '以下のとおり合意する。', styles['body']))

    # Article 1
    story.append(Paragraph('第１条（物件の表示）', styles['article_title']))
    story.append(Paragraph(
        '本合意書の対象となる物件（以下「本物件」という。）は、以下のとおり'
        'とする。', styles['body']))

    prop_data = [
        ['物件所在地', '東京都北区上十条五丁目14番6号'],
        ['用途', '飲食店（SUHANA Indian Nepal Restaurant）'],
        ['現賃借人', f'{SELLER_NAME}（代表：{SELLER_REP_NAME}）'],
        ['賃貸人（家主）',
         '氏名：_______________________　住所：_______________________'],
        ['原賃貸借契約',
         '契約日：令和___年___月___日　契約書番号：__________'],
        ['現行賃料', '月額　¥_____________（消費税___）'],
        ['共益費・管理費', '月額　¥_____________'],
        ['敷金 / 保証金', '金　¥_____________'],
        ['礼金（償却金）', '金　¥_____________'],
        ['原賃貸借契約期間',
         '令和___年___月___日 ～ 令和___年___月___日'],
        ['新賃借人としての契約期間',
         '令和8年5月1日 ～ 令和11年4月30日（3年間）（賃貸人合意による）'],
    ]
    story.append(Spacer(1, 2*mm))
    story.append(info_table(prop_data, key_width=42, val_width=118))

    story.append(Paragraph(
        '※ 賃貸人氏名、賃料、敷金等の金額は、賃貸人より提供される原賃貸借'
        '契約書の記載に基づき、本合意書締結前に確定するものとする。',
        styles['small']))

    # Article 2
    story.append(Paragraph('第２条（賃貸借権の譲渡）', styles['article_title']))
    story.append(Paragraph(
        '乙は、本物件に係る賃貸借契約上の賃借人としての地位（以下「賃貸借権」'
        'という。）を甲に譲渡し、甲はこれを譲り受けるものとする。ただし、'
        '本条に基づく賃貸借権の譲渡は、賃貸人の書面による承諾を得ることを'
        '停止条件とする。', styles['body']))

    # Article 3
    story.append(Paragraph('第３条（賃貸人の承諾取得）', styles['article_title']))
    story.append(Paragraph(
        '乙は、本合意書締結後7日以内に、賃貸人に対し、別添「賃貸人承諾書」'
        '（文書番号EMT-SUHANA-2026-004）に基づき、賃貸借権の譲渡について'
        '書面による承諾を求めるものとする。甲は、賃貸人が求める場合には、'
        '会社の登記事項証明書、決算書、代表者の身分証明書その他の信用情報を'
        '提供し、承諾取得に協力するものとする。', styles['body']))
    story.append(Paragraph(
        '２　賃貸人の承諾が得られない場合、甲乙は協議の上、賃貸人との間で'
        '甲を賃借人とする新たな賃貸借契約の締結を試みるものとし、乙は当該'
        '新規賃貸借契約締結に向け合理的な範囲で協力するものとする。',
        styles['body']))

    # Article 4
    story.append(Paragraph('第４条（譲渡の効力発生条件）', styles['article_title']))
    story.append(Paragraph(
        '賃貸借権の譲渡は、以下の条件を全て充足した時点で効力を生じるものとする。',
        styles['body']))
    items = [
        '（１）賃貸人の書面による承諾が得られること',
        '（２）事業譲渡契約書（文書番号EMT-SUHANA-2026-001）に基づく事業譲渡の'
        '効力が生じること',
        '（３）甲が飲食店営業許可を取得すること、または取得の見込みが客観的に'
        '確実であること',
        '（４）甲が乙に対し、第５条に定める敷金等相当額の支払を完了すること',
    ]
    for item in items:
        story.append(Paragraph(item, styles['body_no_indent']))

    # Article 5 - deposit
    story.append(Paragraph('第５条（敷金・保証金の取扱い）',
                           styles['article_title']))
    story.append(Paragraph(
        '本物件に係る敷金及び保証金（以下「敷金等」という。）の賃貸人に対する'
        '返還請求権は、賃貸借権の譲渡に伴い、乙から甲に移転するものとする。',
        styles['body']))
    story.append(Paragraph(
        '２　甲は、乙に対し、敷金等相当額（第１条に記載の金額）を、賃貸借権'
        '譲渡の効力発生日に銀行振込の方法により支払うものとする。ただし、'
        '譲渡日までに既存の原状回復義務違反その他乙の責めに帰すべき事由に'
        '基づく敷金等の控除事由が判明した場合、当該控除相当額を減額する'
        'ものとする。', styles['body']))
    story.append(Paragraph(
        '３　礼金（償却金）の取扱いは、賃貸人との協議により別途定めるものと'
        'する。', styles['body']))

    # Article 6
    story.append(Paragraph('第６条（賃貸借条件の承継）', styles['article_title']))
    story.append(Paragraph(
        '甲は、原則として、現行の賃貸借契約と同一の条件にて賃貸借を承継する'
        'ものとする。ただし、賃貸人との合意により条件が変更される場合は'
        'この限りでなく、甲は変更後の条件に従うものとする。', styles['body']))

    # Article 7
    story.append(Paragraph('第７条（原状回復義務の分担）', styles['article_title']))
    story.append(Paragraph(
        '譲渡日以前に生じた本物件の原状回復義務（乙又は乙の従業員、出入業者の'
        '行為に起因する毀損、汚損、改造等に係るもの）は乙が負担し、譲渡日'
        '以降に生じた原状回復義務は甲が負担するものとする。', styles['body']))
    story.append(Paragraph(
        '２　譲渡日において、甲乙立会いの下、本物件の現状を確認し、'
        '「物件現況確認書」を作成して甲乙双方が署名押印するものとする。',
        styles['body']))

    # Article 8
    story.append(Paragraph('第８条（物件の引渡し）', styles['article_title']))
    story.append(Paragraph(
        '乙は、譲渡日において、本物件を現状有姿にて甲に引き渡すものとする。'
        '乙は、引渡し時に本物件の鍵一切（合鍵を含む。）を甲に交付し、'
        '甲はその受領証を乙に交付するものとする。', styles['body']))

    # Article 9
    story.append(Paragraph('第９条（乙の表明保証）', styles['article_title']))
    story.append(Paragraph('乙は、甲に対し、以下の事項を表明し、保証する。',
                           styles['body']))
    items = [
        '（１）乙は、本物件の賃貸借契約上の義務を履行しており、賃料、共益費'
        'その他金銭債務の滞納その他の債務不履行がないこと',
        '（２）本物件について、第三者による転貸、占有その他の権利の設定が'
        'ないこと',
        '（３）本物件について、建物の構造・設備（給排水、電気、ガス、空調、'
        '排気ダクト等）に関し、乙が知り得る重大な瑕疵がないこと',
        '（４）本物件について、賃貸人から賃料増額請求、解約申入、改修要請'
        'その他の要求を受けていないこと',
        '（５）賃貸人との間で、未解決の紛争または係争（訴訟、調停、'
        'ADR等）がないこと',
        '（６）本物件において、過去に保健所、消防署その他の行政機関から'
        '是正命令、改善指導等を受けていないこと',
    ]
    for item in items:
        story.append(Paragraph(item, styles['body_no_indent']))

    # Article 10
    story.append(Paragraph('第１０条（費用負担）', styles['article_title']))
    story.append(Paragraph(
        '賃貸借権の譲渡に関して賃貸人に支払う承諾料その他の費用が発生する'
        '場合は、甲乙折半にて負担するものとする。ただし、甲乙協議の上、'
        '別段の定めをすることができる。', styles['body']))
    story.append(Paragraph(
        '２　不動産仲介業者の関与により仲介手数料が発生する場合、当該手数料の'
        '負担者は事前に甲乙協議の上決定するものとする。', styles['body']))

    # Article 11
    story.append(Paragraph('第１１条（契約不成立の場合）',
                           styles['article_title']))
    story.append(Paragraph(
        '賃貸人の承諾が得られず、かつ甲を賃借人とする新たな賃貸借契約の'
        '締結もできない場合、本合意書は効力を失うものとする。この場合、'
        '甲乙はそれぞれ相手方に対し、損害賠償その他の請求を行わない'
        'ものとする。ただし、乙の故意または過失により承諾不取得となった'
        '場合はこの限りでない。', styles['body']))

    # Article 12 - Anti-social
    story.append(Paragraph('第１２条（反社会的勢力の排除）',
                           styles['article_title']))
    story.append(Paragraph(
        '甲及び乙は、自己又はその役員、従業員、株主、社員その他の関係者が、'
        '暴力団、暴力団員、暴力団準構成員、暴力団関係企業、総会屋その他の'
        '反社会的勢力に該当しないこと、かつ将来にわたり該当しないことを'
        '相互に表明し、保証する。', styles['body']))

    # Article 13
    story.append(Paragraph('第１３条（不可抗力・通知）', styles['article_title']))
    story.append(Paragraph(
        '天災地変その他甲乙の責めに帰すべからざる事由により本合意書の履行が'
        '遅滞した場合、当該当事者は責任を負わないものとする。本合意書に'
        '関する通知は、書面（電子メールを含む。）により、相手方の本店'
        '所在地または電子メールアドレス宛に行うものとする。', styles['body']))

    # Article 14
    story.append(Paragraph('第１４条（準拠法及び管轄）', styles['article_title']))
    story.append(Paragraph(
        '本合意書は、日本法に準拠するものとし、本合意書に関する紛争に'
        'ついては、東京地方裁判所を第一審の専属的合意管轄裁判所とする。',
        styles['body']))

    add_signature_block(story, styles)
    add_doc_footer(story, styles, '2026-003')

    doc.build(story)
    print(f"Generated: {filepath}")
    return filepath


# ============================================================
# DOCUMENT 4: 賃貸人承諾書（雛形） — Landlord Consent Letter Template
# ============================================================
def generate_landlord_consent():
    styles = get_styles()
    filepath = os.path.join(OUTPUT_DIR, '04_賃貸人承諾書（雛形）.pdf')
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            topMargin=25*mm, bottomMargin=25*mm,
                            leftMargin=22*mm, rightMargin=22*mm)
    story = []

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('賃貸借権譲渡に関する承諾書', styles['title']))
    story.append(Paragraph(
        'Landlord Consent to Assignment of Lease', styles['subtitle']))
    add_header_line(story)

    story.append(Paragraph(
        '【書式について】本書は賃貸人（家主）から取得する承諾書の雛形です。'
        '賃貸人氏名、住所、賃料、敷金等の各欄に必要事項を記入の上、賃貸人の'
        '署名押印を取得してください。', styles['warn']))

    story.append(Paragraph(f'{CONTRACT_DATE_JP}（{CONTRACT_DATE_WESTERN}）',
                           styles['right']))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(f'譲渡人（現賃借人）：{SELLER_NAME}　御中',
                           styles['body_no_indent']))
    story.append(Paragraph(f'譲受人（新賃借人）：{BUYER_NAME}　御中',
                           styles['body_no_indent']))
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph('記', styles['center']))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        '私（以下「賃貸人」という。）は、下記物件に関する賃貸借契約について、'
        '現賃借人より新賃借人への賃貸借権の譲渡（賃借人としての地位の移転）'
        'に承諾いたします。', styles['body']))

    # Property
    story.append(Paragraph('１．対象物件', styles['article_title']))
    prop_data = [
        ['所在地', '東京都北区上十条五丁目14番6号'],
        ['用途', '飲食店（SUHANA Indian Nepal Restaurant）'],
    ]
    story.append(info_table(prop_data, key_width=35, val_width=125))

    # Original lease
    story.append(Paragraph('２．原賃貸借契約の表示', styles['article_title']))
    orig_data = [
        ['原賃貸借契約締結日', '令和___年___月___日'],
        ['契約期間',
         '令和___年___月___日 ～ 令和___年___月___日'],
        ['月額賃料', '¥_____________（消費税___）'],
        ['共益費・管理費', '¥_____________'],
        ['敷金 / 保証金', '¥_____________'],
        ['礼金（償却）', '¥_____________'],
    ]
    story.append(info_table(orig_data, key_width=42, val_width=118))

    # Parties
    story.append(Paragraph('３．譲渡当事者', styles['article_title']))
    party_data = [
        ['現賃借人（譲渡人）', f'{SELLER_NAME}（代表：{SELLER_REP_NAME}）'],
        ['新賃借人（譲受人）', f'{BUYER_NAME}（{BUYER_REP_TITLE}：{BUYER_REP_NAME}）'],
        ['新賃借人所在地', BUYER_ADDR],
        ['譲渡予定日', f'令和8年（2026年）5月1日'],
    ]
    story.append(info_table(party_data, key_width=42, val_width=118))

    # Consent terms
    story.append(Paragraph('４．承諾の内容', styles['article_title']))
    items = [
        '（１）賃貸人は、現賃借人から新賃借人への賃貸借権譲渡（地位移転）に'
        '承諾する。',
        '（２）譲渡日以降、賃貸人と新賃借人との間に、原賃貸借契約と同一の'
        '内容の賃貸借契約関係が成立するものとする。ただし、賃貸人と新賃借人'
        '間の協議により条件を変更する場合はこの限りでない。',
        '（３）譲渡日以降の賃料、共益費その他の支払債務は、新賃借人が負担'
        'するものとする。',
        '（４）譲渡日前日までの賃料、共益費等の未払があれば、現賃借人が'
        'これを負担し、譲渡日までに完済する。',
        '（５）敷金及び保証金は、譲渡日以降、新賃借人が差し入れたものと'
        'みなし、賃貸借終了時には新賃借人に対し返還する。',
    ]
    for item in items:
        story.append(Paragraph(item, styles['body_no_indent']))

    # Optional consent fee
    story.append(Paragraph('５．承諾料（該当する場合）', styles['article_title']))
    story.append(Paragraph(
        '本譲渡に関する承諾料：¥_____________（金　　　　　　円）',
        styles['body_no_indent']))
    story.append(Paragraph(
        '上記承諾料は、譲渡日までに、賃貸人指定口座に振込の方法により'
        '支払うものとする。', styles['body_no_indent']))

    # Use restriction
    story.append(Paragraph('６．用途の制限', styles['article_title']))
    story.append(Paragraph(
        '新賃借人は、本物件を飲食店（インド料理・ネパール料理を主とする'
        'レストラン）以外の用途に使用してはならず、賃貸人の事前書面承諾'
        'なくして用途を変更してはならない。', styles['body']))

    # Other
    story.append(Paragraph('７．その他', styles['article_title']))
    story.append(Paragraph(
        '本承諾書に定めのない事項は、原賃貸借契約の定めに従うものとする。',
        styles['body']))

    # Signature - landlord
    story.append(Spacer(1, 12*mm))
    story.append(Paragraph('以上、上記内容を承諾いたします。', styles['body']))
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(f'承諾日：　令和___年___月___日',
                           styles['body_no_indent']))
    story.append(Spacer(1, 10*mm))

    landlord_sig = [
        [Paragraph('<b>【賃貸人】</b>', styles['signature_label']), ''],
        [Paragraph('氏名／商号：', styles['signature_line']),
         Paragraph('_______________________　　　　印（実印）',
                   styles['signature_line'])],
        [Paragraph('住所：', styles['signature_line']),
         Paragraph('_______________________', styles['signature_line'])],
        [Paragraph('電話番号：', styles['signature_line']),
         Paragraph('_______________________', styles['signature_line'])],
    ]
    t = Table(landlord_sig, colWidths=[35*mm, 115*mm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBELOW', (1, 1), (1, 3), 0.5, LINE_COLOR),
    ]))
    story.append(t)

    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(
        '【写し】本承諾書の写しを、現賃借人及び新賃借人にそれぞれ1通ずつ'
        '交付するものとする。', styles['small']))

    add_doc_footer(story, styles, '2026-004')

    doc.build(story)
    print(f"Generated: {filepath}")
    return filepath


# ============================================================
# DOCUMENT 5: 別紙_資産目録（雛形） — Asset Inventory Template
# ============================================================
def generate_asset_inventory():
    styles = get_styles()
    filepath = os.path.join(OUTPUT_DIR, '05_別紙１_資産目録.pdf')
    # Remove obsolete template filename from previous runs
    legacy = os.path.join(OUTPUT_DIR, '05_別紙_資産目録（雛形）.pdf')
    if os.path.exists(legacy):
        os.remove(legacy)
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            topMargin=25*mm, bottomMargin=25*mm,
                            leftMargin=22*mm, rightMargin=22*mm)
    story = []

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('別紙１　資 産 目 録', styles['title']))
    story.append(Paragraph(
        'Schedule 1 — Asset Inventory（事業譲渡契約書 文書番号EMT-SUHANA-2026-001添付）',
        styles['subtitle']))
    add_header_line(story)

    story.append(Paragraph(
        '【注記】本資産目録は、事業譲渡契約書（文書番号EMT-SUHANA-2026-001）'
        '第２条第１項第２号に基づき、譲渡対象となる什器・備品・厨房設備等を'
        '特定するものである。品目及び数量は乙の申告に基づき記載されており、'
        '型式・規格、状態、推定価額の各欄については、譲渡日（令和8年5月1日'
        '予定）に甲乙立会いの上で実物確認し、本書に追記の上、甲乙双方が'
        '署名押印するものとする。本目録に記載のない物品は譲渡対象外とする。',
        styles['warn']))

    story.append(Paragraph('１．厨房設備', styles['article_title']))
    kitchen_data = [
        ['No.', '品名', '型式・規格', '数量', '状態', '推定価額（円）', '備考'],
        ['1', '冷蔵庫', '__________', '1台', '__', '__________', ''],
        ['2', '冷蔵保管庫（ストレージ）', '__________', '1台', '__', '__________', ''],
        ['3', '冷蔵ショーケース（飲料ディスプレイ）',
         '__________', '1台', '__', '__________', ''],
        ['4', 'タンドール窯一式', '__________', '1式', '__', '__________', ''],
        ['5', '製氷機', '__________', '1台', '__', '__________', ''],
        ['6', '電子レンジ', '__________', '1台', '__', '__________', ''],
        ['7', '炊飯器', '__________', '1台', '__', '__________', ''],
        ['8', '換気フード・排気ダクト', '__________', '1式', '__', '__________', ''],
        ['9', 'シンク', '__________', '1式', '__', '__________', ''],
        ['10', '作業台（プレップテーブル）', '__________', '__', '__', '__________',
         '※ 数量要確認'],
        ['11', '収納棚・ストレージシェルフ', '__________', '__', '__', '__________',
         '※ 数量要確認'],
    ]
    t = Table(kitchen_data,
              colWidths=[10*mm, 38*mm, 28*mm, 12*mm, 14*mm, 26*mm, 32*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 8),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 8),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('ALIGN', (4, 0), (4, -1), 'CENTER'),
        ('ALIGN', (5, 0), (5, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    story.append(Paragraph('２．客席・ホール備品', styles['article_title']))
    hall_data = [
        ['No.', '品名', '型式・規格', '数量', '状態', '推定価額（円）', '備考'],
        ['1', 'テーブル', '__________', '3台', '__', '__________', ''],
        ['2', '椅子', '__________', '12脚', '__', '__________', ''],
        ['3', 'テレビ（32インチ）', '__________', '1台', '__', '__________', ''],
        ['4', 'エアコン（空調設備）', '__________', '__', '__', '__________',
         '※ 数量要確認'],
        ['5', 'POS・レジスター', '__________', '1式', '__', '__________', ''],
        ['6', '照明器具', '__________', '1式', '__', '__________', ''],
        ['7', '看板（店頭・店内）', '__________', '1式', '__', '__________',
         '※ 屋外・屋内分要確認'],
    ]
    t = Table(hall_data,
              colWidths=[10*mm, 38*mm, 28*mm, 12*mm, 14*mm, 26*mm, 32*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 8),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 8),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('ALIGN', (4, 0), (4, -1), 'CENTER'),
        ('ALIGN', (5, 0), (5, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    story.append(Paragraph('３．食器・調理器具', styles['article_title']))
    tableware_data = [
        ['No.', '品名', '数量', '状態', '備考'],
        ['1', '調理器具及び食器一式（鍋・フライパン・包丁・まな板・'
         'お玉・ざる・皿・グラス・カトラリー等、現状の一切）',
         '1式', '__', '※ 譲渡日に甲乙立会いの上で現物確認・引渡'],
    ]
    t = Table(tableware_data,
              colWidths=[10*mm, 60*mm, 22*mm, 18*mm, 50*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 8),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 8),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    # Notes
    story.append(Paragraph('４．状態の凡例', styles['article_title']))
    story.append(Paragraph(
        'A：新品同様　／　B：良好（通常使用に支障なし）　／　'
        'C：使用感あり（機能上の支障なし）　／　D：要修理',
        styles['body_no_indent']))

    # Confirmation
    story.append(Paragraph('５．引渡確認', styles['article_title']))
    story.append(Paragraph(
        '上記資産については、令和8年（2026年）　月　日、本物件において'
        '甲乙立会いの上、現状有姿にて確認・引渡を完了した。',
        styles['body']))

    story.append(Spacer(1, 10*mm))

    sig_data = [
        [Paragraph('<b>【甲】　譲受人</b>', styles['signature_label']),
         Paragraph('<b>【乙】　譲渡人</b>', styles['signature_label'])],
        [Paragraph(BUYER_NAME, styles['signature_line']),
         Paragraph(SELLER_NAME, styles['signature_line'])],
        [Paragraph(f'{BUYER_REP_TITLE}：{BUYER_REP_NAME}　印',
                   styles['signature_line']),
         Paragraph(f'代表者：{SELLER_REP_NAME}　印',
                   styles['signature_line'])],
    ]
    t = Table(sig_data, colWidths=[80*mm, 80*mm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 2), (1, 2), 0.5, LINE_COLOR),
    ]))
    story.append(t)

    add_doc_footer(story, styles, '2026-001-A1')

    doc.build(story)
    print(f"Generated: {filepath}")
    return filepath


# ============================================================
# DOCUMENT 6: 賃借権譲渡承諾願書 — Request for Landlord Consent
# ============================================================
def generate_lease_consent_request():
    styles = get_styles()
    filepath = os.path.join(OUTPUT_DIR, '06_賃借権譲渡承諾願書.pdf')
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            topMargin=25*mm, bottomMargin=25*mm,
                            leftMargin=22*mm, rightMargin=22*mm)
    story = []

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('賃借権譲渡承諾願書', styles['title']))
    story.append(Paragraph(
        'Request for Landlord Consent to Lease Assignment',
        styles['subtitle']))
    add_header_line(story)

    story.append(Paragraph(
        '【書式について】本書は、現賃借人（乙）が賃貸人（家主）に対し、賃借権の'
        '譲渡について書面による承諾を求めるための正式な願書です。民法第612条'
        '第1項に基づく手続として必要です。賃貸人氏名・住所欄を記入の上、'
        '現賃借人の署名押印を取得し、原賃貸借契約書の写し及び譲受人の'
        '信用情報（登記事項証明書、決算書、代表者身分証明書）を添付して'
        '賃貸人に提出してください。', styles['warn']))

    story.append(Paragraph(f'{CONTRACT_DATE_JP}（{CONTRACT_DATE_WESTERN}）',
                           styles['right']))
    story.append(Spacer(1, 4*mm))

    # Addressee
    addressee = [
        [Paragraph('賃貸人：', styles['signature_line']),
         Paragraph('氏名／商号　_______________________　御中',
                   styles['signature_line'])],
        [Paragraph('', styles['signature_line']),
         Paragraph('住所　　　　_______________________',
                   styles['signature_line'])],
    ]
    t = Table(addressee, colWidths=[22*mm, 128*mm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 6*mm))

    # Requestor (seller)
    story.append(Paragraph('願出人（現賃借人）', styles['article_title']))
    req_data = [
        ['商号', SELLER_NAME],
        ['所在地', SELLER_ADDR],
        ['代表者', f'{SELLER_REP_NAME}　　印（実印）'],
    ]
    story.append(info_table(req_data, key_width=30, val_width=130))
    story.append(Spacer(1, 6*mm))

    # Body
    story.append(Paragraph(
        '拝啓　時下ますますご清栄のこととお慶び申し上げます。平素より格別の'
        'ご高配を賜り、厚く御礼申し上げます。',
        styles['body']))
    story.append(Paragraph(
        'さて、当社（願出人）は、貴殿より賃借しております下記物件について、'
        'この度、eMoment Japan合同会社（以下「譲受人」という。）に対し、'
        '賃借権を譲渡し、賃借人としての地位を移転することにつき基本合意に'
        '至りました（文書番号EMT-SUHANA-2026-003「賃貸借権譲渡に関する'
        '合意書」）。',
        styles['body']))
    story.append(Paragraph(
        'つきましては、民法第612条第1項の定めに従い、貴殿に対し当該譲渡に'
        'ついて書面による承諾を賜りたく、本書をもって謹んでお願い申し上げ'
        'ます。',
        styles['body']))

    # Property
    story.append(Paragraph('１．対象物件', styles['article_title']))
    prop_data = [
        ['所在地', '東京都北区上十条五丁目14番6号'],
        ['用途', '飲食店（SUHANA Indian Nepal Restaurant）'],
        ['原賃貸借契約締結日', '令和___年___月___日'],
        ['契約期間', '令和___年___月___日 ～ 令和___年___月___日'],
        ['月額賃料', '¥_____________（消費税___）'],
    ]
    story.append(info_table(prop_data, key_width=42, val_width=118))

    # Assignee
    story.append(Paragraph('２．譲受人（新賃借人）の表示',
                           styles['article_title']))
    assignee_data = [
        ['商号', BUYER_NAME],
        ['所在地', BUYER_ADDR],
        ['代表者', f'{BUYER_REP_TITLE}　{BUYER_REP_NAME}'],
        ['事業目的', '飲食店経営（インド料理・ネパール料理）'],
        ['設立年月日', '（登記事項証明書のとおり）'],
    ]
    story.append(info_table(assignee_data, key_width=30, val_width=130))

    # Proposed transfer
    story.append(Paragraph('３．譲渡予定日', styles['article_title']))
    story.append(Paragraph(
        '令和8年（2026年）5月1日（貴殿の承諾を得られ次第、正式に確定する。）',
        styles['body_no_indent']))

    # Continuation terms
    story.append(Paragraph('４．譲渡後の賃貸借条件', styles['article_title']))
    items = [
        '（１）譲受人は、原賃貸借契約の全条項（賃料、共益費、契約期間、'
        '用途、禁止事項、その他一切）を誠実に遵守し、原賃借人の地位を'
        '全面的に承継するものとします。',
        '（２）譲渡日以降の賃料、共益費その他支払債務は、譲受人が負担'
        'します。譲渡日前日までの未払債務があれば願出人がこれを完済の上、'
        '譲渡に応じるものとします。',
        '（３）敷金及び保証金は、譲渡日以降、譲受人が差し入れたものと'
        'みなし、賃貸借終了時には譲受人に対し返還願います。',
        '（４）本物件の用途は、現状どおり飲食店（インド料理・ネパール'
        '料理を主とするレストラン）とし、貴殿の事前書面承諾なくして'
        '用途を変更することはございません。',
    ]
    for item in items:
        story.append(Paragraph(item, styles['body_no_indent']))

    # Attachments
    story.append(Paragraph('５．添付書類', styles['article_title']))
    attachments = [
        '（１）賃貸借権譲渡に関する合意書の写し（文書番号EMT-SUHANA-2026-003）',
        '（２）譲受人　eMoment Japan合同会社の登記事項証明書',
        '（３）譲受人　代表社員の身分証明書（運転免許証・在留カード等の写し）',
        '（４）譲受人の直近決算書または事業計画書',
        '（５）賃貸人承諾書（雛形）（文書番号EMT-SUHANA-2026-004）',
    ]
    for item in attachments:
        story.append(Paragraph(item, styles['body_no_indent']))

    # Closing
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        'つきましては、ご多忙中誠に恐縮ではございますが、別添「賃貸人'
        '承諾書」（文書番号EMT-SUHANA-2026-004）にご署名ご捺印の上、'
        '下記連絡先までご返送賜りますよう、何卒よろしくお願い申し上げ'
        'ます。',
        styles['body']))
    story.append(Paragraph('敬具', styles['right']))

    # Contact
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph('６．連絡先', styles['article_title']))
    contact_data = [
        ['担当', f'{SELLER_NAME}　{SELLER_REP_NAME}'],
        ['電話番号', '_______________________'],
        ['Email', '_______________________'],
        ['返送先住所', SELLER_ADDR],
    ]
    story.append(info_table(contact_data, key_width=30, val_width=130))

    # Signature
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph('以上', styles['right']))
    story.append(Spacer(1, 8*mm))

    sig_data = [
        [Paragraph('<b>願出人（現賃借人）</b>', styles['signature_label']), ''],
        [Paragraph('商号：', styles['signature_line']),
         Paragraph(SELLER_NAME, styles['signature_line'])],
        [Paragraph('代表者：', styles['signature_line']),
         Paragraph(f'{SELLER_REP_NAME}　　　　　　印（実印）',
                   styles['signature_line'])],
    ]
    t = Table(sig_data, colWidths=[30*mm, 120*mm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBELOW', (1, 2), (1, 2), 0.5, LINE_COLOR),
    ]))
    story.append(t)

    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(
        '【写し】本願書の写しを、譲受人（eMoment Japan合同会社）にも'
        '1通交付するものとする。',
        styles['small']))

    add_doc_footer(story, styles, '2026-005')

    doc.build(story)
    print(f"Generated: {filepath}")
    return filepath


# ============================================================
# DOCUMENT 7: 別紙２_在庫品目録（雛形） — Stock Inventory Template
# ============================================================
def generate_stock_inventory():
    styles = get_styles()
    filepath = os.path.join(OUTPUT_DIR, '07_別紙２_在庫品目録.pdf')
    # Remove obsolete template filename from previous runs
    legacy = os.path.join(OUTPUT_DIR, '07_別紙２_在庫品目録（雛形）.pdf')
    if os.path.exists(legacy):
        os.remove(legacy)
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            topMargin=25*mm, bottomMargin=25*mm,
                            leftMargin=22*mm, rightMargin=22*mm)
    story = []

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('別紙２　在 庫 品 目 録', styles['title']))
    story.append(Paragraph(
        'Schedule 2 — Stock Inventory（事業譲渡契約書 文書番号EMT-SUHANA-2026-001添付）',
        styles['subtitle']))
    add_header_line(story)

    story.append(Paragraph(
        '【注記】本在庫品目録は、事業譲渡契約書（文書番号EMT-SUHANA-2026-001）'
        '第２条第１項第３号に基づき、譲渡日時点における食材・飲料等の在庫を'
        '特定するものである。品目及び数量は乙の申告に基づき記載されており、'
        '譲渡日（令和8年5月1日予定）に甲乙立会いの上で実地棚卸を実施し、'
        '数量・状態を最終確認の上、甲乙双方が署名押印するものとする。'
        '賞味期限切れ・状態不良の物品は譲渡対象から除外し、乙の責任と'
        '費用負担で処分するものとする。',
        styles['warn']))

    # 1. Food ingredients
    story.append(Paragraph('１．食材（生鮮・冷蔵・冷凍）', styles['article_title']))
    food_data = [
        ['No.', '品目', '規格・単位', '数量', '状態', '推定価額（円）', '備考'],
        ['1', '米', '__________', '10kg', '__', '__________', ''],
        ['2', '肉類', '__________', '10kg', '__', '__________', '※ 種別要確認'],
        ['3', 'インドスパイス類（各種）', '__________', '1式', '__', '__________',
         '※ 内訳は現物確認時に特定'],
        ['4', '食用油（調理油）', '__________', '1L', '__', '__________', ''],
    ]
    t = Table(food_data,
              colWidths=[10*mm, 44*mm, 26*mm, 14*mm, 12*mm, 24*mm, 30*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 8),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 8),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('ALIGN', (4, 0), (4, -1), 'CENTER'),
        ('ALIGN', (5, 0), (5, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    # 2. Beverages
    story.append(Paragraph('２．飲料（アルコール／ノンアルコール）',
                           styles['article_title']))
    bev_data = [
        ['No.', '品目', '規格・単位', '数量', '状態', '推定価額（円）', '備考'],
        ['1', 'ソフトドリンク', '__________', '10L', '__', '__________',
         '※ 種類・容器形態は現物確認'],
        ['2', '酒類（ハードドリンク）', '__________', '20本', '__', '__________',
         '※ 種類・アルコール度数は現物確認'],
    ]
    t = Table(bev_data,
              colWidths=[10*mm, 44*mm, 26*mm, 14*mm, 12*mm, 24*mm, 30*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 8),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 8),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('ALIGN', (4, 0), (4, -1), 'CENTER'),
        ('ALIGN', (5, 0), (5, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    # 3. Consumables
    story.append(Paragraph('３．消耗品・雑貨', styles['article_title']))
    consume_data = [
        ['No.', '品目', '規格・単位', '数量', '状態', '推定価額（円）', '備考'],
        ['1', '消耗品一式（容器・紙ナプキン・洗剤・その他）',
         '__________', '現状一切', '__', '__________',
         '※ 乙申告なし — 譲渡日現物確認'],
    ]
    t = Table(consume_data,
              colWidths=[10*mm, 44*mm, 26*mm, 14*mm, 12*mm, 24*mm, 30*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 8),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 8),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('ALIGN', (4, 0), (4, -1), 'CENTER'),
        ('ALIGN', (5, 0), (5, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    # Totals
    story.append(Paragraph('４．小計', styles['article_title']))
    total_data = [
        ['区分', '推定価額（円）'],
        ['１．食材', '¥_____________'],
        ['２．飲料', '¥_____________'],
        ['３．消耗品・雑貨', '¥_____________'],
        ['合計', '¥_____________'],
    ]
    t = Table(total_data, colWidths=[80*mm, 60*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 9),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 9),
        ('FONT', (0, -1), (-1, -1), GOTHIC, 9),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

    # Legend and exclusions
    story.append(Paragraph('５．状態の凡例', styles['article_title']))
    story.append(Paragraph(
        'A：新鮮・未開封　／　B：開封済（使用可能）　／　'
        'C：要早期使用　／　D：賞味期限切れ（譲渡対象外・乙が処分）',
        styles['body_no_indent']))

    story.append(Paragraph('６．除外品', styles['article_title']))
    story.append(Paragraph(
        '賞味期限を経過した食材・飲料、開封後長期経過により品質劣化した'
        '物品、食品衛生法上の基準を満たさない物品は、本目録の対象外と'
        'し、乙の責任と費用負担において譲渡日までに処分するものとする。',
        styles['body']))

    # Confirmation
    story.append(Paragraph('７．引渡確認', styles['article_title']))
    story.append(Paragraph(
        '上記在庫品については、令和8年（2026年）　月　日、本物件において'
        '甲乙立会いの上、実地棚卸を実施し、現状有姿にて確認・引渡を'
        '完了した。',
        styles['body']))

    story.append(Spacer(1, 10*mm))

    sig_data = [
        [Paragraph('<b>【甲】　譲受人</b>', styles['signature_label']),
         Paragraph('<b>【乙】　譲渡人</b>', styles['signature_label'])],
        [Paragraph(BUYER_NAME, styles['signature_line']),
         Paragraph(SELLER_NAME, styles['signature_line'])],
        [Paragraph(f'{BUYER_REP_TITLE}：{BUYER_REP_NAME}　印',
                   styles['signature_line']),
         Paragraph(f'代表者：{SELLER_REP_NAME}　印',
                   styles['signature_line'])],
    ]
    t = Table(sig_data, colWidths=[80*mm, 80*mm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 2), (1, 2), 0.5, LINE_COLOR),
    ]))
    story.append(t)

    add_doc_footer(story, styles, '2026-001-A2')

    doc.build(story)
    print(f"Generated: {filepath}")
    return filepath


# ============================================================
# DOCUMENT 8: 別紙３_既払金振込明細書（Payment Receipts Cover)
# ============================================================
def generate_payment_receipts_cover():
    styles = get_styles()
    filepath = os.path.join(OUTPUT_DIR, '08_別紙３_既払金振込明細書.pdf')
    # Remove obsolete filenames from previous runs
    for legacy_name in [
        '08_別紙３_取引先一覧（雛形）.pdf',
        '08_別紙３_取引先一覧.pdf',
    ]:
        legacy = os.path.join(OUTPUT_DIR, legacy_name)
        if os.path.exists(legacy):
            os.remove(legacy)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            topMargin=25*mm, bottomMargin=25*mm,
                            leftMargin=22*mm, rightMargin=22*mm)
    story = []

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('別紙３　既払金振込明細書', styles['title']))
    story.append(Paragraph(
        'Schedule 3 — Payment Receipts Schedule（事業譲渡契約書 文書番号EMT-SUHANA-2026-001添付）',
        styles['subtitle']))
    add_header_line(story)

    story.append(Paragraph(
        '【注記】本明細書は、事業譲渡契約書（文書番号EMT-SUHANA-2026-001）'
        '第３条第２項に基づき、甲が乙に対し既に支払った譲渡対価の一部に'
        'ついて、振込明細の一覧を示すものである。各振込の証憑（Wise取引'
        '明細書・銀行振込受領書等）の写しを本明細書に添付する。',
        styles['warn']))

    story.append(Paragraph('１．既払金一覧', styles['article_title']))
    receipts = [
        ['No.', '支払日', '区分', '金額（円）', '支払方法', '振込先口座', '取引番号／参照番号'],
        ['1', '令和8年3月18日\n(2026-03-18)', '手付金', '¥100,000',
         'Wise銀行振込',
         'ゆうちょ銀行\n5167306 / 9900-018\nラミツアネ デリ ラザ',
         'Wise #2028470429\n1784050398TW0'],
        ['2', '令和8年3月24日\n(2026-03-24)', '中間金①', '¥500,000',
         'Wise銀行振込',
         '東京東信用金庫\n両国支店 1320-101\n口座4136776\nRIONA株式会社',
         'Wise #2037504590\n1792447262TW0'],
        ['3', '令和8年4月1日\n(2026-04-01)', '中間金②', '¥500,000',
         '楽天銀行振込',
         'RIONA株式会社\n（口座詳細 — 要確認）',
         '（取引番号 — 要確認）'],
        ['', '', '既払合計', '¥1,100,000', '', '', ''],
    ]
    t = Table(receipts,
              colWidths=[8*mm, 22*mm, 20*mm, 22*mm, 22*mm, 36*mm, 30*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 7),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 7),
        ('FONT', (0, -1), (-1, -1), GOTHIC, 8),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    # Note on receipt attachment
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        '<b>【証憑添付について】</b>上記No.3（令和8年4月1日 ¥500,000 楽天'
        '銀行振込）の振込明細書については、本契約締結時までに甲が楽天銀行'
        'より発行される取引明細書の原本（または電子明細のPDF写し）を'
        '本明細書に添付し、記載事項（取引番号・振込先口座）を完備する'
        'ものとする。',
        styles['warn']))

    # Remaining balance section
    story.append(Paragraph('２．残代金', styles['article_title']))
    remaining = [
        ['項目', '金額（円）', '支払予定日'],
        ['譲渡対価（税抜）', '¥1,850,000', ''],
        ['（控除）既払合計', '△¥1,100,000', ''],
        ['残代金（税抜）', '¥750,000', '令和8年4月30日まで'],
        ['消費税（10％）', '¥185,000', '残代金支払時'],
        ['残払込予定額 合計', '¥935,000', ''],
    ]
    t = Table(remaining, colWidths=[60*mm, 50*mm, 50*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 9),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 9),
        ('FONT', (0, -1), (-1, -1), GOTHIC, 9),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

    # Attachments checklist
    story.append(Paragraph('３．添付証憑（別添）', styles['article_title']))
    items = [
        '（１）Wise取引明細書 — 令和8年3月18日 ¥100,000（取引番号2028470429）',
        '（２）Wise取引明細書 — 令和8年3月24日 ¥500,000（取引番号2037504590）',
        '（３）楽天銀行振込明細書 — 令和8年4月1日 ¥500,000（※ 乙より原本提示）',
    ]
    for item in items:
        story.append(Paragraph(item, styles['body_no_indent']))

    story.append(Paragraph('４．確認', styles['article_title']))
    story.append(Paragraph(
        '甲乙は、上記既払金の内容及び振込証憑について相互に確認し、'
        '本明細書に記載の既払合計額を事業譲渡契約書第３条第１項に定める'
        '譲渡対価の一部として充当することを確認した。',
        styles['body']))

    story.append(Spacer(1, 10*mm))

    sig_data = [
        [Paragraph('<b>【甲】　譲受人</b>', styles['signature_label']),
         Paragraph('<b>【乙】　譲渡人</b>', styles['signature_label'])],
        [Paragraph(BUYER_NAME, styles['signature_line']),
         Paragraph(SELLER_NAME, styles['signature_line'])],
        [Paragraph(f'{BUYER_REP_TITLE}：{BUYER_REP_NAME}　印',
                   styles['signature_line']),
         Paragraph(f'代表者：{SELLER_REP_NAME}　印',
                   styles['signature_line'])],
    ]
    t = Table(sig_data, colWidths=[80*mm, 80*mm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 2), (1, 2), 0.5, LINE_COLOR),
    ]))
    story.append(t)

    add_doc_footer(story, styles, '2026-001-A3')

    doc.build(story)
    print(f"Generated: {filepath}")
    return filepath


# ============================================================
# DEPRECATED: old supplier list function — kept for reference but not called
# ============================================================
def _deprecated_generate_supplier_list():
    styles = get_styles()
    filepath = os.path.join(OUTPUT_DIR, '_deprecated_supplier_list.pdf')
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            topMargin=25*mm, bottomMargin=25*mm,
                            leftMargin=22*mm, rightMargin=22*mm)
    story = []

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph('別紙３　取 引 先 一 覧', styles['title']))
    story.append(Paragraph(
        'Schedule 3 — Supplier & Counterparty List（事業譲渡契約書 文書番号EMT-SUHANA-2026-001添付）',
        styles['subtitle']))
    add_header_line(story)

    story.append(Paragraph(
        '【書式について】本取引先一覧は、事業譲渡契約書（文書番号'
        'EMT-SUHANA-2026-001）第２条第１項第４号に基づき、本事業に係る'
        '仕入先・業務委託先・サービス提供者等の取引関係を特定するための'
        '雛形です。各取引先の担当者・連絡先・契約形態・未払債務の有無を'
        '明記の上、乙は甲に対し、譲渡日までに各取引先への紹介及び引継を'
        '行うものとします。', styles['warn']))

    # 1. Food ingredient suppliers
    story.append(Paragraph('１．食材仕入先', styles['article_title']))
    food_sup = [
        ['No.', '取引先名', '担当者', '電話／Email', '取扱品目', '支払条件', '未払債務'],
        ['1', '__________', '__________', '__________', '__________', '__________', '¥______'],
        ['2', '__________', '__________', '__________', '__________', '__________', '¥______'],
        ['3', '__________', '__________', '__________', '__________', '__________', '¥______'],
        ['4', '__________', '__________', '__________', '__________', '__________', '¥______'],
    ]
    t = Table(food_sup,
              colWidths=[8*mm, 28*mm, 22*mm, 28*mm, 24*mm, 22*mm, 22*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 7),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 7),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (6, 0), (6, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    # 2. Beverage suppliers
    story.append(Paragraph('２．飲料・酒類仕入先', styles['article_title']))
    bev_sup = [
        ['No.', '取引先名', '担当者', '電話／Email', '取扱品目', '支払条件', '未払債務'],
        ['1', '__________', '__________', '__________', '__________', '__________', '¥______'],
        ['2', '__________', '__________', '__________', '__________', '__________', '¥______'],
        ['3', '__________', '__________', '__________', '__________', '__________', '¥______'],
    ]
    t = Table(bev_sup,
              colWidths=[8*mm, 28*mm, 22*mm, 28*mm, 24*mm, 22*mm, 22*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 7),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 7),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (6, 0), (6, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    # 3. Delivery platforms
    story.append(Paragraph('３．出前・デリバリーサービス',
                           styles['article_title']))
    delivery = [
        ['No.', 'プラットフォーム', '店舗ID／アカウント', '契約形態', '手数料率', '未清算残高'],
        ['1', 'Uber Eats', '__________', '__________', '__________', '¥______'],
        ['2', '出前館', '__________', '__________', '__________', '¥______'],
        ['3', 'Wolt', '__________', '__________', '__________', '¥______'],
        ['4', 'menu', '__________', '__________', '__________', '¥______'],
        ['5', 'その他', '__________', '__________', '__________', '¥______'],
    ]
    t = Table(delivery,
              colWidths=[8*mm, 28*mm, 34*mm, 28*mm, 24*mm, 32*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 7),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 7),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (5, 0), (5, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    # 4. Utilities & telecom
    story.append(Paragraph('４．光熱費・通信・インフラ契約',
                           styles['article_title']))
    util = [
        ['No.', '契約先', 'サービス種別', '契約者名義', '契約番号', '月額概算', '備考'],
        ['1', '東京電力', '電気', '__________', '__________', '¥______', ''],
        ['2', '東京ガス', 'ガス', '__________', '__________', '¥______', ''],
        ['3', '東京都水道局', '水道', '__________', '__________', '¥______', ''],
        ['4', 'NTT等', '固定電話', '__________', '__________', '¥______', ''],
        ['5', 'ISP', 'インターネット', '__________', '__________', '¥______', ''],
        ['6', 'その他', '__________', '__________', '__________', '¥______', ''],
    ]
    t = Table(util,
              colWidths=[8*mm, 24*mm, 22*mm, 26*mm, 26*mm, 20*mm, 28*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 7),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 7),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (5, 0), (5, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    # 5. Services (cleaning, pest, POS, accounting, etc.)
    story.append(Paragraph('５．業務委託・保守契約',
                           styles['article_title']))
    services = [
        ['No.', '取引先名', 'サービス種別', '連絡先', '契約期間', '月額', '備考'],
        ['1', '__________', '清掃・害虫駆除', '__________', '__________', '¥______', ''],
        ['2', '__________', 'POS・レジ保守', '__________', '__________', '¥______', ''],
        ['3', '__________', '会計・税務', '__________', '__________', '¥______', ''],
        ['4', '__________', '厨房機器保守', '__________', '__________', '¥______', ''],
        ['5', '__________', 'リース契約', '__________', '__________', '¥______', ''],
        ['6', '__________', 'その他', '__________', '__________', '¥______', ''],
    ]
    t = Table(services,
              colWidths=[8*mm, 28*mm, 24*mm, 28*mm, 28*mm, 20*mm, 18*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 7),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 7),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (5, 0), (5, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    # 6. Online accounts
    story.append(Paragraph('６．オンライン予約・SNS・Webアカウント',
                           styles['article_title']))
    online = [
        ['No.', 'サービス', 'アカウント／URL', 'ログインID', '引継方法', '備考'],
        ['1', 'Google Business Profile', '__________', '__________', '__________', ''],
        ['2', 'Tabelog（食べログ）', '__________', '__________', '__________', ''],
        ['3', 'ぐるなび', '__________', '__________', '__________', ''],
        ['4', 'Hot Pepper', '__________', '__________', '__________', ''],
        ['5', 'Instagram', '__________', '__________', '__________', ''],
        ['6', 'Facebook', '__________', '__________', '__________', ''],
        ['7', '自社Webサイト', '__________', '__________', '__________', ''],
        ['8', 'ドメイン・サーバー', '__________', '__________', '__________', ''],
    ]
    t = Table(online,
              colWidths=[8*mm, 34*mm, 34*mm, 28*mm, 26*mm, 24*mm])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), MINCHO, 7),
        ('FONT', (0, 0), (-1, 0), GOTHIC, 7),
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    # Notes
    story.append(Paragraph('７．取引先への通知・引継', styles['article_title']))
    notes = [
        '（１）乙は、譲渡日までに上記各取引先に対し、事業譲渡及び新たな'
        '取引主体（甲）への切替について書面または口頭で通知し、甲の'
        '紹介及び引継を行うものとする。',
        '（２）譲渡日前日までに発生した仕入代金・委託料等の未払債務は、'
        '乙の負担及び帰属とし、譲渡日までに完済するものとする。',
        '（３）譲渡日以降の新規発注・契約更新は、甲の名義及び責任において'
        '行うものとし、乙は甲の名義への切替に必要な合理的な協力をする'
        'ものとする。',
        '（４）デリバリーサービス、オンライン予約サービス等のアカウントに'
        'ついては、譲渡日に甲乙立会いの上、ログイン情報・管理者権限を'
        '甲に移管する。移管不能なアカウントがある場合、乙は速やかに'
        '解約手続を行い、甲は新規にアカウントを開設するものとする。',
    ]
    for item in notes:
        story.append(Paragraph(item, styles['body_no_indent']))

    # Confirmation
    story.append(Paragraph('８．引渡確認', styles['article_title']))
    story.append(Paragraph(
        '上記取引先一覧については、令和8年（2026年）　月　日、甲乙'
        '立会いの上、内容を確認し、関係資料の引渡を完了した。',
        styles['body']))

    story.append(Spacer(1, 10*mm))

    sig_data = [
        [Paragraph('<b>【甲】　譲受人</b>', styles['signature_label']),
         Paragraph('<b>【乙】　譲渡人</b>', styles['signature_label'])],
        [Paragraph(BUYER_NAME, styles['signature_line']),
         Paragraph(SELLER_NAME, styles['signature_line'])],
        [Paragraph(f'{BUYER_REP_TITLE}：{BUYER_REP_NAME}　印',
                   styles['signature_line']),
         Paragraph(f'代表者：{SELLER_REP_NAME}　印',
                   styles['signature_line'])],
    ]
    t = Table(sig_data, colWidths=[80*mm, 80*mm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 2), (1, 2), 0.5, LINE_COLOR),
    ]))
    story.append(t)

    add_doc_footer(story, styles, '2026-001-A3')

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
    f4 = generate_landlord_consent()
    f5 = generate_asset_inventory()
    f6 = generate_lease_consent_request()
    f7 = generate_stock_inventory()
    f8 = generate_payment_receipts_cover()
    print(f"\n=== All documents generated in {OUTPUT_DIR} ===")
    print(f"1. {f1}")
    print(f"2. {f2}")
    print(f"3. {f3}")
    print(f"4. {f4}")
    print(f"5. {f5}")
    print(f"6. {f6}")
    print(f"7. {f7}")
    print(f"8. {f8}")
    print(f"4. {f4}")
    print(f"5. {f5}")
