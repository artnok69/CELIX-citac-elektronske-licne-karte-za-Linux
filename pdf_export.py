"""
Official-style PDF Report Generator ("Čitač elektronske lične karte: štampa podataka")
matching the layout, typography, lines, and legal footnotes of Čelik v1.4.2.1.
"""

from __future__ import annotations

import datetime
import io
import os
import subprocess
from typing import Dict, Tuple

from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from eid_card import EidCardData


# ---------------------------------------------------------------------------
# Localization Strings (Cyrillic & Latin) matching Celik.exe resources
# ---------------------------------------------------------------------------

LABELS: Dict[str, Dict[str, str]] = {
    "cyr": {
        "report_title_id": "Читач електронске личне карте: штампа података",
        "report_title_if": "Читач електронске личне карте за странца: штампа података",
        "report_title_rp": "Читач дозволе за привремени боравак: штампа података",
        "citizen_section": "Подаци о грађанину",
        "foreigner_section": "Подаци о странцу",
        "surname": "Презиме:",
        "given_name": "Име:",
        "parent_name": "Име једног родитеља:",
        "nationality": "Држављанство:",
        "date_of_birth": "Датум рођења:",
        "place_of_birth": "Место рођења, општина и држава:",
        "address": "Пребивалиште и адреса стана:",
        "address_if": "Боравиште и адреса стана:",
        "address_date": "Датум промене адресе:",
        "jmbg": "ЈМБГ:",
        "ebs": "Евиденцијски број странца:",
        "sex": "Пол:",
        "status_of_foreigner": "Статус странца:",
        "purpose_of_stay": "Основ боравка:",
        "e_note": "Напомена:",
        "doc_section": "Подаци о документу",
        "doc_name": "Назив документа:",
        "issuing_authority": "Документ издаје:",
        "doc_reg_no": "Број документа:",
        "issuing_date": "Датум издавања:",
        "expiry_date": "Важи до:",
        "print_date": "Датум штампе:",
        "footnote_id": (
            "1. У чипу личне карте, подаци о имену и презимену имаоца личне карте "
            "исписани су на националном писму онако како су исписани на самом обрасцу "
            "личне карте, док су остали подаци исписани латиничким писмом.\n"
            "2. Ако се име или презиме грађанина састоји од две речи чија укупна дужина "
            "прелази 20 карактера за име, односно 30 карактера за презиме, у чип личне "
            "карте уписује се пуно име и презиме грађанина, а на самом обрасцу личне карте "
            "уписује се до 20 карактера за име, односно 30 карактера за презиме."
        ),
        "footnote_foreigner": (
            "1. У чипу личне карте за странца, подаци о имену и презимену странца "
            "исписани су онако како су исписани на самом обрасцу личне карте за странца "
            "латиничним писмом.\n"
            "2. Ако се име или презиме странца састоји од две или више речи чија дужина "
            "прелази 30 карактера за име, односно 36 карактера за презиме, у чип се "
            "уписује пуно име и презиме странца, а на обрасцу личне карте за странца се "
            "уписује до 30 карактера за име, односно 36 карактера за презиме."
        ),
    },
    "lat": {
        "report_title_id": "Čitač elektronske lične karte: štampa podataka",
        "report_title_if": "Čitač elektronske lične karte za stranca: štampa podataka",
        "report_title_rp": "Čitač dozvole za privremeni boravak: štampa podataka",
        "citizen_section": "Podaci o građaninu",
        "foreigner_section": "Podaci o strancu",
        "surname": "Prezime:",
        "given_name": "Ime:",
        "parent_name": "Ime jednog roditelja:",
        "nationality": "Državljanstvo:",
        "date_of_birth": "Datum rođenja:",
        "place_of_birth": "Mesto rođenja, opština i država:",
        "address": "Prebivalište i adresa stana:",
        "address_if": "Boravište i adresa stana:",
        "address_date": "Datum promene adrese:",
        "jmbg": "JMBG:",
        "ebs": "Evidencijski broj stranca:",
        "sex": "Pol:",
        "status_of_foreigner": "Status stranca:",
        "purpose_of_stay": "Osnov boravka:",
        "e_note": "Napomena:",
        "doc_section": "Podaci o dokumentu",
        "doc_name": "Naziv dokumenta:",
        "issuing_authority": "Dokument izdaje:",
        "doc_reg_no": "Broj dokumenta:",
        "issuing_date": "Datum izdavanja:",
        "expiry_date": "Važi do:",
        "print_date": "Datum štampe:",
        "footnote_id": (
            "1. U čipu lične карте, podaci o imenu i prezimenu imaoca lične karte "
            "ispisani su na nacionalnom pismu onako kako su ispisani na samom obrascu "
            "lične karte, dok su ostali podaci ispisani latiničkim pismom.\n"
            "2. Ako se ime ili prezime građanina sastoji od dve reči čija ukupna dužina "
            "prelazi 20 karaktera za ime, odnosno 30 karaktera za prezime, u čip lične "
            "karte upisuje se puno ime i prezime građanina, a na samom obrascu lične karte "
            "upisuje se do 20 karaktera za ime, odnosno 30 karaktera za prezime."
        ),
        "footnote_foreigner": (
            "1. U čipu lične karte za stranca, podaci o imenu i prezimenu stranca "
            "ispisani su onako kako su ispisani na samom obrascu lične karte za stranca "
            "latiničnim pismom.\n"
            "2. Ako se ime ili prezime stranca sastoji od dve ili više reči čija dužina "
            "prelazi 30 karaktera za ime, odnosno 36 karaktera za prezime, u čip se "
            "upisuje puno ime i prezime stranca, a na obrascu lične karte za stranca se "
            "upisuje do 30 karaktera za ime, odnosno 36 karaktera za prezime."
        ),
    },
}


