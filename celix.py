#!/usr/bin/env python3
"""
Čelik Linux — Čitač elektronske lične karte (PyQt5 Desktop GUI)

Native Linux desktop application replicating and modernizing the official
Serbian eID reader (Čelik v1.4.2.1), supporting:
- Automatic smart card detection via PC/SC (libpcsclite)
- Serbian Cyrillic (Ћирилица) and Latin (Latinica) UI & printouts
- Official-style A4 PDF export ("Izvod iz elektronske lične karte") & direct printing
- X.509 Certificate viewer & DER/PEM export (Auth & Digital Signature certificates)
- PIN verification & PIN change dialog
- Demo / Simulation mode when no hardware reader is attached
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLayout,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from eid_card import (
    CertificateInfo,
    EidCardData,
    PCSCLite,
    PCSCError,
    SCARD_STATE_PRESENT,
    SerbianEidReader,
    create_demo_card_data,
)
from pdf_export import generate_eid_pdf


if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
    BUNDLE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

ASSETS_DIR = (
    os.path.join(BUNDLE_DIR, "assets")
    if os.path.isdir(os.path.join(BUNDLE_DIR, "assets"))
    else os.path.join(BASE_DIR, "assets")
)


# ---------------------------------------------------------------------------
# UI Translations (Srpski ćirilica & Srpski latinica)
# ---------------------------------------------------------------------------

UI_STRINGS: Dict[str, Dict[str, str]] = {
    "lat": {
        "window_title": "Čitač elektronske lične karte - Čelix",
        "header_state": "Република Србија   •   Republika Srbija   •   Republic of Serbia",
        "header_doc_id": "ЛИЧНА КАРТА   •   LIČNA KARTA   •   IDENTITY CARD",
        "header_doc_if": "ЛИЧНА КАРТА ЗА СТРАНЦА   •   IDENTITY CARD FOR FOREIGNER",
        "menu_doc": "&Lični dokument",
        "act_read_now": "&Očitaj karticu ponovo\tF5",
        "act_demo": "&Učitaj demo karticu (simulacija)\tCtrl+D",
        "act_change_pin": "&Promeni PIN...\tCtrl+K",
        "act_verify_pin": "Pro&veri PIN...",
        "act_export_pdf": "Sačuvaj &PDF izvod...\tCtrl+S",
        "act_print": "&Štampaj podatke...\tCtrl+P",
        "act_exit": "&Izlaz\tCtrl+Q",
        "menu_options": "&Opcije",
        "menu_script": "&Promeni pismo",
        "act_cyr": "Српски (ћирилица)",
        "act_lat": "Srpski (latinica)",
        "menu_reader": "Izbor &čitača",
        "any_reader": "Bilo koji čitač",
        "act_verify_format": "Proveri &format kartice",
        "act_verify_blocks": "Proveri potpis &blokova podataka",
        "menu_certs": "Prikaz &sertifikata",
        "act_cert_auth": "Sertifikat za &autentifikaciju i šifrovanje...",
        "act_cert_sign": "Sertifikat za &elektronski potpis...",
        "menu_help": "&Pomoć",
        "act_manual": "&Uputstvo za upotrebu\tF1",
        "act_about": "&O aplikaciji Čitač elektronske lične karte",
        "group_citizen": "Podaci o građaninu",
        "group_foreigner": "Podaci o strancu",
        "lbl_surname": "Prezime:",
        "lbl_given_name": "Ime:",
        "lbl_parent_name": "Ime jednog roditelja:",
        "lbl_nationality": "Državljanstvo:",
        "lbl_dob": "Datum rođenja:",
        "lbl_pob": "Mesto rođenja, opština i država:",
        "lbl_address": "Prebivalište i adresa stana:",
        "lbl_address_if": "Boravište i adresa stana:",
        "lbl_address_date": "Datum promene adrese:",
        "lbl_jmbg": "JMBG:",
        "lbl_ebs": "EBS:",
        "lbl_sex": "Pol:",
        "lbl_purpose": "Osnov boravka:",
        "lbl_enote": "Napomena:",
        "group_doc": "Podaci o dokumentu",
        "lbl_issuer": "Dokument izdaje:",
        "lbl_doc_no": "Broj dokumenta:",
        "lbl_issue_date": "Datum izdavanja:",
        "lbl_expiry_date": "Važi do:",
        "lbl_sig_status": "Digitalni potpisi blokova:",
        "status_verified": "VERIFIKOVAN",
        "status_not_verified": "NIJE VERIFIKOVAN",
        "status_reading": "ČITANJE JE U TOKU...",
        "status_no_card": "Elektronski lični dokument nije priključen na čitač smart kartica.",
        "status_no_reader": "Nije detektovan nijedan PC/SC čitač kartica. Možete koristiti Demo režim (Ctrl+D).",
        "status_card_ready": "Kartica uspešno očitana sa čitača: {reader}",
        "status_demo_ready": "Prikazani su demonstracioni podaci (simulacija elektronske lične karte).",
        "btn_print": "Štampa podataka",
        "btn_save_pdf": "Sačuvaj PDF izvod",
        "btn_certs": "Sertifikati",
        "btn_change_pin": "Promena PIN-a",
        "btn_demo": "Demo kartica",
        "tip_sig_card": "Struktura kartice: blok je verifikovan",
        "tip_sig_fixed": "Fiksni podaci: blok je verifikovan",
        "tip_sig_var": "Promenljivi podaci: blok je verifikovan",
        "no_photo": "Fotografija\nnije učitana",
    },
    "cyr": {
        "window_title": "Читач електронске личне карте - ЧЕЛИКС",
        "header_state": "Република Србија   •   Republika Srbija   •   Republic of Serbia",
        "header_doc_id": "ЛИЧНА КАРТА   •   LIČNA KARTA   •   IDENTITY CARD",
        "header_doc_if": "ЛИЧНА КАРТА ЗА СТРАНЦА   •   IDENTITY CARD FOR FOREIGNER",
        "menu_doc": "&Лични документ",
        "act_read_now": "&Очитај картицу поново\tF5",
        "act_demo": "&Учитај демо картицу (симулација)\tCtrl+D",
        "act_change_pin": "&Промени ПИН...\tCtrl+K",
        "act_verify_pin": "Про&вери ПИН...",
        "act_export_pdf": "Сачувај &ПДФ извод...\tCtrl+S",
        "act_print": "&Штампај податке...\tCtrl+P",
        "act_exit": "&Излаз\tCtrl+Q",
        "menu_options": "&Опције",
        "menu_script": "&Промени писмо",
        "act_cyr": "Српски (ћирилица)",
        "act_lat": "Srpski (latinica)",
        "menu_reader": "Избор &читача",
        "any_reader": "Било који читач",
        "act_verify_format": "Провери &формат картице",
        "act_verify_blocks": "Провери потпис &блокова података",
        "menu_certs": "Приказ &сертификата",
        "act_cert_auth": "Сертификат за &аутентификацију и шифровање...",
        "act_cert_sign": "Сертификат за &електронски потпис...",
        "menu_help": "&Помоћ",
        "act_manual": "&Упутство за употребу\tF1",
        "act_about": "&О апликацији Читач електронске личне карте",
        "group_citizen": "Подаци о грађанину",
        "group_foreigner": "Подаци о странцу",
        "lbl_surname": "Презиме:",
        "lbl_given_name": "Име:",
        "lbl_parent_name": "Име једног родитеља:",
        "lbl_nationality": "Држављанство:",
        "lbl_dob": "Датум рођења:",
        "lbl_pob": "Место рођења, општина и држава:",
        "lbl_address": "Пребивалиште и адреса стана:",
        "lbl_address_if": "Боравиште и адреса стана:",
        "lbl_address_date": "Датум промене адресе:",
        "lbl_jmbg": "ЈМБГ:",
        "lbl_ebs": "ЕБС:",
        "lbl_sex": "Пол:",
        "lbl_purpose": "Основ боравка:",
        "lbl_enote": "Напомена:",
        "group_doc": "Подаци о документу",
        "lbl_issuer": "Документ издаје:",
        "lbl_doc_no": "Број документа:",
        "lbl_issue_date": "Датум издавања:",
        "lbl_expiry_date": "Важи до:",
        "lbl_sig_status": "Дигитални потписи блокова:",
        "status_verified": "ВЕРИФИКОВАН",
        "status_not_verified": "НИЈЕ ВЕРИФИКОВАН",
        "status_reading": "ЧИТАЊЕ ЈЕ У ТОКУ...",
        "status_no_card": "Електронски лични документ није прикључен на читач смарт картица.",
        "status_no_reader": "Није детектован ниједан PC/SC читач картица. Можете користити Демо режим (Ctrl+D).",
        "status_card_ready": "Картица успешно очитана са читача: {reader}",
        "status_demo_ready": "Приказани су демонстрациони подаци (симулација електронске личне карте).",
        "btn_print": "Штампа података",
        "btn_save_pdf": "Сачувај ПДФ извод",
        "btn_certs": "Сертификати",
        "btn_change_pin": "Промена ПИН-а",
        "btn_demo": "Демо картица",
        "tip_sig_card": "Структура картице: блок је верификован",
        "tip_sig_fixed": "Фиксни подаци: блок је верификован",
        "tip_sig_var": "Променљиви подаци: блок је верификован",
        "no_photo": "Фотографија\nније учитана",
    },
}


# ---------------------------------------------------------------------------
# Background Smart Card Monitor Thread
# ---------------------------------------------------------------------------

class CardMonitorThread(QThread):
    readers_changed = pyqtSignal(list)
    card_inserted = pyqtSignal(str, bytes)
    card_removed = pyqtSignal(str)
    card_read_success = pyqtSignal(object)
    card_read_error = pyqtSignal(str)
    reading_started = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._running = True
        self._selected_reader: Optional[str] = None
        self._force_reread = False

    def set_selected_reader(self, reader_name: Optional[str]) -> None:
        self._selected_reader = reader_name
        self._force_reread = True

    def request_reread(self) -> None:
        self._force_reread = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        try:
            pcsc = PCSCLite()
        except PCSCError:
            return

        hcontext: Optional[int] = None
        last_readers: List[str] = []
        active_card_state: Dict[str, bytes] = {}

        while self._running:
            try:
                if hcontext is None:
                    hcontext = pcsc.establish_context()

                readers = pcsc.list_readers(hcontext)
                if readers != last_readers:
                    last_readers = readers
                    self.readers_changed.emit(readers)
                    active_card_state.clear()

                if not readers:
                    self.msleep(800)
                    continue

                watch_list = (
                    [self._selected_reader]
                    if self._selected_reader and self._selected_reader in readers
                    else readers
                )
                states = pcsc.get_reader_states(hcontext, watch_list, timeout_ms=250)

                if self._force_reread:
                    self._force_reread = False
                    active_card_state.clear()

                for rname, event_state, atr in states:
                    is_present = bool(event_state & SCARD_STATE_PRESENT)
                    was_present = rname in active_card_state

                    if is_present and (not was_present or active_card_state[rname] != atr):
                        active_card_state[rname] = atr
                        self.card_inserted.emit(rname, atr)
                        self.reading_started.emit(rname)
                        try:
                            with SerbianEidReader(pcsc, hcontext, rname) as eid_reader:
                                card_data = eid_reader.read_all(atr=atr)
                            self.card_read_success.emit(card_data)
                        except Exception as exc:
                            self.card_read_error.emit(str(exc))

                    elif not is_present and was_present:
                        del active_card_state[rname]
                        self.card_removed.emit(rname)

            except PCSCError:
                if hcontext is not None:
                    try:
                        pcsc.release_context(hcontext)
                    except Exception:
                        pass
                    hcontext = None
                self.msleep(1000)
                continue

            self.msleep(400)

        if hcontext is not None:
            try:
                pcsc.release_context(hcontext)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Dialogs: Certificate Viewer, PIN Change/Verify, Help Manual, About
# ---------------------------------------------------------------------------

class CertificateDialog(QDialog):
    """Three-tab X.509 certificate inspector matching Windows CryptUIDlgViewCertificateW."""

    def __init__(self, certs: List[CertificateInfo], initial_type: str = "auth", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.certs = certs
        self.setWindowTitle("Prikaz sertifikata")
        self.resize(640, 520)

        layout = QVBoxLayout(self)

        # Certificate selector if multiple certificates are present
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("<b>Odaberite sertifikat sa kartice:</b>"))
        self.cert_buttons: List[QPushButton] = []
        self.current_cert: Optional[CertificateInfo] = None

        for cert in certs:
            btn = QPushButton(cert.name)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, c=cert: self.select_certificate(c))
            top_bar.addWidget(btn)
            self.cert_buttons.append(btn)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Osnovni podaci (General)
        self.general_widget = QWidget()
        gen_layout = QVBoxLayout(self.general_widget)
        self.general_summary = QTextBrowser()
        self.general_summary.setOpenExternalLinks(False)
        gen_layout.addWidget(self.general_summary)
        self.tabs.addTab(self.general_widget, "Osnovni podaci (General)")

        # Tab 2: Detaljni podaci (Details)
        self.details_table = QTableWidget(0, 2)
        self.details_table.setHorizontalHeaderLabels(["Polje (Field)", "Vrednost (Value)"])
        self.details_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.details_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.details_table.verticalHeader().setVisible(False)
        self.details_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.details_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabs.addTab(self.details_table, "Detaljni podaci (Details)")

        # Tab 3: Sertifikacioni lanac (Certification Path)
        self.chain_browser = QTextBrowser()
        self.tabs.addTab(self.chain_browser, "Putanja sertifikata (Certification Path)")

        # Bottom buttons: Export DER/PEM + Close
        btn_row = QHBoxLayout()
        self.export_btn = QPushButton("Izvezi sertifikat (.cer / .pem)...")
        self.export_btn.clicked.connect(self.export_certificate)
        btn_row.addWidget(self.export_btn)
        btn_row.addStretch()

        close_btn = QPushButton("U redu")
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        # Select matching initial certificate
        target = next((c for c in certs if c.cert_type == initial_type), certs[0] if certs else None)
        if target:
            self.select_certificate(target)

    def select_certificate(self, cert: CertificateInfo) -> None:
        self.current_cert = cert
        for btn, c in zip(self.cert_buttons, self.certs):
            btn.setChecked(c is cert)

        status_color = "#1b7e3c" if cert.is_valid_now else "#c92a2a"
        status_text = (
            "Sertifikat je važeći u trenutnom vremenskom periodu."
            if cert.is_valid_now
            else "Sertifikat je istekao ili još nije počeo da važi."
        )
        ku_html = "".join(f"<li>{u}</li>" for u in (cert.key_usage or ["Standardna upotreba"]))

        self.general_summary.setHtml(
            f"""
            <div style="font-family: sans-serif; padding: 6px;">
              <h3 style="margin-top:0; color:#1c3d6e;">{cert.name}</h3>
              <p style="color:{status_color}; font-weight:bold;">✔ {status_text}</p>
              <hr/>
              <p><b>Namena sertifikata:</b></p>
              <ul>{ku_html}</ul>
              <hr/>
              <table cellspacing="6" cellpadding="2">
                <tr><td><b>Izdat za (Subject):</b></td><td>{cert.subject_cn}</td></tr>
                <tr><td><b>Izdao (Issuer):</b></td><td>{cert.issuer_cn}</td></tr>
                <tr><td><b>Važi od:</b></td><td>{cert.not_before}</td></tr>
                <tr><td><b>Važi do:</b></td><td>{cert.not_after}</td></tr>
                <tr><td><b>Javni ključ:</b></td><td>{cert.public_key_info}</td></tr>
                <tr><td><b>Serijski broj:</b></td><td><code>{cert.serial_number}</code></td></tr>
              </table>
            </div>
            """
        )

        rows = [
            ("Naziv sertifikata", cert.name),
            ("Serijski broj (Serial Number)", cert.serial_number),
            ("Algoritam potpisa", cert.signature_algorithm),
            ("Izdavač (Issuer DN)", cert.issuer_dn),
            ("Korisnik (Subject DN)", cert.subject_dn),
            ("Važi od (Not Before)", cert.not_before),
            ("Važi do (Not After)", cert.not_after),
            ("Javni ključ (Public Key)", cert.public_key_info),
            ("Upotreba ključa (Key Usage)", ", ".join(cert.key_usage)),
            ("Proširena upotreba (EKU)", ", ".join(cert.extended_key_usage)),
            ("SHA-256 otisak (Fingerprint)", cert.sha256_fingerprint),
            ("SHA-1 otisak (Thumbprint)", cert.sha1_fingerprint),
        ]
        for k, v in cert.extensions_summary.items():
            rows.append((f"Ekstenzija: {k}", v))

        self.details_table.setRowCount(len(rows))
        for i, (field_name, val) in enumerate(rows):
            k_item = QTableWidgetItem(field_name)
            v_item = QTableWidgetItem(val)
            self.details_table.setItem(i, 0, k_item)
            self.details_table.setItem(i, 1, v_item)

        self.chain_browser.setHtml(
            f"""
            <div style="font-family: sans-serif; padding: 10px;">
              <h4 style="color:#1c3d6e;">Sertifikacioni lanac poverenja (MUP RS CA)</h4>
              <ul style="line-height: 1.8;">
                <li>🏛 <b>MUP RS Root CA</b> (Sertifikaciono telo MUP-a Republike Srbije)
                  <ul>
                    <li>🏢 <b>{cert.issuer_cn}</b> (Intermedijarni CA sertifikat)
                      <ul>
                        <li>🪪 <b>{cert.subject_cn}</b> ({cert.name})</li>
                      </ul>
                    </li>
                  </ul>
                </li>
              </ul>
              <hr/>
              <p><b>Status sertifikata:</b> <span style="color:{status_color};">{status_text}</span></p>
            </div>
            """
        )

    def export_certificate(self) -> None:
        if not self.current_cert:
            return
        default_name = f"{self.current_cert.cert_type}_certificate.cer"
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Sačuvaj sertifikat",
            default_name,
            "DER kodirani X.509 (*.cer *.der);;PEM kodirani X.509 (*.pem)",
        )
        if not path:
            return
        try:
            if path.lower().endswith(".pem") or "PEM" in selected_filter:
                import base64
                b64 = base64.encodebytes(self.current_cert.der_bytes).decode("ascii")
                pem_data = f"-----BEGIN CERTIFICATE-----\n{b64}-----END CERTIFICATE-----\n"
                with open(path, "w", encoding="ascii") as f:
                    f.write(pem_data)
            else:
                with open(path, "wb") as f:
                    f.write(self.current_cert.der_bytes)
            QMessageBox.information(self, "Izvoz sertifikata", f"Sertifikat je uspešno sačuvan u:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Greška", f"Greška pri čuvanju sertifikata:\n{exc}")


class PinDialog(QDialog):
    """Dialog for changing or verifying the card PIN (matching Celik.exe Dialog 139/140)."""

    def __init__(
        self,
        reader_name: str,
        is_demo: bool = False,
        verify_only: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.reader_name = reader_name
        self.is_demo = is_demo
        self.verify_only = verify_only

        self.setWindowTitle("Provera PIN-a" if verify_only else "Promena PIN-a")
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint, True)
        self.setSizeGripEnabled(False)
        self.setStyleSheet(
            "QDialog { background-color: #f8fafc; color: #111827; } "
            "QLabel { color: #111827; background: transparent; font-size: 13px; } "
            "QCheckBox { color: #111827; font-size: 13px; spacing: 8px; } "
            "QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #64748b; "
            "border-radius: 3px; background-color: #ffffff; } "
            "QCheckBox::indicator:checked { background-color: #1e4273; border-color: #1e4273; } "
            "QLineEdit { background-color: #ffffff; color: #111827; border: 1px solid #94a3b8; "
            "border-radius: 4px; padding: 4px 8px; font-size: 14px; font-weight: 600; } "
            "QLineEdit:focus { border: 1px solid #1e4273; } "
            "QPushButton { background-color: #e2e8f0; color: #1e293b; border: 1px solid #cbd5e1; "
            "border-radius: 4px; padding: 6px 16px; font-weight: 600; font-size: 13px; } "
            "QPushButton:hover { background-color: #cbd5e1; } "
            "QPushButton:default { background-color: #1e4273; color: #ffffff; border: 1px solid #1e4273; } "
            "QPushButton:default:hover { background-color: #295794; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        info_text = (
            "Ovde možete proveriti ispravnost postojećeg PIN-a i broj preostalih pokušaja na kartici."
            if verify_only
            else "Ovde možete promeniti PIN. Ne otkrivajte ni postojeći ni novi PIN drugim licima. "
                 "Izbegavajte promenu PIN-a na nepoznatim računarima.\n\n"
                 "PIN može imati najmanje 4, a najviše 8 znakova (ISO-8859-1)."
        )
        info_lbl = QLabel(info_text)
        info_lbl.setWordWrap(True)
        info_lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        info_lbl.setFixedSize(480, 52 if verify_only else 108)
        info_lbl.setStyleSheet("color: #1e293b;")
        layout.addWidget(info_lbl)

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        lbl_old = QLabel("Postojeći (stari) PIN:" if not verify_only else "Unesite PIN:")
        lbl_old.setMinimumWidth(175)
        self.old_pin_edit = QLineEdit()
        self.old_pin_edit.setEchoMode(QLineEdit.Password)
        self.old_pin_edit.setMaxLength(8)
        self.old_pin_edit.setMinimumHeight(34)
        form.addRow(lbl_old, self.old_pin_edit)

        self.new_pin_edit = QLineEdit()
        self.new_pin_edit.setEchoMode(QLineEdit.Password)
        self.new_pin_edit.setMaxLength(8)
        self.new_pin_edit.setMinimumHeight(34)

        self.confirm_pin_edit = QLineEdit()
        self.confirm_pin_edit.setEchoMode(QLineEdit.Password)
        self.confirm_pin_edit.setMaxLength(8)
        self.confirm_pin_edit.setMinimumHeight(34)

        if not verify_only:
            lbl_new = QLabel("Novi PIN:")
            lbl_new.setMinimumWidth(175)
            lbl_conf = QLabel("Ponovljen novi PIN:")
            lbl_conf.setMinimumWidth(175)
            form.addRow(lbl_new, self.new_pin_edit)
            form.addRow(lbl_conf, self.confirm_pin_edit)

        layout.addLayout(form)

        self.show_pin_cb = QCheckBox("Prikaži unete znakove PIN-a")
        self.show_pin_cb.toggled.connect(self._toggle_pin_visibility)
        layout.addWidget(self.show_pin_cb)

        self.tries_label = QLabel("")
        self.tries_label.setWordWrap(True)
        self.tries_label.setFixedWidth(480)
        self.tries_label.setMinimumHeight(28)
        self.tries_label.setStyleSheet("color: #1e4273; font-weight: bold; margin-top: 2px;")
        layout.addWidget(self.tries_label)

        btn_box = QDialogButtonBox()
        ok_btn = btn_box.addButton("Potvrdi", QDialogButtonBox.AcceptRole)
        cancel_btn = btn_box.addButton("Odustani", QDialogButtonBox.RejectRole)
        ok_btn.setDefault(True)
        ok_btn.setMinimumSize(115, 36)
        cancel_btn.setMinimumSize(115, 36)
        ok_btn.clicked.connect(self.on_submit)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(btn_box)

        self._query_tries()

        # Lock both width and height to exact layout size so window cannot be resized
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    def _toggle_pin_visibility(self, checked: bool) -> None:
        mode = QLineEdit.Normal if checked else QLineEdit.Password
        self.old_pin_edit.setEchoMode(mode)
        self.new_pin_edit.setEchoMode(mode)
        self.confirm_pin_edit.setEchoMode(mode)

    def _query_tries(self) -> None:
        if self.is_demo:
            self.tries_label.setText("Demo režim: Broj preostalih pokušaja: 3.")
            return
        if not self.reader_name:
            return
        try:
            pcsc = PCSCLite()
            hctx = pcsc.establish_context()
            try:
                with SerbianEidReader(pcsc, hctx, self.reader_name) as reader:
                    tries = reader.get_pin_tries_remaining()
                    if tries is not None:
                        self.tries_label.setText(f"Broj preostalih pokušaja na kartici: {tries}")
            finally:
                pcsc.release_context(hctx)
        except Exception:
            pass

    def on_submit(self) -> None:
        old_pin = self.old_pin_edit.text()
        if not (4 <= len(old_pin) <= 8):
            QMessageBox.warning(self, "Upozorenje", "PIN mora imati između 4 i 8 znakova.")
            return
        try:
            old_pin.encode("latin-1")
        except UnicodeEncodeError:
            QMessageBox.warning(self, "Upozorenje", "PIN sme sadržati samo standardne ISO-8859-1 znakove.")
            return

        if not self.verify_only:
            new_pin = self.new_pin_edit.text()
            conf_pin = self.confirm_pin_edit.text()
            if not (4 <= len(new_pin) <= 8):
                QMessageBox.warning(self, "Upozorenje", "Novi PIN mora imati između 4 i 8 znakova.")
                return
            if new_pin != conf_pin:
                QMessageBox.warning(self, "Upozorenje", "Novi PIN i ponovljeni novi PIN se ne poklapaju.")
                return
            try:
                new_pin.encode("latin-1")
            except UnicodeEncodeError:
                QMessageBox.warning(self, "Upozorenje", "Novi PIN sme sadržati samo ISO-8859-1 znakove.")
                return

        if self.is_demo:
            msg = "PIN je ispravan (Demo režim)." if self.verify_only else "PIN je uspešno promenjen (Demo režim)."
            QMessageBox.information(self, "Uspeh", msg)
            self.accept()
            return

        try:
            pcsc = PCSCLite()
            hctx = pcsc.establish_context()
            try:
                with SerbianEidReader(pcsc, hctx, self.reader_name) as reader:
                    if self.verify_only:
                        ok, tries, msg = reader.verify_pin(old_pin)
                    else:
                        ok, tries, msg = reader.change_pin(old_pin, self.new_pin_edit.text())
            finally:
                pcsc.release_context(hctx)

            if tries is not None:
                self.tries_label.setText(f"Broj preostalih pokušaja: {tries}")
            if ok:
                QMessageBox.information(self, "Uspeh", msg)
                self.accept()
            else:
                QMessageBox.critical(self, "Greška", msg)
        except Exception as exc:
            QMessageBox.critical(self, "Greška", f"Greška pri komunikaciji sa karticom:\n{exc}")


class HelpManualDialog(QDialog):
    """Built-in viewer for the extracted CelikHelp.chm user manual."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Čelik — Uputstvo za upotrebu")
        self.resize(760, 560)

        layout = QHBoxLayout(self)

        # Left topic list + Right HTML browser
        topics_box = QVBoxLayout()
        topics_box.addWidget(QLabel("<b>Sadržaj uputstva:</b>"))

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)

        pages = [
            ("Uvod u aplikaciju", "introduction.html"),
            ("Čitanje podataka", "read_data.html"),
            ("Štampa podataka", "print_data.html"),
            ("Prikaz sertifikata", "show_certificate.html"),
            ("Promena korisničkog PIN-a", "change_password.html"),
            ("Podešavanje rada aplikacije", "configuration.html"),
        ]

        for title, filename in pages:
            btn = QPushButton(title)
            btn.setStyleSheet("text-align: left; padding: 6px 10px;")
            btn.clicked.connect(lambda checked, fn=filename: self.load_page(fn))
            topics_box.addWidget(btn)

        topics_box.addStretch()
        close_btn = QPushButton("Zatvori")
        close_btn.clicked.connect(self.accept)
        topics_box.addWidget(close_btn)

        left_widget = QWidget()
        left_widget.setFixedWidth(220)
        left_widget.setLayout(topics_box)

        layout.addWidget(left_widget)
        layout.addWidget(self.browser, stretch=1)

        self.load_page("introduction.html")

    def load_page(self, filename: str) -> None:
        page_path = os.path.join(ASSETS_DIR, "help", "pages", filename)
        if os.path.isfile(page_path):
            with open(page_path, "rb") as f:
                raw = f.read()
            html = raw.decode("cp1250", errors="replace")
            self.browser.setSearchPaths([
                os.path.join(ASSETS_DIR, "help", "pages"),
                os.path.join(ASSETS_DIR, "help"),
            ])
            self.browser.setHtml(html)
        else:
            self.browser.setHtml("<h3>Uputstvo nije pronađeno.</h3>")


