import json
from pathlib import Path
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Add project root to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from anchor.config import settings


def get_gazette_styles():
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "GazetteTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=1,  # Centered
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    sub_title_style = ParagraphStyle(
        "GazetteSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        alignment=1,  # Centered
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=3,
    )

    meta_style = ParagraphStyle(
        "GazetteMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        alignment=1,  # Centered
        textColor=colors.HexColor("#475569"),
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "GazetteBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        alignment=4,  # Justified
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
    )

    heading_style = ParagraphStyle(
        "GazetteHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=6,
        spaceAfter=3,
    )

    table_header_style = ParagraphStyle(
        "GazetteTableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        alignment=1,  # Centered
        textColor=colors.white,
    )

    table_cell_style = ParagraphStyle(
        "GazetteTableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0f172a"),
    )

    table_cell_bold = ParagraphStyle(
        "GazetteTableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0f172a"),
    )

    table_cell_center = ParagraphStyle(
        "GazetteTableCellCenter",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        alignment=1,
        textColor=colors.HexColor("#0f172a"),
    )

    return {
        "title": title_style,
        "subtitle": sub_title_style,
        "meta": meta_style,
        "body": body_style,
        "heading": heading_style,
        "th": table_header_style,
        "td": table_cell_style,
        "td_bold": table_cell_bold,
        "td_center": table_cell_center,
    }


