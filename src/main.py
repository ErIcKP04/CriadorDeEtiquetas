import os
import sys
import ctypes
import json
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox, Canvas, Scrollbar, Toplevel

from PIL import Image, ImageDraw, ImageFont, ImageTk
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm


# =========================
# Persistência (memória)
# =========================
APP_NAME = "EtiquetasTransportadora"


# =========================
# ÍCONE (Title bar / Taskbar - Windows + PyInstaller)
# =========================
# ✅ Tenha um arquivo "Etiqueta_icone.ico"
# - No modo DEV: pode estar junto do .py
# - No EXE onefile: precisa empacotar com --add-data "...Etiqueta_icone.ico;."
ICON_FILE = "Etiqueta_icone.ico"

# (Opcional) fallback absoluto no DEV:
ICON_ABS_DEV = r"D:\Arquivos e Programas HD\Code\Criador_de_Etiquetas\assets\Etiqueta_icone.ico"

def resource_path(rel_path: str) -> str:
    """Caminho que funciona no .py e no .exe (PyInstaller)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel_path)
    return os.path.join(os.path.dirname(__file__), rel_path)


def get_icon_path() -> str:
    """Procura o ícone em locais comuns (DEV, bundle, ao lado do EXE)."""
    # 1) DEV (absoluto)
    if ICON_ABS_DEV and os.path.exists(ICON_ABS_DEV):
        return ICON_ABS_DEV

    # 2) dentro do bundle (PyInstaller --add-data)
    p = resource_path(ICON_FILE)
    if os.path.exists(p):
        return p

    # 3) ao lado do exe (se você copiar o .ico junto do .exe)
    if getattr(sys, "frozen", False):
        p2 = os.path.join(os.path.dirname(sys.executable), ICON_FILE)
        if os.path.exists(p2):
            return p2

    # 4) pasta atual
    p3 = os.path.join(os.getcwd(), ICON_FILE)
    if os.path.exists(p3):
        return p3

    return ""


def set_appusermodelid_windows():
    """Ajuda o Windows a usar o ícone correto na taskbar/alt-tab."""
    try:
        if sys.platform.startswith("win"):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                u"EtiquetasTransportadora.1"
            )
    except Exception:
        pass


def apply_icon(win):
    """Aplica o ícone na janela (title bar). Reaplique via after() para ser mais confiável."""
    icon_path = get_icon_path()
    if not icon_path or not os.path.exists(icon_path):
        return

    # 1) iconbitmap (Windows .ico)
    try:
        try:
            win.iconbitmap(default=icon_path)
        except Exception:
            pass
        try:
            win.iconbitmap(icon_path)
        except Exception:
            pass
        try:
            win.wm_iconbitmap(icon_path)
        except Exception:
            pass
    except Exception:
        pass

    # 2) fallback com iconphoto (mantém referência!)
    try:
        img = Image.open(icon_path).convert("RGBA").resize((64, 64))
        win._icon_photo = ImageTk.PhotoImage(img)
        win.iconphoto(True, win._icon_photo)
    except Exception:
        pass

    try:
        win.update_idletasks()
    except Exception:
        pass


def get_app_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:  # Windows
        return Path(appdata) / APP_NAME
    return Path.home() / ".config" / APP_NAME


APP_DIR = get_app_dir()
STATE_FILE = APP_DIR / "state.json"
LOGO_FILE = APP_DIR / "logo.png"


def load_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_state(state: dict) -> None:
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def uniq_add(lst: list[str], value: str) -> list[str]:
    v = (value or "").strip()
    if not v:
        return lst
    if v not in lst:
        lst.append(v)
    return lst


# =========================
# Tema (azul escuro)
# =========================
BG = "#07101F"
PANEL = "#0B1B33"
PANEL2 = "#081426"
BORDER = "#14345D"
TEXT = "#EAF1FF"
MUTED = "#A9B4C6"
ACCENT = "#1E4D86"
ACCENT_HOVER = "#2561AB"


# =========================
# Layout A4 em mm (margem automática)
# =========================
def compute_layout_mm(per_page: int, label_w_mm: float, label_h_mm: float):
    page_w_pt, page_h_pt = A4
    page_w_mm = page_w_pt / mm
    page_h_mm = page_h_pt / mm

    layouts = {1: (1, 1), 2: (1, 2), 4: (2, 2), 6: (2, 3)}
    if per_page not in layouts:
        raise ValueError("Use 1, 2, 4 ou 6 por folha.")

    cols, rows = layouts[per_page]

    default_margin = 5.0
    margin_x_max = (page_w_mm - cols * label_w_mm) / 2
    margin_y_max = (page_h_mm - rows * label_h_mm) / 2

    if margin_x_max < 0 or margin_y_max < 0:
        raise ValueError(
            f"Etiqueta {label_w_mm}x{label_h_mm} mm NÃO cabe em {per_page}/folha no A4.\n"
            f"Tente outro layout (ex: 1 por folha) ou reduza o tamanho."
        )

    margin_x = min(default_margin, margin_x_max)
    margin_y = min(default_margin, margin_y_max)

    cell_w = (page_w_mm - 2 * margin_x) / cols
    cell_h = (page_h_mm - 2 * margin_y) / rows

    return cols, rows, margin_x, margin_y, cell_w, cell_h, page_w_mm, page_h_mm


# =========================
# PNG Preview (etiqueta única)
# =========================
def make_label_image(data: dict, logo_path: Path | None, out_path: Path, w_px=900, h_px=560) -> None:
    img = Image.new("RGB", (w_px, h_px), (7, 16, 31))
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arialbd.ttf", 36)
        font_bold = ImageFont.truetype("arialbd.ttf", 28)
    except Exception:
        font_title = ImageFont.load_default()
        font_bold = ImageFont.load_default()

    pad = 24
    draw.rounded_rectangle(
        [pad, pad, w_px - pad, h_px - pad],
        radius=22,
        fill=(11, 27, 51),
        outline=(20, 52, 93),
        width=2
    )

    if logo_path and logo_path.exists():
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo.thumbnail((220, 120))
            img.paste(logo, (pad + 16, pad + 16), logo)
        except Exception:
            pass

    draw.text((pad + 260, pad + 24), "ETIQUETA DE COLETA", fill=(234, 241, 255), font=font_title)

    x = pad + 20
    y = pad + 150
    step = 56

    def line(label, value):
        nonlocal y
        draw.text((x, y), f"{label} {value or ''}", fill=(234, 241, 255), font=font_bold)
        y += step

    line("DE:", data.get("de", ""))
    line("PARA:", data.get("para", ""))
    line("CIDADE/UF:", data.get("cidade_uf", ""))
    line("NF:", data.get("nf", ""))
    line("TRANSP.:", data.get("transportadora", ""))
    line("Nº TRANSP.:", data.get("num_transportadora", ""))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")


# =========================
# PDF: desenha UMA etiqueta (SEM borda)
# =========================
def draw_one_label_pdf(c: canvas.Canvas, data: dict, logo_path: Path | None,
                       x_mm: float, y_mm: float, w_mm: float, h_mm: float) -> None:
    base_w, base_h = 100.0, 60.0
    scale = min(w_mm / base_w, h_mm / base_h)
    scale = max(0.9, min(scale, 3.0))

    def s(v: float) -> float:
        return v * scale

    pad = s(6.0)
    left = x_mm + pad
    top = y_mm + h_mm - pad

    title_font = max(18, int(round(s(20.0))))
    body_font = max(13, int(round(s(15.0))))

    title_x = left
    if logo_path and logo_path.exists():
        try:
            lw, lh = s(30.0), s(16.0)
            c.drawImage(
                str(logo_path),
                left * mm,
                (top - lh) * mm,
                width=lw * mm,
                height=lh * mm,
                mask="auto",
                preserveAspectRatio=True,
                anchor="nw",
            )
            title_x = left + lw + s(6.0)
        except Exception:
            title_x = left

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", title_font)
    c.drawString(title_x * mm, (top - s(2.0)) * mm, "ETIQUETA DE COLETA")

    c.setFont("Helvetica", body_font)
    y = top - s(22.0)
    step = s(10.0)

    def line(label: str, value: str):
        nonlocal y
        c.drawString(left * mm, y * mm, f"{label} {value or ''}")
        y -= step

    line("DE:", data.get("de", ""))
    line("PARA:", data.get("para", ""))
    line("CIDADE/UF:", data.get("cidade_uf", ""))
    line("NF:", data.get("nf", ""))
    line("TRANSP.:", data.get("transportadora", ""))
    line("Nº TRANSP.:", data.get("num_transportadora", ""))


# =========================
# PDF A4 com várias etiquetas diferentes (múltiplas páginas)
# =========================
def make_labels_pdf_a4_multi(labels: list[dict], logo_path: Path | None, out_path: Path,
                             label_w_mm: float, label_h_mm: float, per_page: int) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cols, rows, margin_x, margin_y, cell_w, cell_h, page_w_mm, page_h_mm = compute_layout_mm(
        per_page, label_w_mm, label_h_mm
    )

    c = canvas.Canvas(str(out_path), pagesize=A4)

    idx = 0
    total = len(labels)
    while idx < total:
        for r in range(rows):
            for col in range(cols):
                if idx >= total:
                    break

                d = labels[idx]
                idx += 1

                x0 = margin_x + col * cell_w
                y0 = page_h_mm - margin_y - (r + 1) * cell_h

                x = x0 + (cell_w - label_w_mm) / 2
                y = y0 + (cell_h - label_h_mm) / 2

                draw_one_label_pdf(c, d, logo_path, x, y, label_w_mm, label_h_mm)

        c.showPage()

    c.save()


# =========================
# Pré-visualização A4 (delimita a etiqueta REAL)
# =========================
def make_preview_a4_image(labels: list[dict], label_w_mm: float, label_h_mm: float, per_page: int) -> Image.Image:
    W, H = 1240, 1754  # ~150 DPI
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    try:
        f = ImageFont.truetype("arial.ttf", 18)
        fb = ImageFont.truetype("arialbd.ttf", 20)
    except Exception:
        f = fb = ImageFont.load_default()

    cols, rows, margin_x, margin_y, cell_w_mm, cell_h_mm, page_w_mm, page_h_mm = compute_layout_mm(
        per_page, label_w_mm, label_h_mm
    )

    px_per_mm_x = W / page_w_mm
    px_per_mm_y = H / page_h_mm

    def mm_to_px_x(v): return int(round(v * px_per_mm_x))
    def mm_to_px_y(v): return int(round(v * px_per_mm_y))

    draw.text(
        (mm_to_px_x(margin_x), 10),
        f"Pré-visualização A4 — {per_page} por folha | Etiqueta: {label_w_mm}x{label_h_mm} mm | Margem: {margin_x:.1f}/{margin_y:.1f} mm",
        fill=(0, 0, 0),
        font=fb
    )

    idx = 0
    for r in range(rows):
        for c_ in range(cols):
            x0_mm = margin_x + c_ * cell_w_mm
            y0_mm = margin_y + r * cell_h_mm
            x1_mm = x0_mm + cell_w_mm
            y1_mm = y0_mm + cell_h_mm

            x0 = mm_to_px_x(x0_mm)
            y0 = mm_to_px_y(y0_mm)
            x1 = mm_to_px_x(x1_mm)
            y1 = mm_to_px_y(y1_mm)

            draw.rectangle([x0, y0, x1, y1], outline=(230, 230, 230), width=2)

            lx0_mm = x0_mm + (cell_w_mm - label_w_mm) / 2
            ly0_mm = y0_mm + (cell_h_mm - label_h_mm) / 2
            lx1_mm = lx0_mm + label_w_mm
            ly1_mm = ly0_mm + label_h_mm

            lx0 = mm_to_px_x(lx0_mm)
            ly0 = mm_to_px_y(ly0_mm)
            lx1 = mm_to_px_x(lx1_mm)
            ly1 = mm_to_px_y(ly1_mm)

            draw.rectangle([lx0, ly0, lx1, ly1], outline=(120, 120, 120), width=3)

            if idx < len(labels):
                d = labels[idx]
                idx += 1

                tx = lx0 + 16
                ty = ly0 + 14
                draw.text((tx, ty), "ETIQUETA", fill=(0, 0, 0), font=fb)
                ty += 30

                lines = [
                    f"DE: {d.get('de','')[:32]}",
                    f"PARA: {d.get('para','')[:32]}",
                    f"CIDADE/UF: {d.get('cidade_uf','')[:28]}",
                    f"NF: {d.get('nf','')[:22]}",
                    f"TRANSP.: {d.get('transportadora','')[:26]}",
                    f"Nº TRANSP.: {d.get('num_transportadora','')[:22]}",
                ]
                for t in lines:
                    draw.text((tx, ty), t, fill=(0, 0, 0), font=f)
                    ty += 24

    return img


# =========================
# UI: CadastroList
# =========================
class CadastroList(ctk.CTkFrame):
    def __init__(self, master, title: str, get_items, set_items):
        super().__init__(master, fg_color=PANEL, corner_radius=16, border_width=1, border_color=BORDER)
        self.get_items = get_items
        self.set_items = set_items

        ctk.CTkLabel(self, text=title, text_color=TEXT,
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=14, pady=(14, 8))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 10))

        self.entry = ctk.CTkEntry(
            row,
            placeholder_text="Digite e clique em Adicionar",
            fg_color=PANEL2,
            border_color=ACCENT,
            text_color=TEXT,
            corner_radius=12,
            height=36,
        )
        self.entry.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            row,
            text="Adicionar",
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            corner_radius=12,
            height=36,
            command=self.add_item,
        ).pack(side="left", padx=(10, 0))

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self.refresh()

    def refresh(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        items = self.get_items()
        if not items:
            ctk.CTkLabel(self.list_frame, text="(vazio)", text_color=MUTED).pack(anchor="w", pady=6)
            return

        for item in items:
            line = ctk.CTkFrame(
                self.list_frame,
                fg_color=PANEL2,
                corner_radius=12,
                border_width=1,
                border_color=BORDER,
            )
            line.pack(fill="x", pady=6)

            ctk.CTkLabel(line, text=item, text_color=TEXT).pack(side="left", padx=10, pady=10)

            ctk.CTkButton(
                line,
                text="Remover",
                fg_color="#3A1C24",
                hover_color="#5A2B36",
                corner_radius=10,
                height=30,
                command=lambda it=item: self.remove_item(it),
            ).pack(side="right", padx=10, pady=8)

    def add_item(self):
        v = self.entry.get().strip()
        if not v:
            return
        items = list(self.get_items())
        if v not in items:
            items.append(v)
            self.set_items(items)
        self.entry.delete(0, "end")
        self.refresh()

    def remove_item(self, item: str):
        items = [x for x in self.get_items() if x != item]
        self.set_items(items)
        self.refresh()


# =========================
# App
# =========================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")

        # Windows/taskbar (ajuda a “colar” o ícone do app na taskbar)
        set_appusermodelid_windows()

        # Aplicar ícone depois (CustomTkinter pode resetar)
        self.after(0, lambda: apply_icon(self))
        self.after(200, lambda: apply_icon(self))
        self.after(800, lambda: apply_icon(self))

        self.title("Gerador de Etiquetas - Transportadora")
        self.geometry("1020x780")
        self.minsize(900, 640)
        self.configure(fg_color=BG)

        self.app_state = load_state()
        self.app_state.setdefault("emitentes", [])
        self.app_state.setdefault("destinatarios", [])
        self.app_state.setdefault("cidades_uf", [])
        self.app_state.setdefault("transportadoras", [])

        self.de_var = ctk.StringVar(value=self.app_state.get("last_de", ""))
        self.para_var = ctk.StringVar(value=self.app_state.get("last_para", ""))
        self.cidade_var = ctk.StringVar(value=self.app_state.get("last_cidade_uf", ""))
        self.nf_var = ctk.StringVar(value=self.app_state.get("last_nf", ""))
        self.num_transp_var = ctk.StringVar(value=self.app_state.get("last_num_transportadora", ""))
        self.transportadora_var = ctk.StringVar(value=self.app_state.get("last_transportadora", ""))

        self.size_var = ctk.StringVar(value=self.app_state.get("last_size", "100 x 60 mm"))
        self.custom_w_var = ctk.StringVar(value=str(self.app_state.get("last_custom_w", "")))
        self.custom_h_var = ctk.StringVar(value=str(self.app_state.get("last_custom_h", "")))
        self.size_map = {
            "100 x 60 mm": (100.0, 60.0),
            "100 x 150 mm": (100.0, 150.0),
            "A6 (105 x 148 mm)": (105.0, 148.0),
            "Personalizado": None,
        }

        self.per_page_var = ctk.StringVar(value=self.app_state.get("last_per_page", "4 por folha (A4)"))
        self.per_page_map = {
            "1 por folha (A4)": 1,
            "2 por folha (A4)": 2,
            "4 por folha (A4)": 4,
            "6 por folha (A4)": 6,
        }

        self.sheet_labels: list[dict] = []

        self.tabs = ctk.CTkTabview(
            self,
            fg_color=BG,
            segmented_button_fg_color=PANEL,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_hover_color="#0F2648",
        )
        self.tabs.pack(fill="both", expand=True, padx=16, pady=16)

        self.tab_etiqueta = self.tabs.add("Etiqueta")
        self.tab_cadastro = self.tabs.add("Cadastro")
        self.tab_logo = self.tabs.add("Logo")

        self._build_etiqueta()
        self._build_cadastro()
        self._build_logo()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def save_now(self):
        save_state(self.app_state)

    def set_list(self, key: str, items: list[str]):
        self.app_state[key] = items
        self.save_now()
        self.refresh_option_menus()

    def refresh_option_menus(self):
        self.de_menu.configure(values=self.app_state.get("emitentes", []))
        self.para_menu.configure(values=self.app_state.get("destinatarios", []))
        self.cidade_menu.configure(values=self.app_state.get("cidades_uf", []))
        self.transportadora_menu.configure(values=self.app_state.get("transportadoras", []))

    def _build_etiqueta(self):
        container = ctk.CTkFrame(self.tab_etiqueta, fg_color="transparent")
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(container, fg_color=PANEL, corner_radius=18, border_width=1, border_color=BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_columnconfigure(1, weight=1)

        right = ctk.CTkFrame(container, fg_color=PANEL, corner_radius=18, border_width=1, border_color=BORDER)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Dados da etiqueta", text_color=TEXT,
                     font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2,
                                                                    padx=14, pady=(14, 10), sticky="w")

        def field(row, label, var, values_key=None):
            ctk.CTkLabel(left, text=label, text_color=MUTED).grid(row=row, column=0, padx=14, pady=10, sticky="w")
            entry = ctk.CTkEntry(
                left, textvariable=var,
                fg_color=PANEL2, border_color=ACCENT, text_color=TEXT,
                corner_radius=12, height=36,
            )
            entry.grid(row=row, column=1, padx=14, pady=10, sticky="ew")

            menu = None
            if values_key:
                menu = ctk.CTkOptionMenu(
                    left, values=self.app_state.get(values_key, []),
                    variable=var,
                    fg_color=PANEL2, button_color=ACCENT, button_hover_color=ACCENT_HOVER,
                    dropdown_fg_color=PANEL2, dropdown_hover_color="#0F2648",
                    text_color=TEXT, corner_radius=12,
                )
                menu.grid(row=row + 1, column=1, padx=14, pady=(0, 10), sticky="ew")
            return entry, menu

        _, self.de_menu = field(1, "De (Emissor):", self.de_var, "emitentes")
        _, self.para_menu = field(3, "Para (Destinatário):", self.para_var, "destinatarios")
        _, self.cidade_menu = field(5, "Cidade - UF:", self.cidade_var, "cidades_uf")
        field(7, "Nº Nota Fiscal:", self.nf_var, None)
        field(8, "Nº Transportadora:", self.num_transp_var, None)
        _, self.transportadora_menu = field(9, "Transportadora:", self.transportadora_var, "transportadoras")

        size_box = ctk.CTkFrame(left, fg_color="transparent")
        size_box.grid(row=11, column=0, columnspan=2, sticky="ew", padx=14, pady=(4, 10))
        size_box.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(size_box, text="Tamanho (mm):", text_color=MUTED).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.size_menu = ctk.CTkOptionMenu(
            size_box,
            values=list(self.size_map.keys()),
            variable=self.size_var,
            fg_color=PANEL2,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            dropdown_fg_color=PANEL2,
            dropdown_hover_color="#0F2648",
            text_color=TEXT,
            corner_radius=12,
            command=lambda *_: self.on_size_change(),
        )
        self.size_menu.grid(row=0, column=1, sticky="ew")

        self.custom_size_row = ctk.CTkFrame(left, fg_color="transparent")
        self.custom_size_row.grid(row=12, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 10))
        self.custom_size_row.grid_columnconfigure(0, weight=1)
        self.custom_size_row.grid_columnconfigure(1, weight=1)

        self.custom_w_entry = ctk.CTkEntry(
            self.custom_size_row, textvariable=self.custom_w_var,
            placeholder_text="Largura (mm)",
            fg_color=PANEL2, border_color=ACCENT, text_color=TEXT,
            corner_radius=12, height=36
        )
        self.custom_h_entry = ctk.CTkEntry(
            self.custom_size_row, textvariable=self.custom_h_var,
            placeholder_text="Altura (mm)",
            fg_color=PANEL2, border_color=ACCENT, text_color=TEXT,
            corner_radius=12, height=36
        )
        self.custom_w_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.custom_h_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        pp_box = ctk.CTkFrame(left, fg_color="transparent")
        pp_box.grid(row=13, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))
        pp_box.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(pp_box, text="Etiquetas por folha:", text_color=MUTED).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.pp_menu = ctk.CTkOptionMenu(
            pp_box,
            values=list(self.per_page_map.keys()),
            variable=self.per_page_var,
            fg_color=PANEL2,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            dropdown_fg_color=PANEL2,
            dropdown_hover_color="#0F2648",
            text_color=TEXT,
            corner_radius=12,
        )
        self.pp_menu.grid(row=0, column=1, sticky="ew")

        quick = ctk.CTkFrame(left, fg_color="transparent")
        quick.grid(row=14, column=0, columnspan=2, sticky="ew", padx=14, pady=(6, 14))
        quick.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            quick,
            text="Salvar opções digitadas (De/Para/Cidade/Transportadora)",
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            corner_radius=12,
            height=40,
            command=self.save_typed_options,
        ).grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(right, text="Folha (A4) — etiquetas diferentes", text_color=TEXT,
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=14, pady=(14, 8))
        ctk.CTkLabel(right, text="Agora a etiqueta ocupa o espaço real e não extravasa.",
                     text_color=MUTED).pack(anchor="w", padx=14, pady=(0, 10))

        self.sheet_frame = ctk.CTkScrollableFrame(right, fg_color=PANEL2, corner_radius=14)
        self.sheet_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 10))
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_row, text="➕ Adicionar à folha",
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            corner_radius=12, height=40,
            command=self.add_to_sheet
        ).grid(row=0, column=0, padx=(0, 8), sticky="ew")

        ctk.CTkButton(
            btn_row, text="🧹 Limpar folha",
            fg_color="#3A1C24", hover_color="#5A2B36",
            corner_radius=12, height=40,
            command=self.clear_sheet
        ).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        btn_row2 = ctk.CTkFrame(right, fg_color="transparent")
        btn_row2.pack(fill="x", padx=14, pady=(0, 10))
        btn_row2.grid_columnconfigure(0, weight=1)
        btn_row2.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_row2, text="👁 Pré-visualizar (A4)",
            fg_color=PANEL, hover_color="#0F2648",
            border_width=1, border_color=ACCENT,
            corner_radius=12, height=40,
            command=self.preview_sheet
        ).grid(row=0, column=0, padx=(0, 8), sticky="ew")

        ctk.CTkButton(
            btn_row2, text="📄 Gerar PDF (A4)",
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            corner_radius=12, height=40,
            command=self.export_pdf_sheet
        ).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        self.refresh_option_menus()
        self.on_size_change()
        self.refresh_sheet_ui()

    def on_size_change(self):
        if self.size_var.get() == "Personalizado":
            self.custom_size_row.grid()
        else:
            self.custom_size_row.grid_remove()

    def save_typed_options(self):
        self.app_state["emitentes"] = uniq_add(self.app_state.get("emitentes", []), self.de_var.get())
        self.app_state["destinatarios"] = uniq_add(self.app_state.get("destinatarios", []), self.para_var.get())
        self.app_state["cidades_uf"] = uniq_add(self.app_state.get("cidades_uf", []), self.cidade_var.get())
        self.app_state["transportadoras"] = uniq_add(self.app_state.get("transportadoras", []), self.transportadora_var.get())
        self.save_now()
        self.refresh_option_menus()
        messagebox.showinfo("Salvo", "Opções salvas no cadastro para uso futuro.")

    def current_label_data(self) -> dict:
        return {
            "de": self.de_var.get().strip(),
            "para": self.para_var.get().strip(),
            "cidade_uf": self.cidade_var.get().strip(),
            "nf": self.nf_var.get().strip(),
            "num_transportadora": self.num_transp_var.get().strip(),
            "transportadora": self.transportadora_var.get().strip(),
        }

    def get_label_size_mm(self) -> tuple[float, float]:
        key = self.size_var.get()
        if key != "Personalizado":
            return self.size_map[key]

        try:
            w = float((self.custom_w_var.get() or "").replace(",", "."))
            h = float((self.custom_h_var.get() or "").replace(",", "."))
        except ValueError:
            raise ValueError("Informe largura e altura (mm) para o tamanho personalizado.")

        if w <= 0 or h <= 0:
            raise ValueError("Largura/Altura devem ser maiores que zero.")
        if w > 300 or h > 300:
            raise ValueError("Tamanho muito grande para sulfite A4.")
        return w, h

    def add_to_sheet(self):
        d = self.current_label_data()
        if not (d["de"] or d["para"] or d["nf"]):
            messagebox.showwarning("Atenção", "Preencha pelo menos DE ou PARA ou NF antes de adicionar.")
            return
        self.sheet_labels.append(d)
        self.refresh_sheet_ui()

    def remove_from_sheet(self, index: int):
        if 0 <= index < len(self.sheet_labels):
            self.sheet_labels.pop(index)
            self.refresh_sheet_ui()

    def clear_sheet(self):
        self.sheet_labels.clear()
        self.refresh_sheet_ui()

    def refresh_sheet_ui(self):
        for w in self.sheet_frame.winfo_children():
            w.destroy()

        if not self.sheet_labels:
            ctk.CTkLabel(self.sheet_frame, text="(nenhuma etiqueta adicionada)", text_color=MUTED).pack(anchor="w", pady=10, padx=10)
            return

        for i, d in enumerate(self.sheet_labels, start=1):
            row = ctk.CTkFrame(self.sheet_frame, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=6)
            row.grid_columnconfigure(0, weight=1)

            txt = f"{i}) PARA: {d.get('para','')} | NF: {d.get('nf','')} | CIDADE: {d.get('cidade_uf','')}"
            ctk.CTkLabel(row, text=txt, text_color=TEXT, wraplength=380, justify="left").grid(row=0, column=0, sticky="w")

            ctk.CTkButton(
                row, text="Remover",
                fg_color="#3A1C24", hover_color="#5A2B36",
                corner_radius=10, height=30, width=90,
                command=lambda idx=i-1: self.remove_from_sheet(idx)
            ).grid(row=0, column=1, padx=(10, 0), sticky="e")

    def export_pdf_sheet(self):
        if not self.sheet_labels:
            messagebox.showwarning("Atenção", "Adicione pelo menos 1 etiqueta na folha.")
            return

        path = filedialog.asksaveasfilename(
            title="Salvar PDF (A4) com etiquetas diferentes",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if not path:
            return

        try:
            label_w, label_h = self.get_label_size_mm()
            per_page = self.per_page_map[self.per_page_var.get()]

            make_labels_pdf_a4_multi(
                labels=self.sheet_labels,
                logo_path=(LOGO_FILE if LOGO_FILE.exists() else None),
                out_path=Path(path),
                label_w_mm=label_w,
                label_h_mm=label_h,
                per_page=per_page
            )
            messagebox.showinfo("OK", "PDF gerado! (múltiplas páginas se necessário)")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar PDF:\n{e}")

    def preview_sheet(self):
        if not self.sheet_labels:
            messagebox.showwarning("Atenção", "Adicione pelo menos 1 etiqueta para pré-visualizar.")
            return

        try:
            label_w, label_h = self.get_label_size_mm()
            per_page = self.per_page_map[self.per_page_var.get()]
            img = make_preview_a4_image(self.sheet_labels, label_w, label_h, per_page)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha na pré-visualização:\n{e}")
            return

        top = Toplevel(self)
        top.title("Pré-visualização (A4)")
        top.geometry("820x980")

        # ícone no toplevel também
        top.after(0, lambda: apply_icon(top))
        top.after(200, lambda: apply_icon(top))

        canvas_widget = Canvas(top, bg="white")
        vbar = Scrollbar(top, orient="vertical", command=canvas_widget.yview)
        hbar = Scrollbar(top, orient="horizontal", command=canvas_widget.xview)

        canvas_widget.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

        vbar.pack(side="right", fill="y")
        hbar.pack(side="bottom", fill="x")
        canvas_widget.pack(side="left", fill="both", expand=True)

        tk_img = ImageTk.PhotoImage(img)
        img_id = canvas_widget.create_image(0, 0, image=tk_img, anchor="nw")
        canvas_widget.image = tk_img
        canvas_widget.config(scrollregion=canvas_widget.bbox(img_id))

    # ---------- Logo / Cadastro ----------
    def _build_logo(self):
        wrap = ctk.CTkFrame(self.tab_logo, fg_color=PANEL, corner_radius=18, border_width=1, border_color=BORDER)
        wrap.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(wrap, text="Logo da etiqueta", text_color=TEXT,
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=14, pady=(14, 10))
        ctk.CTkLabel(wrap, text="Selecione uma imagem. O app salva uma cópia para usar sempre.",
                     text_color=MUTED).pack(anchor="w", padx=14, pady=(0, 12))

        btns = ctk.CTkFrame(wrap, fg_color="transparent")
        btns.pack(fill="x", padx=14, pady=(0, 14))
        btns.grid_columnconfigure(0, weight=1)
        btns.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            btns, text="Escolher logo",
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            corner_radius=12, height=44, command=self.pick_logo
        ).grid(row=0, column=0, padx=(0, 8), sticky="ew")

        ctk.CTkButton(
            btns, text="Remover logo",
            fg_color="#3A1C24", hover_color="#5A2B36",
            corner_radius=12, height=44, command=self.remove_logo
        ).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        self.logo_preview = ctk.CTkLabel(wrap, text="(sem logo)", text_color=MUTED, justify="left")
        self.logo_preview.pack(anchor="w", padx=14, pady=(0, 14))
        self.update_logo_preview()

    def pick_logo(self):
        path = filedialog.askopenfilename(
            title="Selecione a logo",
            filetypes=[("Imagens", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")],
        )
        if not path:
            return
        try:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            img = Image.open(path).convert("RGBA")
            img.save(LOGO_FILE, "PNG")
            self.update_logo_preview()
            messagebox.showinfo("OK", f"Logo salva em:\n{LOGO_FILE}")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível salvar a logo:\n{e}")

    def remove_logo(self):
        try:
            if LOGO_FILE.exists():
                LOGO_FILE.unlink()
        except Exception:
            pass
        self.update_logo_preview()

    def update_logo_preview(self):
        if LOGO_FILE.exists():
            self.logo_preview.configure(text=f"Logo atual: {LOGO_FILE.name}\nLocal: {LOGO_FILE}", text_color=TEXT)
        else:
            self.logo_preview.configure(text="(sem logo)", text_color=MUTED)

    def _build_cadastro(self):
        container = ctk.CTkFrame(self.tab_cadastro, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)

        emit = CadastroList(
            container, "Cadastro — Emitentes (DE)",
            get_items=lambda: self.app_state.get("emitentes", []),
            set_items=lambda items: self.set_list("emitentes", items),
        )
        emit.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))

        dest = CadastroList(
            container, "Cadastro — Destinatários (PARA)",
            get_items=lambda: self.app_state.get("destinatarios", []),
            set_items=lambda items: self.set_list("destinatarios", items),
        )
        dest.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=(0, 10))

        transp = CadastroList(
            container, "Cadastro — Transportadoras",
            get_items=lambda: self.app_state.get("transportadoras", []),
            set_items=lambda items: self.set_list("transportadoras", items),
        )
        transp.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(10, 0))

        cities = CadastroList(
            container, "Cadastro — Cidades/UF (ex: Goiânia - GO)",
            get_items=lambda: self.app_state.get("cidades_uf", []),
            set_items=lambda items: self.set_list("cidades_uf", items),
        )
        cities.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(10, 0))

        self.refresh_option_menus()

    def on_close(self):
        self.app_state["last_de"] = self.de_var.get()
        self.app_state["last_para"] = self.para_var.get()
        self.app_state["last_cidade_uf"] = self.cidade_var.get()
        self.app_state["last_nf"] = self.nf_var.get()
        self.app_state["last_num_transportadora"] = self.num_transp_var.get()
        self.app_state["last_transportadora"] = self.transportadora_var.get()

        self.app_state["last_size"] = self.size_var.get()
        self.app_state["last_custom_w"] = self.custom_w_var.get()
        self.app_state["last_custom_h"] = self.custom_h_var.get()
        self.app_state["last_per_page"] = self.per_page_var.get()

        self.save_now()
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()