# ---------------------------------------------------------------------------
# Main Application Window (matching & modernizing Celik.exe Dialog 102)
# ---------------------------------------------------------------------------

class CelikMainWindow(QMainWindow):
    def __init__(self, start_with_demo: bool = False) -> None:
        super().__init__()
        self.script = "cyr"  # Default script: Serbian Cyrillic (can be switched in Opcije -> Promeni pismo)
        self.current_card: Optional[EidCardData] = None
        self.available_readers: List[str] = []
        self.selected_reader: Optional[str] = None
        self.verify_format_enabled = True
        self.verify_blocks_enabled = True

        self._init_window_icon()
        self._build_ui()
        self._build_menus()
        self._set_verification_icons(None)
        self._update_buttons_state(False)
        self._apply_translations()

        # Start PC/SC monitor thread
        self.monitor = CardMonitorThread(self)
        self.monitor.readers_changed.connect(self.on_readers_changed)
        self.monitor.reading_started.connect(self.on_reading_started)
        self.monitor.card_read_success.connect(self.on_card_read_success)
        self.monitor.card_read_error.connect(self.on_card_read_error)
        self.monitor.card_removed.connect(self.on_card_removed)
        self.monitor.start()

        if start_with_demo:
            QTimer.singleShot(150, self.load_demo_card)

    def _init_window_icon(self) -> None:
        icon_path = os.path.join(ASSETS_DIR, "celik_4_256x256x32.png")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def _make_readonly_field(self, multiline: bool = False) -> QLineEdit | QTextEdit:
        if multiline:
            w = QTextEdit()
            w.setReadOnly(True)
            w.setFixedHeight(44)
            w.setStyleSheet(
                "QTextEdit { background: #ffffff; border: 1px solid #b8c2cc; "
                "border-radius: 3px; padding: 2px 5px; color: #111827; font-weight: 500; }"
            )
            return w
        w = QLineEdit()
        w.setReadOnly(True)
        w.setStyleSheet(
            "QLineEdit { background: #ffffff; border: 1px solid #b8c2cc; "
            "border-radius: 3px; padding: 3px 6px; color: #111827; font-weight: 500; }"
        )
        return w

    def _build_ui(self) -> None:
        self.resize(820, 650)
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(10)

        # 1. Official Top Banner (Serbian Tricolor + Coat of Arms + Titles)
        banner = QFrame()
        banner.setStyleSheet(
            "QFrame { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #1a365d, stop:0.65 #234876, stop:1 #2b5890); "
            "border-radius: 6px; color: white; }"
        )
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(14, 10, 14, 10)
        banner_layout.setSpacing(14)

        flag_lbl = QLabel()
        flag_path = os.path.join(ASSETS_DIR, "coat_of_arms.png")
        if os.path.isfile(flag_path):
            pix = QPixmap(flag_path).scaled(85, 43, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            flag_lbl.setPixmap(pix)
        flag_lbl.setStyleSheet("background: transparent; border: 1px solid rgba(255,255,255,0.35);")
        banner_layout.addWidget(flag_lbl)

        titles_box = QVBoxLayout()
        titles_box.setSpacing(2)
        self.lbl_header_state = QLabel()
        self.lbl_header_state.setStyleSheet(
            "color: #e2e8f0; font-size: 11px; font-weight: 600; background: transparent;"
        )
        self.lbl_header_doc = QLabel()
        self.lbl_header_doc.setStyleSheet(
            "color: #ffffff; font-size: 15px; font-weight: bold; letter-spacing: 0.5px; background: transparent;"
        )
        titles_box.addWidget(self.lbl_header_state)
        titles_box.addWidget(self.lbl_header_doc)
        banner_layout.addLayout(titles_box, stretch=1)

        root_layout.addWidget(banner)

        # 2. Main Content Body: Left Column (Portrait + Action Buttons) & Right Column (Citizen + Document Groups)
        body_layout = QHBoxLayout()
        body_layout.setSpacing(14)

        # Left Column
        left_col = QVBoxLayout()
        left_col.setSpacing(8)

        self.photo_label = QLabel()
        self.photo_label.setFixedSize(180, 232)
        self.photo_label.setAlignment(Qt.AlignCenter)
        self.photo_label.setStyleSheet(
            "QLabel { background: #e5e9f0; border: 1px solid #9aa5b1; "
            "border-radius: 4px; color: #616e7c; font-size: 12px; }"
        )
        left_col.addWidget(self.photo_label, alignment=Qt.AlignTop | Qt.AlignHCenter)

        # Action buttons under portrait
        btn_style = (
            "QPushButton { background-color: #1e4273; color: white; font-weight: 600; "
            "padding: 7px 10px; border-radius: 4px; border: none; } "
            "QPushButton:hover { background-color: #295794; } "
            "QPushButton:disabled { background-color: #9fb3c8; color: #e0e8f0; }"
        )
        sec_btn_style = (
            "QPushButton { background-color: #f0f4f8; color: #1e4273; font-weight: 600; "
            "padding: 6px 10px; border-radius: 4px; border: 1px solid #bcccdc; } "
            "QPushButton:hover { background-color: #d9e2ec; } "
            "QPushButton:disabled { color: #9aa5b1; background-color: #f5f7fa; }"
        )

        self.btn_print = QPushButton()
        self.btn_print.setStyleSheet(btn_style)
        self.btn_print.clicked.connect(self.print_document)
        left_col.addWidget(self.btn_print)

        self.btn_save_pdf = QPushButton()
        self.btn_save_pdf.setStyleSheet(sec_btn_style)
        self.btn_save_pdf.clicked.connect(self.export_pdf_dialog)
        left_col.addWidget(self.btn_save_pdf)

        self.btn_certs = QPushButton()
        self.btn_certs.setStyleSheet(sec_btn_style)
        self.btn_certs.clicked.connect(lambda: self.show_certificates_dialog("auth"))
        left_col.addWidget(self.btn_certs)

        self.btn_change_pin = QPushButton()
        self.btn_change_pin.setStyleSheet(sec_btn_style)
        self.btn_change_pin.clicked.connect(lambda: self.open_pin_dialog(verify_only=False))
        left_col.addWidget(self.btn_change_pin)

        self.btn_demo = QPushButton()
        self.btn_demo.setStyleSheet(sec_btn_style)
        self.btn_demo.clicked.connect(self.load_demo_card)
        left_col.addWidget(self.btn_demo)

        left_col.addStretch()
        body_layout.addLayout(left_col)

        # Right Column: Group 1 (Citizen Data) + Group 2 (Document Data)
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        group_style = (
            "QGroupBox { font-weight: bold; color: #1e3a5f; border: 1px solid #cbd5e1; "
            "border-radius: 5px; margin-top: 8px; padding-top: 8px; background: #f8fafc; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }"
        )

        # Citizen Data GroupBox
        self.grp_citizen = QGroupBox()
        self.grp_citizen.setStyleSheet(group_style)
        cit_grid = QGridLayout(self.grp_citizen)
        cit_grid.setHorizontalSpacing(10)
        cit_grid.setVerticalSpacing(6)

        self.lbl_surname = QLabel()
        self.edt_surname = self._make_readonly_field()
        cit_grid.addWidget(self.lbl_surname, 0, 0)
        cit_grid.addWidget(self.edt_surname, 0, 1, 1, 3)

        self.lbl_given_name = QLabel()
        self.edt_given_name = self._make_readonly_field()
        cit_grid.addWidget(self.lbl_given_name, 1, 0)
        cit_grid.addWidget(self.edt_given_name, 1, 1, 1, 3)

        self.lbl_parent_name = QLabel()
        self.edt_parent_name = self._make_readonly_field()
        cit_grid.addWidget(self.lbl_parent_name, 2, 0)
        cit_grid.addWidget(self.edt_parent_name, 2, 1, 1, 3)

        self.lbl_dob = QLabel()
        self.edt_dob = self._make_readonly_field()
        cit_grid.addWidget(self.lbl_dob, 3, 0)
        cit_grid.addWidget(self.edt_dob, 3, 1, 1, 3)

        self.lbl_pob = QLabel()
        self.edt_pob = self._make_readonly_field(multiline=True)
        cit_grid.addWidget(self.lbl_pob, 4, 0, Qt.AlignTop)
        cit_grid.addWidget(self.edt_pob, 4, 1, 1, 3)

        self.lbl_address = QLabel()
        self.edt_address = self._make_readonly_field(multiline=True)
        cit_grid.addWidget(self.lbl_address, 5, 0, Qt.AlignTop)
        cit_grid.addWidget(self.edt_address, 5, 1, 1, 3)

        self.lbl_address_date = QLabel()
        self.edt_address_date = self._make_readonly_field()
        cit_grid.addWidget(self.lbl_address_date, 6, 0)
        cit_grid.addWidget(self.edt_address_date, 6, 1, 1, 3)

        self.lbl_jmbg = QLabel()
        self.edt_jmbg = self._make_readonly_field()
        self.lbl_sex = QLabel()
        self.edt_sex = self._make_readonly_field()
        self.edt_sex.setFixedWidth(60)
        cit_grid.addWidget(self.lbl_jmbg, 7, 0)
        cit_grid.addWidget(self.edt_jmbg, 7, 1)
        cit_grid.addWidget(self.lbl_sex, 7, 2, Qt.AlignRight)
        cit_grid.addWidget(self.edt_sex, 7, 3)

        right_col.addWidget(self.grp_citizen, stretch=3)

        # Document Data GroupBox
        self.grp_doc = QGroupBox()
        self.grp_doc.setStyleSheet(group_style)
        doc_grid = QGridLayout(self.grp_doc)
        doc_grid.setHorizontalSpacing(10)
        doc_grid.setVerticalSpacing(6)

        self.lbl_issuer = QLabel()
        self.edt_issuer = self._make_readonly_field()
        doc_grid.addWidget(self.lbl_issuer, 0, 0)
        doc_grid.addWidget(self.edt_issuer, 0, 1, 1, 3)

        self.lbl_doc_no = QLabel()
        self.edt_doc_no = self._make_readonly_field()
        doc_grid.addWidget(self.lbl_doc_no, 1, 0)
        doc_grid.addWidget(self.edt_doc_no, 1, 1, 1, 3)

        self.lbl_issue_date = QLabel()
        self.edt_issue_date = self._make_readonly_field()
        self.lbl_expiry_date = QLabel()
        self.edt_expiry_date = self._make_readonly_field()
        doc_grid.addWidget(self.lbl_issue_date, 2, 0)
        doc_grid.addWidget(self.edt_issue_date, 2, 1)
        doc_grid.addWidget(self.lbl_expiry_date, 2, 2, Qt.AlignRight)
        doc_grid.addWidget(self.edt_expiry_date, 2, 3)

        # Digital Signature Verification Status Row (3 block icons + VERIFIKOVAN badge)
        self.lbl_sig_status = QLabel()
        sig_row = QHBoxLayout()
        sig_row.setSpacing(6)

        self.sig_icon_card = QLabel()
        self.sig_icon_fixed = QLabel()
        self.sig_icon_var = QLabel()
        for ic in (self.sig_icon_card, self.sig_icon_fixed, self.sig_icon_var):
            ic.setFixedSize(18, 18)
            sig_row.addWidget(ic)

        self.lbl_sig_badge = QLabel()
        self.lbl_sig_badge.setStyleSheet("font-weight: bold; color: #1b7e3c; margin-left: 6px;")
        sig_row.addWidget(self.lbl_sig_badge)
        sig_row.addStretch()

        doc_grid.addWidget(self.lbl_sig_status, 3, 0)
        doc_grid.addLayout(sig_row, 3, 1, 1, 3)

        right_col.addWidget(self.grp_doc, stretch=1)
        body_layout.addLayout(right_col, stretch=1)
        root_layout.addLayout(body_layout, stretch=1)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _build_menus(self) -> None:
        mb = self.menuBar()

        # 1. Lični dokument
        self.menu_doc = mb.addMenu("")
        self.act_read_now = QAction(self)
        self.act_read_now.triggered.connect(self.reread_card)
        self.menu_doc.addAction(self.act_read_now)

        self.act_demo = QAction(self)
        self.act_demo.triggered.connect(self.load_demo_card)
        self.menu_doc.addAction(self.act_demo)

        self.menu_doc.addSeparator()

        self.act_change_pin = QAction(self)
        self.act_change_pin.triggered.connect(lambda: self.open_pin_dialog(verify_only=False))
        self.menu_doc.addAction(self.act_change_pin)

        self.act_verify_pin = QAction(self)
        self.act_verify_pin.triggered.connect(lambda: self.open_pin_dialog(verify_only=True))
        self.menu_doc.addAction(self.act_verify_pin)

        self.menu_doc.addSeparator()

        self.act_export_pdf = QAction(self)
        self.act_export_pdf.triggered.connect(self.export_pdf_dialog)
        self.menu_doc.addAction(self.act_export_pdf)

        self.act_print = QAction(self)
        self.act_print.triggered.connect(self.print_document)
        self.menu_doc.addAction(self.act_print)

        self.menu_doc.addSeparator()

        self.act_exit = QAction(self)
        self.act_exit.triggered.connect(self.close)
        self.menu_doc.addAction(self.act_exit)

        # 2. Opcije
        self.menu_options = mb.addMenu("")
        self.menu_script = QMenu(self)
        self.menu_options.addMenu(self.menu_script)

        script_group = QActionGroup(self)
        self.act_cyr = QAction(self, checkable=True)
        self.act_lat = QAction(self, checkable=True)
        self.act_cyr.setChecked(self.script == "cyr")
        self.act_lat.setChecked(self.script == "lat")
        script_group.addAction(self.act_cyr)
        script_group.addAction(self.act_lat)
        self.act_cyr.triggered.connect(lambda: self.set_script("cyr"))
        self.act_lat.triggered.connect(lambda: self.set_script("lat"))
        self.menu_script.addAction(self.act_cyr)
        self.menu_script.addAction(self.act_lat)

        self.menu_reader = QMenu(self)
        self.menu_options.addMenu(self.menu_reader)
        self._rebuild_reader_menu()

        self.menu_options.addSeparator()
        self.act_verify_format = QAction(self, checkable=True, checked=True)
        self.act_verify_blocks = QAction(self, checkable=True, checked=True)
        self.act_verify_format.triggered.connect(self._on_verify_options_changed)
        self.act_verify_blocks.triggered.connect(self._on_verify_options_changed)
        self.menu_options.addAction(self.act_verify_format)
        self.menu_options.addAction(self.act_verify_blocks)

        # 3. Prikaz sertifikata
        self.menu_certs = mb.addMenu("")
        self.act_cert_auth = QAction(self)
        self.act_cert_auth.triggered.connect(lambda: self.show_certificates_dialog("auth"))
        self.menu_certs.addAction(self.act_cert_auth)

        self.act_cert_sign = QAction(self)
        self.act_cert_sign.triggered.connect(lambda: self.show_certificates_dialog("sign"))
        self.menu_certs.addAction(self.act_cert_sign)

        # 4. Pomoć
        self.menu_help = mb.addMenu("")
        self.act_manual = QAction(self)
        self.act_manual.triggered.connect(self.show_manual_dialog)
        self.menu_help.addAction(self.act_manual)

        self.act_about = QAction(self)
        self.act_about.triggered.connect(self.show_about_dialog)
        self.menu_help.addAction(self.act_about)

    def _rebuild_reader_menu(self) -> None:
        self.menu_reader.clear()
        tr = UI_STRINGS[self.script]
        grp = QActionGroup(self)

        any_act = QAction(tr["any_reader"], self, checkable=True)
        any_act.setChecked(self.selected_reader is None)
        any_act.triggered.connect(lambda: self._select_reader(None))
        grp.addAction(any_act)
        self.menu_reader.addAction(any_act)

        for rname in self.available_readers:
            act = QAction(rname, self, checkable=True)
            act.setChecked(self.selected_reader == rname)
            act.triggered.connect(lambda checked, r=rname: self._select_reader(r))
            grp.addAction(act)
            self.menu_reader.addAction(act)

    def _select_reader(self, reader_name: Optional[str]) -> None:
        self.selected_reader = reader_name
        self.monitor.set_selected_reader(reader_name)

    def set_script(self, script: str) -> None:
        self.script = script
        self._apply_translations()
        if self.current_card:
            self._populate_card_fields(self.current_card)

    def _apply_translations(self) -> None:
        tr = UI_STRINGS[self.script]
        self.setWindowTitle(tr["window_title"])
        self.lbl_header_state.setText(tr["header_state"])
        if self.current_card and self.current_card.is_foreigner:
            self.lbl_header_doc.setText(tr["header_doc_if"])
            self.grp_citizen.setTitle(tr["group_foreigner"])
            self.lbl_address.setText(tr["lbl_address_if"])
            self.lbl_jmbg.setText(tr["lbl_ebs"])
        else:
            self.lbl_header_doc.setText(tr["header_doc_id"])
            self.grp_citizen.setTitle(tr["group_citizen"])
            self.lbl_address.setText(tr["lbl_address"])
            self.lbl_jmbg.setText(tr["lbl_jmbg"])

        self.menu_doc.setTitle(tr["menu_doc"])
        self.act_read_now.setText(tr["act_read_now"])
        self.act_demo.setText(tr["act_demo"])
        self.act_change_pin.setText(tr["act_change_pin"])
        self.act_verify_pin.setText(tr["act_verify_pin"])
        self.act_export_pdf.setText(tr["act_export_pdf"])
        self.act_print.setText(tr["act_print"])
        self.act_exit.setText(tr["act_exit"])

        self.menu_options.setTitle(tr["menu_options"])
        self.menu_script.setTitle(tr["menu_script"])
        self.act_cyr.setText(tr["act_cyr"])
        self.act_lat.setText(tr["act_lat"])
        self.menu_reader.setTitle(tr["menu_reader"])
        self.act_verify_format.setText(tr["act_verify_format"])
        self.act_verify_blocks.setText(tr["act_verify_blocks"])

        self.menu_certs.setTitle(tr["menu_certs"])
        self.act_cert_auth.setText(tr["act_cert_auth"])
        self.act_cert_sign.setText(tr["act_cert_sign"])

        self.menu_help.setTitle(tr["menu_help"])
        self.act_manual.setText(tr["act_manual"])
        self.act_about.setText(tr["act_about"])

        self.lbl_surname.setText(tr["lbl_surname"])
        self.lbl_given_name.setText(tr["lbl_given_name"])
        self.lbl_parent_name.setText(tr["lbl_parent_name"])
        self.lbl_dob.setText(tr["lbl_dob"])
        self.lbl_pob.setText(tr["lbl_pob"])
        self.lbl_address_date.setText(tr["lbl_address_date"])
        self.lbl_sex.setText(tr["lbl_sex"])

        self.grp_doc.setTitle(tr["group_doc"])
        self.lbl_issuer.setText(tr["lbl_issuer"])
        self.lbl_doc_no.setText(tr["lbl_doc_no"])
        self.lbl_issue_date.setText(tr["lbl_issue_date"])
        self.lbl_expiry_date.setText(tr["lbl_expiry_date"])
        self.lbl_sig_status.setText(tr["lbl_sig_status"])

        self.btn_print.setText(tr["btn_print"])
        self.btn_save_pdf.setText(tr["btn_save_pdf"])
        self.btn_certs.setText(tr["btn_certs"])
        self.btn_change_pin.setText(tr["btn_change_pin"])
        self.btn_demo.setText(tr["btn_demo"])

        if not self.current_card:
            self.photo_label.setText(tr["no_photo"])
            self.status_bar.showMessage(
                tr["status_no_card"] if self.available_readers else tr["status_no_reader"]
            )

        self._rebuild_reader_menu()

    def _set_verification_icons(self, verified: Optional[bool]) -> None:
        tr = UI_STRINGS[self.script]
        green_path = os.path.join(ASSETS_DIR, "help", "images", "Green-check-mark-16.png")
        grey_path = os.path.join(ASSETS_DIR, "help", "images", "Grey-minus-16.png")
        red_path = os.path.join(ASSETS_DIR, "help", "images", "Red-exclamation-16.png")

        if verified is None:
            pix = QPixmap(grey_path) if os.path.isfile(grey_path) else QPixmap()
            for ic in (self.sig_icon_card, self.sig_icon_fixed, self.sig_icon_var):
                ic.setPixmap(pix)
                ic.setToolTip("")
            self.lbl_sig_badge.setText("—")
            self.lbl_sig_badge.setStyleSheet("color: #64748b; font-weight: bold;")
            return

        ok_pix = QPixmap(green_path) if os.path.isfile(green_path) else QPixmap()
        skip_pix = QPixmap(grey_path) if os.path.isfile(grey_path) else QPixmap()
        fail_pix = QPixmap(red_path) if os.path.isfile(red_path) else QPixmap()

        self.sig_icon_card.setPixmap(
            (ok_pix if verified else fail_pix) if self.verify_format_enabled else skip_pix
        )
        self.sig_icon_card.setToolTip(tr["tip_sig_card"])

        for ic, tip in (
            (self.sig_icon_fixed, tr["tip_sig_fixed"]),
            (self.sig_icon_var, tr["tip_sig_var"]),
        ):
            ic.setPixmap(
                (ok_pix if verified else fail_pix) if self.verify_blocks_enabled else skip_pix
            )
            ic.setToolTip(tip)

        if not self.verify_format_enabled and not self.verify_blocks_enabled:
            self.lbl_sig_badge.setText("—")
            self.lbl_sig_badge.setStyleSheet("color: #64748b; font-weight: bold;")
        elif verified:
            self.lbl_sig_badge.setText(tr["status_verified"])
            self.lbl_sig_badge.setStyleSheet("color: #1b7e3c; font-weight: bold;")
        else:
            self.lbl_sig_badge.setText(tr["status_not_verified"])
            self.lbl_sig_badge.setStyleSheet("color: #c92a2a; font-weight: bold;")

    def _on_verify_options_changed(self) -> None:
        self.verify_format_enabled = self.act_verify_format.isChecked()
        self.verify_blocks_enabled = self.act_verify_blocks.isChecked()
        if self.current_card:
            self._set_verification_icons(self.current_card.card_verified)

    def _update_buttons_state(self, has_card: bool) -> None:
        self.btn_print.setEnabled(has_card)
        self.btn_save_pdf.setEnabled(has_card)
        self.btn_certs.setEnabled(has_card)
        self.btn_change_pin.setEnabled(has_card)
        self.act_export_pdf.setEnabled(has_card)
        self.act_print.setEnabled(has_card)
        self.act_change_pin.setEnabled(has_card)
        self.act_verify_pin.setEnabled(has_card)
        self.act_cert_auth.setEnabled(has_card)
        self.act_cert_sign.setEnabled(has_card)

    def _populate_card_fields(self, card: EidCardData) -> None:
        tr = UI_STRINGS[self.script]
        self.current_card = card

        if card.is_foreigner:
            self.lbl_header_doc.setText(tr["header_doc_if"])
            self.grp_citizen.setTitle(tr["group_foreigner"])
            self.lbl_parent_name.setText(tr["lbl_nationality"])
            self.edt_parent_name.setText(card.fixed.nationality_full or card.fixed.parent_given_name)
            self.lbl_address.setText(tr["lbl_address_if"])
            self.lbl_jmbg.setText(tr["lbl_ebs"])
        else:
            self.lbl_header_doc.setText(tr["header_doc_id"])
            self.grp_citizen.setTitle(tr["group_citizen"])
            self.lbl_parent_name.setText(tr["lbl_parent_name"])
            self.edt_parent_name.setText(card.fixed.parent_given_name)
            self.lbl_address.setText(tr["lbl_address"])
            self.lbl_jmbg.setText(tr["lbl_jmbg"])

        self.edt_surname.setText(card.fixed.surname)
        self.edt_given_name.setText(card.fixed.given_name)
        self.edt_dob.setText(card.fixed.date_of_birth)
        self.edt_pob.setPlainText(card.full_place_of_birth)
        self.edt_address.setPlainText(card.full_address)
        self.edt_address_date.setText(card.variable.address_date)
        self.edt_jmbg.setText(card.fixed.personal_number)
        self.edt_sex.setText(card.fixed.sex)

        self.edt_issuer.setText(card.document.issuing_authority)
        self.edt_doc_no.setText(card.document.doc_reg_no)
        self.edt_issue_date.setText(card.document.issuing_date)
        self.edt_expiry_date.setText(card.document.expiry_date)

        # Highlight expired document date in red (matching CelikHelp specification)
        is_expired = False
        try:
            exp_clean = card.document.expiry_date.strip().rstrip(".")
            exp_dt = datetime.datetime.strptime(exp_clean, "%d.%m.%Y").date()
            if exp_dt < datetime.date.today():
                is_expired = True
        except Exception:
            pass

        if is_expired:
            self.edt_expiry_date.setStyleSheet(
                "QLineEdit { background: #fff5f5; border: 1px solid #e03131; "
                "border-radius: 3px; padding: 3px 6px; color: #c92a2a; font-weight: bold; }"
            )
        else:
            self.edt_expiry_date.setStyleSheet(
                "QLineEdit { background: #ffffff; border: 1px solid #b8c2cc; "
                "border-radius: 3px; padding: 3px 6px; color: #111827; font-weight: 500; }"
            )

        # Portrait photo
        if card.portrait_jpeg:
            pix = QPixmap()
            if pix.loadFromData(card.portrait_jpeg):
                scaled = pix.scaled(
                    self.photo_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.photo_label.setPixmap(scaled)
        else:
            self.photo_label.setPixmap(QPixmap())
            self.photo_label.setText(tr["no_photo"])

        self._set_verification_icons(card.card_verified)
        self._update_buttons_state(True)

    # -----------------------------------------------------------------------
    # Slots & User Actions
    # -----------------------------------------------------------------------

    def on_readers_changed(self, readers: List[str]) -> None:
        self.available_readers = readers
        self._rebuild_reader_menu()
        tr = UI_STRINGS[self.script]
        if not self.current_card:
            self.status_bar.showMessage(
                tr["status_no_card"] if readers else tr["status_no_reader"]
            )

    def on_reading_started(self, reader_name: str) -> None:
        tr = UI_STRINGS[self.script]
        self.lbl_sig_badge.setText(tr["status_reading"])
        self.lbl_sig_badge.setStyleSheet("color: #1e4273; font-weight: bold;")
        self.status_bar.showMessage(f"{tr['status_reading']} ({reader_name})")

    def on_card_read_success(self, card: EidCardData) -> None:
        self._populate_card_fields(card)
        tr = UI_STRINGS[self.script]
        self.status_bar.showMessage(tr["status_card_ready"].format(reader=card.reader_name))

    def on_card_read_error(self, err_msg: str) -> None:
        self._set_verification_icons(False)
        self.status_bar.showMessage(f"Greška: {err_msg}")
        QMessageBox.warning(self, "Greška pri čitanju kartice", err_msg)

    def on_card_removed(self, reader_name: str) -> None:
        tr = UI_STRINGS[self.script]
        self.status_bar.showMessage(tr["status_no_card"])

    def reread_card(self) -> None:
        if self.available_readers:
            self.monitor.request_reread()
        else:
            self.load_demo_card()

    def load_demo_card(self) -> None:
        demo = create_demo_card_data()
        self._populate_card_fields(demo)
        tr = UI_STRINGS[self.script]
        self.status_bar.showMessage(tr["status_demo_ready"])

    def export_pdf_dialog(self) -> None:
        if not self.current_card:
            return
        surname = self.current_card.fixed.surname or "Gradjanin"
        default_filename = f"Licna_karta_{surname}_{self.current_card.document.doc_reg_no}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Sačuvaj PDF izvod iz elektronske lične karte",
            os.path.join(BASE_DIR, default_filename),
            "PDF dokument (*.pdf)",
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            generate_eid_pdf(self.current_card, path, script=self.script)
            reply = QMessageBox.question(
                self,
                "PDF izvod je sačuvan",
                f"Izvod iz elektronske lične karte je sačuvan u:\n{path}\n\nŽelite li da otvorite PDF dokument?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as exc:
            QMessageBox.critical(self, "Greška", f"Greška prilikom kreiranja PDF dokumenta:\n{exc}")

    def print_document(self) -> None:
        if not self.current_card:
            return
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPrinter.A4)
        printer.setDocName(f"Licna_karta_{self.current_card.document.doc_reg_no}")

        dlg = QPrintDialog(printer, self)
        dlg.setWindowTitle("Štampa podataka iz elektronske lične karte")
        if dlg.exec_() != QDialog.Accepted:
            return

        # If user chose "Print to File (PDF)" or a system CUPS printer, generate high-res A4 sheet
        if printer.outputFormat() == QPrinter.PdfFormat and printer.outputFileName():
            generate_eid_pdf(self.current_card, printer.outputFileName(), script=self.script)
            QMessageBox.information(
                self,
                "Štampa podataka",
                f"Dokument je odštampan u PDF fajl:\n{printer.outputFileName()}",
            )
            return

        # Otherwise generate temporary A4 PDF and send to CUPS lpr or render via QPainter
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_pdf = tmp.name
        try:
            generate_eid_pdf(self.current_card, tmp_pdf, script=self.script)
            printer_name = printer.printerName()
            cmd = ["lpr"]
            if printer_name:
                cmd.extend(["-P", printer_name])
            cmd.append(tmp_pdf)
            subprocess.run(cmd, check=True)
            QMessageBox.information(
                self,
                "Štampa podataka",
                f"Dokument je uspešno poslat na štampač: {printer_name or 'podrazumevani štampač'}.",
            )
        except Exception:
            # Fallback to direct QPainter rendering onto QPrinter
            self._paint_onto_qprinter(printer)
        finally:
            try:
                os.unlink(tmp_pdf)
            except OSError:
                pass

    def _paint_onto_qprinter(self, printer: QPrinter) -> None:
        if not self.current_card:
            return
        painter = QPainter(printer)
        try:
            rect = painter.viewport()
            pix = self.centralWidget().grab()
            scaled = pix.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(0, 0, scaled)
        finally:
            painter.end()

    def show_certificates_dialog(self, initial_type: str = "auth") -> None:
        if not self.current_card:
            return
        if not self.current_card.certificates:
            QMessageBox.information(
                self,
                "Prikaz sertifikata",
                "Na ovoj kartici nisu pronađeni korisnički X.509 sertifikati.",
            )
            return
        dlg = CertificateDialog(self.current_card.certificates, initial_type=initial_type, parent=self)
        dlg.exec_()

    def open_pin_dialog(self, verify_only: bool = False) -> None:
        if not self.current_card:
            return
        dlg = PinDialog(
            reader_name=self.current_card.reader_name,
            is_demo=self.current_card.is_demo,
            verify_only=verify_only,
            parent=self,
        )
        dlg.exec_()

    def show_manual_dialog(self) -> None:
        dlg = HelpManualDialog(self)
        dlg.exec_()

    def show_about_dialog(self) -> None:
        QMessageBox.about(
            self,
            "O aplikaciji Čitač elektronske lične karte",
            "<h3>ČELIX 1.0</h3>"
            "<p><b>Čitač elektronske lične karte za Linux (PC/SC)</b></p>"
            "<p>Kompatibilan sa svim generacijama elektronskih ličnih karata Republike Srbije "
            "(Apollo 2008–2014, Gemalto / IF2020 2014+, Lična karta za stranca i Dozvola za "
            "privremeni boravak i rad).</p>"
            "<p><b>Podržane funkcionalnosti:</b></p>"
            "<ul>"
            "<li>Čitanje fiksnih, promenljivih i podataka o dokumentu + fotografije</li>"
            "<li>Zvanični A4 PDF izvod za štampu (ћирилица и латиница)</li>"
            "<li>Pregled i izvoz X.509 sertifikata sa kartice</li>"
            "<li>Provera i promena korisničkog PIN-a (PKCS#15 / CardEdge)</li>"
            "</ul>"
            "<p><small>Zasnovano na specifikaciji Čelik 1.4.2.1 (MUP RS / Veridos Netset d.o.o.).</small></p>",
        )

    def closeEvent(self, event) -> None:
        self.monitor.stop()
        self.monitor.wait(1000)
        super().closeEvent(event)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Čelik Linux — Čitač elektronske lične karte")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Pokreni aplikaciju sa učitanom demonstracionom ličnom kartom",
    )
    parser.add_argument(
        "--export-demo-pdf",
        metavar="PUTANJA",
        help="Generiši zvanični A4 PDF izvod iz demo lične karte i izađi",
    )
    args = parser.parse_args()

    if args.export_demo_pdf:
        card = create_demo_card_data()
        out = generate_eid_pdf(card, args.export_demo_pdf, script="cyr")
        print(f"PDF generated: {out}")
        return 0

    app = QApplication(sys.argv)
    app.setApplicationName("Čelik Linux")
    app.setOrganizationName("MUP RS / Celik Linux")

    win = CelikMainWindow(start_with_demo=args.demo)
    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