def generate_dfpds_pdf(schedule_data: dict, output_path: Path):
    styles = get_gazette_styles()
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    story = []

    # Gazette Masthead
    story.append(Paragraph("THE GAZETTE OF INDIA : EXTRAORDINARY", styles["title"]))
    story.append(Paragraph("PART II — SECTION 3 — SUB-SECTION (ii)", styles["subtitle"]))
    story.append(Paragraph("PUBLISHED BY AUTHORITY OF THE GOVERNMENT OF INDIA", styles["meta"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=6))

    # Ministry Meta
    notif = schedule_data.get("gazette_notification", "S.O. 2026/NAVY/STATUTORY(E)")
    eff_date = schedule_data.get("effective_date", "01 January 2026")
    story.append(Paragraph("MINISTRY OF DEFENCE &bull; DEPARTMENT OF MILITARY AFFAIRS", styles["subtitle"]))
    story.append(Paragraph(f"NOTIFICATION &bull; {notif} &bull; New Delhi, the {eff_date}", styles["meta"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94a3b8"), spaceAfter=8))

    # Schedule Title
    sch_name = schedule_data.get("schedule_name", "Schedule")
    ref_code = schedule_data.get("reference", "DFPDS-2026/NAVY")
    story.append(Paragraph(f"DELEGATION OF FINANCIAL POWERS TO DEFENCE SERVICES (DFPDS-2026)", styles["subtitle"]))
    story.append(Paragraph(f"<b>{sch_name.upper()}</b>", styles["heading"]))
    story.append(Paragraph(f"Statutory Reference Code: <b>{ref_code}</b>", styles["meta"]))
    story.append(Spacer(1, 4))

    # Table of Delegation
    table_data = [
        [
            Paragraph("<b>Tier</b>", styles["th"]),
            Paragraph("<b>Competent Financial Authority (CFA)</b>", styles["th"]),
            Paragraph("<b>With IFA Concurrence (₹ Cr)</b>", styles["th"]),
            Paragraph("<b>Without IFA Concurrence (₹ Cr)</b>", styles["th"]),
            Paragraph("<b>PAC Limit (₹ Cr)</b>", styles["th"]),
            Paragraph("<b>Statutory Delegation Notes</b>", styles["th"]),
        ]
    ]

    for t in schedule_data.get("tiers", []):
        tier_label = t.get("tier", "")
        tier_name = t.get("tier_name", "")
        with_ifa = f"₹ {t.get('with_ifa', 0.0):.2f} Cr"
        without_ifa = f"₹ {t.get('without_ifa', 0.0):.2f} Cr"
        pac_val = f"₹ {t.get('pac_limit', 0.0):.2f} Cr"
        notes = t.get("notes", "")

        table_data.append(
            [
                Paragraph(f"<b>{tier_label}</b>", styles["td_bold"]),
                Paragraph(f"<b>{tier_name}</b>", styles["td_bold"]),
                Paragraph(with_ifa, styles["td_center"]),
                Paragraph(without_ifa, styles["td_center"]),
                Paragraph(pac_val, styles["td_center"]),
                Paragraph(notes, styles["td"]),
            ]
        )

    # A4 printable width: 210mm - 30mm margins = 180mm = ~510pt
    col_widths = [45, 115, 65, 65, 55, 165]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 8))

    # Statutory Clauses
    story.append(Paragraph("<b>STATUTORY PROVISIONS & STATUTORY CLAUSES:</b>", styles["heading"]))
    for clause in schedule_data.get("clauses", []):
        story.append(Paragraph(f"&bull; {clause}", styles["body"]))

    doc.build(story)


def generate_dpm_pdf(chapter_data: dict, output_path: Path):
    styles = get_gazette_styles()
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    story = []

    # Header
    story.append(Paragraph("GOVERNMENT OF INDIA &bull; MINISTRY OF DEFENCE", styles["title"]))
    story.append(Paragraph("DEFENCE PROCUREMENT MANUAL 2025 (DPM-2025)", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=6))

    # Chapter Details
    ch_title = chapter_data.get("chapter_title", "Chapter")
    ref_code = chapter_data.get("reference", "DPM-2025/DMA")
    story.append(Paragraph(f"<b>{ch_title.upper()}</b>", styles["heading"]))
    story.append(Paragraph(f"Reference Identifier: <b>{ref_code}</b>", styles["meta"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94a3b8"), spaceAfter=8))

    # Topics
    topics = chapter_data.get("topics", [])
    if topics:
        topics_str = " &bull; ".join(topics)
        story.append(Paragraph(f"<b>Core Subject Domains:</b> {topics_str}", styles["meta"]))
        story.append(Spacer(1, 6))

    # Clauses
    story.append(Paragraph("<b>MANDATORY PROCUREMENT DIRECTIVES & PROCEDURES:</b>", styles["heading"]))
    for clause in chapter_data.get("clauses", []):
        story.append(Paragraph(f"&bull; {clause}", styles["body"]))

    doc.build(story)


def generate_navy_regs_pdf(part_data: dict, output_path: Path):
    styles = get_gazette_styles()
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    story = []

    # Header
    story.append(Paragraph("STATUTORY REGULATIONS &bull; NAVY ACT 1957", styles["title"]))
    story.append(Paragraph("REGULATIONS FOR THE NAVY (NAVREGS)", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=6))

    # Part Details
    part_title = part_data.get("part_title", "Navy Regulations")
    ref_code = part_data.get("reference", "NAVREGS/STATUTORY")
    story.append(Paragraph(f"<b>{part_title.upper()}</b>", styles["heading"]))
    story.append(Paragraph(f"Statutory Reference: <b>{ref_code}</b>", styles["meta"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94a3b8"), spaceAfter=8))

    # Articles
    story.append(Paragraph("<b>STATUTORY ARTICLES & COMMAND PREROGATIVES:</b>", styles["heading"]))
    for art in part_data.get("articles", []):
        art_no = art.get("article_no", "")
        title = art.get("title", "")
        text = art.get("text", "")
        story.append(Paragraph(f"<b>{art_no}: {title}</b>", styles["heading"]))
        story.append(Paragraph(text, styles["body"]))
        story.append(Spacer(1, 4))

    doc.build(story)


def generate_all_regulatory_pdfs():
    settings.ensure_directories()
    schemas_dir = settings.SCHEMAS_DIR
    pdfs_dir = settings.PDFS_DIR

    print(f"[ANCHOR] Generating regulatory PDFs into: {pdfs_dir}")

    # 1. Generate DFPDS-2026 (32 Schedules)
    dfpds_file = schemas_dir / "dfpds_2026.json"
    if dfpds_file.exists():
        with open(dfpds_file, "r", encoding="utf-8") as f:
            dfpds_data = json.load(f)
        for item in dfpds_data:
            sch_no = item.get("schedule_no", 1)
            out_file = pdfs_dir / f"DFPDS_2026_Schedule_{sch_no:02d}.pdf"
            generate_dfpds_pdf(item, out_file)
        print(f"[OK] Generated {len(dfpds_data)} DFPDS-2026 Schedule PDFs")
    else:
        print(f"[WARN] Schema file not found: {dfpds_file}")

    # 2. Generate DPM-2025 (6 Chapters)
    dpm_file = schemas_dir / "dpm_2025.json"
    if dpm_file.exists():
        with open(dpm_file, "r", encoding="utf-8") as f:
            dpm_data = json.load(f)
        for item in dpm_data:
            ch_no = item.get("chapter_no", 1)
            out_file = pdfs_dir / f"DPM_2025_Chapter_{ch_no:02d}.pdf"
            generate_dpm_pdf(item, out_file)
        print(f"[OK] Generated {len(dpm_data)} DPM-2025 Chapter PDFs")
    else:
        print(f"[WARN] Schema file not found: {dpm_file}")

    # 3. Generate Navy Regulations (4 Parts)
    navy_file = schemas_dir / "navy_regs.json"
    roman_map = {1: "I", 2: "II", 3: "III", 4: "IV"}
    if navy_file.exists():
        with open(navy_file, "r", encoding="utf-8") as f:
            navy_data = json.load(f)
        for item in navy_data:
            part_no = item.get("part_no", 1)
            roman = roman_map.get(part_no, f"{part_no}")
            
            # Write canonical Roman numeral and numeric filenames
            out_file_roman = pdfs_dir / f"Navy_Regs_Part_{roman}.pdf"
            out_file_num = pdfs_dir / f"NAVY_REGS_Part_{part_no:02d}.pdf"
            
            generate_navy_regs_pdf(item, out_file_roman)
            generate_navy_regs_pdf(item, out_file_num)
        print(f"[OK] Generated {len(navy_data)} Navy Regulations Part PDFs")
    else:
        print(f"[WARN] Schema file not found: {navy_file}")

    total_generated = len(list(pdfs_dir.glob("*.pdf")))
    print(f"[SUCCESS] Regulatory PDF Generation Complete! Total PDF files in corpus: {total_generated}")


if __name__ == "__main__":
    generate_all_regulatory_pdfs()