def _find_ttf_font(family_candidates: Tuple[str, ...], bold: bool = False) -> str:
    """Locate a system TrueType font with full Serbian Cyrillic & Latin support."""
    style = "Bold" if bold else "Regular"
    for fam in family_candidates:
        try:
            pattern = f"{fam}:style={style}"
            out = subprocess.check_output(
                ["fc-match", "--format=%{file}", pattern],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            if out and os.path.isfile(out) and out.lower().endswith((".ttf", ".otf")):
                return out
        except Exception:
            continue

    # Direct path fallbacks
    fallback_paths = (
        [
            "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            os.path.expanduser("~/.local/share/fonts/DejaVuSans-Bold.ttf"),
        ]
        if bold
        else [
            "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            os.path.expanduser("~/.local/share/fonts/DejaVuSans.ttf"),
        ]
    )
    for p in fallback_paths:
        if os.path.isfile(p):
            return p
    raise RuntimeError("Nije pronađen TTF font za generisanje PDF-a (DejaVu Sans / Liberation Sans).")


_FONTS_REGISTERED = False
FONT_REGULAR = "CelikSans"
FONT_BOLD = "CelikSans-Bold"


def ensure_pdf_fonts() -> Tuple[str, str]:
    global _FONTS_REGISTERED
    if not _FONTS_REGISTERED:
        reg_path = _find_ttf_font(("Arial", "Liberation Sans", "DejaVu Sans"), bold=False)
        bold_path = _find_ttf_font(("Arial", "Liberation Sans", "DejaVu Sans"), bold=True)
        pdfmetrics.registerFont(TTFont(FONT_REGULAR, reg_path))
        pdfmetrics.registerFont(TTFont(FONT_BOLD, bold_path))
        _FONTS_REGISTERED = True
    return FONT_REGULAR, FONT_BOLD


def generate_eid_pdf(card: EidCardData, output_path: str, script: str = "cyr") -> str:
    """
    Generate an official-style A4 PDF printout ("Izvod iz elektronske lične karte")
    at `output_path` and return the path.
    """
    font_reg, font_bold = ensure_pdf_fonts()
    tr = LABELS.get(script, LABELS["cyr"])

    page_w, page_h = A4  # 595.27 x 841.89 pt
    margin_l = 54.0
    margin_r = page_w - 54.0
    content_w = margin_r - margin_l

    c = canvas.Canvas(output_path, pagesize=A4)
    c.setTitle("Čelik - Štampa podataka iz elektronske lične karte")
    c.setAuthor("Čelik Linux")

    y = page_h - 56.0

    # Top horizontal rule
    c.setLineWidth(1.0)
    c.setStrokeColorRGB(0.15, 0.15, 0.15)
    c.line(margin_l, y, margin_r, y)
    y -= 20.0

    # Report title header
    if card.is_foreigner:
        title = tr["report_title_if"]
    else:
        title = tr["report_title_id"]

    c.setFont(font_bold, 11.5)
    c.setFillColorRGB(0.05, 0.05, 0.05)
    c.drawString(margin_l + 4, y, title.upper())
    y -= 10.0

    c.setLineWidth(1.0)
    c.line(margin_l, y, margin_r, y)
    y -= 22.0

    # Portrait image on left (120 x 155 pt)
    photo_w = 118.0
    photo_h = 152.0
    photo_x = margin_l
    photo_y = y - photo_h

    if card.portrait_jpeg:
        try:
            pil_img = PILImage.open(io.BytesIO(card.portrait_jpeg))
            img_reader = ImageReader(pil_img)
            c.drawImage(
                img_reader,
                photo_x,
                photo_y,
                width=photo_w,
                height=photo_h,
                preserveAspectRatio=True,
                anchor="nw",
            )
        except Exception:
            pass

    # Subtle frame around portrait
    c.setLineWidth(0.6)
    c.setStrokeColorRGB(0.55, 0.55, 0.55)
    c.rect(photo_x, photo_y, photo_w, photo_h, stroke=1, fill=0)

    y = photo_y - 24.0

    # Helper to draw a section header with top/bottom rules
    def draw_section_header(heading: str, curr_y: float) -> float:
        c.setStrokeColorRGB(0.15, 0.15, 0.15)
        c.setLineWidth(0.9)
        c.line(margin_l, curr_y, margin_r, curr_y)
        curr_y -= 16.0
        c.setFont(font_bold, 11.0)
        c.setFillColorRGB(0.0, 0.0, 0.0)
        c.drawString(margin_l + 2, curr_y, heading)
        curr_y -= 7.0
        c.setLineWidth(0.6)
        c.line(margin_l, curr_y, margin_r, curr_y)
        curr_y -= 16.0
        return curr_y

    label_col_w = 175.0
    val_col_x = margin_l + label_col_w
    val_col_w = margin_r - val_col_x

    def draw_field_row(label: str, value: str, curr_y: float) -> float:
        c.setFont(font_reg, 10.0)
        c.setFillColorRGB(0.1, 0.1, 0.1)
        label_lines = simpleSplit(label, font_reg, 10.0, label_col_w - 10.0)
        val_lines = simpleSplit(value or "—", font_reg, 10.0, val_col_w)
        if not val_lines:
            val_lines = [""]
        n_lines = max(len(label_lines), len(val_lines))
        for i in range(n_lines):
            if i < len(label_lines):
                c.drawString(margin_l + 2, curr_y, label_lines[i])
            if i < len(val_lines):
                c.drawString(val_col_x, curr_y, val_lines[i])
            curr_y -= 14.5
        curr_y -= 2.5
        return curr_y

    # Section 1: Citizen / Foreigner Personal Data
    sec1_title = tr["foreigner_section"] if card.is_foreigner else tr["citizen_section"]
    y = draw_section_header(sec1_title, y)

    y = draw_field_row(tr["surname"], card.fixed.surname, y)
    y = draw_field_row(tr["given_name"], card.fixed.given_name, y)
    if card.is_foreigner and card.fixed.nationality_full:
        y = draw_field_row(tr["nationality"], card.fixed.nationality_full, y)
    else:
        y = draw_field_row(tr["parent_name"], card.fixed.parent_given_name, y)

    y = draw_field_row(tr["date_of_birth"], card.fixed.date_of_birth, y)
    y = draw_field_row(tr["place_of_birth"], card.full_place_of_birth, y)

    addr_lbl = tr["address_if"] if card.is_foreigner else tr["address"]
    y = draw_field_row(addr_lbl, card.full_address, y)
    y = draw_field_row(tr["address_date"], card.variable.address_date, y)

    id_lbl = tr["ebs"] if card.is_foreigner else tr["jmbg"]
    y = draw_field_row(id_lbl, card.fixed.personal_number, y)
    y = draw_field_row(tr["sex"], card.fixed.sex, y)

    if card.fixed.status_of_foreigner:
        y = draw_field_row(tr["status_of_foreigner"], card.fixed.status_of_foreigner, y)
    if card.fixed.purpose_of_stay:
        y = draw_field_row(tr["purpose_of_stay"], card.fixed.purpose_of_stay, y)
    if card.fixed.e_note:
        y = draw_field_row(tr["e_note"], card.fixed.e_note, y)

    y -= 6.0

    # Section 2: Document Data
    y = draw_section_header(tr["doc_section"], y)
    if card.is_foreigner and card.document.document_name:
        y = draw_field_row(tr["doc_name"], card.document.document_name, y)
    y = draw_field_row(tr["issuing_authority"], card.document.issuing_authority, y)
    y = draw_field_row(tr["doc_reg_no"], card.document.doc_reg_no, y)
    y = draw_field_row(tr["issuing_date"], card.document.issuing_date, y)
    y = draw_field_row(tr["expiry_date"], card.document.expiry_date, y)

    y -= 4.0
    c.setLineWidth(0.9)
    c.line(margin_l, y, margin_r, y)
    y -= 18.0

    # Print Date
    today_str = datetime.date.today().strftime("%d.%m.%Y.")
    y = draw_field_row(tr["print_date"], today_str, y)
    y -= 6.0

    c.setLineWidth(0.9)
    c.line(margin_l, y, margin_r, y)
    y -= 16.0

    # Footnotes at bottom (matching official Čelik printout)
    footnote_text = tr["footnote_foreigner"] if card.is_foreigner else tr["footnote_id"]
    c.setFont(font_reg, 8.2)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    for paragraph in footnote_text.split("\n"):
        lines = simpleSplit(paragraph, font_reg, 8.2, content_w)
        for ln in lines:
            c.drawString(margin_l, y, ln)
            y -= 11.5
        y -= 3.0

    y -= 4.0
    c.setLineWidth(0.9)
    c.line(margin_l, y, margin_r, y)

    c.showPage()
    c.save()
    return output_path
