#!/usr/bin/env python3
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
import tkinter as tk
from tkinter import filedialog, font, messagebox, scrolledtext, simpledialog

META_FILENAME = ".pegy_meta.json"
EXTS = {".txt", ".pdf", ".peg"}
APP_VERSION = "2.3"

LIGHT_THEME = {
    "bg": "#f4ead7",
    "bg2": "#efe2c9",
    "panel": "#f7efdf",
    "text_bg": "#fffaf2",
    "text_fg": "#3d3128",
    "muted": "#8b7b6b",
    "border": "#d6c3a5",
    "button_bg": "#ecd8b8",
    "button_hover": "#e2c89f",
    "button_fg": "#3c2f25",
    "entry_bg": "#fff8ee",
}

DARK_THEME = {
    "bg": "#3e2f25",
    "bg2": "#453428",
    "panel": "#4d3a2d",
    "text_bg": "#2f241d",
    "text_fg": "#f3e6d4",
    "muted": "#d6c3a5",
    "border": "#6a5543",
    "button_bg": "#5a4637",
    "button_hover": "#6b5543",
    "button_fg": "#f3e6d4",
    "entry_bg": "#3a2c23",
}

THEME = dict(LIGHT_THEME)
CURRENT_THEME = "light"

if getattr(sys, "frozen", False):
    ORIGINAL_BASE_FOLDER = os.path.dirname(sys.executable)
else:
    ORIGINAL_BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))

CURRENT_FOLDER = os.path.abspath(ORIGINAL_BASE_FOLDER)
CURRENT_FILTER_TEXT = ""
EDITOR_LOADING = False
SEARCH_LOADING = False

root = tk.Tk()
root.title("Notepegy - Arquivos da Pasta")
root.geometry("700x520")
root.minsize(600, 420)

def apply_theme_defaults(tk_root):
    tk_root.configure(bg=THEME["bg"])
    tk_root.option_add("*Background", THEME["bg"])
    tk_root.option_add("*Foreground", THEME["text_fg"])
    tk_root.option_add("*Frame.Background", THEME["bg"])
    tk_root.option_add("*Label.Background", THEME["bg"])
    tk_root.option_add("*Label.Foreground", THEME["text_fg"])
    tk_root.option_add("*Button.Background", THEME["button_bg"])
    tk_root.option_add("*Button.Foreground", THEME["button_fg"])
    tk_root.option_add("*Button.ActiveBackground", THEME["button_hover"])
    tk_root.option_add("*Button.ActiveForeground", THEME["button_fg"])
    tk_root.option_add("*Button.BorderWidth", 1)
    tk_root.option_add("*Button.Relief", "flat")
    tk_root.option_add("*Button.HighlightThickness", 0)
    tk_root.option_add("*Button.Padx", 10)
    tk_root.option_add("*Button.Pady", 4)
    tk_root.option_add("*Entry.Background", THEME["entry_bg"])
    tk_root.option_add("*Entry.Foreground", THEME["text_fg"])
    tk_root.option_add("*Entry.Relief", "flat")
    tk_root.option_add("*Entry.HighlightThickness", 1)
    tk_root.option_add("*Entry.HighlightColor", THEME["border"])
    tk_root.option_add("*Entry.HighlightBackground", THEME["border"])
    tk_root.option_add("*Text.Background", THEME["text_bg"])
    tk_root.option_add("*Text.Foreground", THEME["text_fg"])
    tk_root.option_add("*Text.Relief", "flat")
    tk_root.option_add("*Text.HighlightThickness", 1)
    tk_root.option_add("*Text.HighlightColor", THEME["border"])
    tk_root.option_add("*Text.HighlightBackground", THEME["border"])

apply_theme_defaults(root)

class Tooltip:
    def __init__(self, widget, text, delay=700):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._after_id = None
        self.tip = None
        widget.bind("<Enter>", self._schedule, add=True)
        widget.bind("<Leave>", self._hide, add=True)
        widget.bind("<ButtonPress>", self._hide, add=True)

    def _schedule(self, event=None):
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self):
        if self.tip or not self.widget.winfo_exists():
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        try:
            self.tip.wm_attributes("-topmost", True)
        except Exception:
            pass
        self.tip.configure(bg=THEME["panel"])
        label = tk.Label(
            self.tip,
            text=self.text,
            bg=THEME["panel"],
            fg=THEME["text_fg"],
            font=font.Font(size=8),
            padx=6,
            pady=3,
            relief="solid",
            bd=1,
        )
        label.pack()
        self.tip.wm_geometry(f"+{x}+{y}")

    def _hide(self, event=None):
        self._cancel()
        if self.tip:
            try:
                self.tip.destroy()
            except Exception:
                pass
            self.tip = None

TOOLTIP_TEXTS = {
    "☀": "Tema claro (bege)",
    "☾": "Tema escuro (bege escuro)",
    "↑": "Encontrar anterior",
    "↓": "Encontrar próximo",
    "✕": "Fechar busca",
    "✖": "Fechar busca",
    "←": "Voltar para a lista",
    "← Voltar": "Voltar para pasta acima",
    "Ir para menu": "Ir para a pasta inicial",
    "Explorar": "Escolher outra pasta",
    "Novo": "Criar novo arquivo",
    "Nova pasta": "Criar nova pasta",
    "Abrir": "Abrir item",
    "Fechar": "Fechar janela",
    "Mover": "Mover arquivo para outra pasta",
    "ℹ": "Ver informações",
    "🗑": "Deletar",
    "🔍": "Buscar no texto",
    "Exportar": "Exportar arquivo",
    "Salvar": "Salvar arquivo",
    "Salvar como...": "Salvar com outro nome",
    "Salvar na pasta": "Salvar na pasta atual",
    "Cancelar": "Cancelar",
}

APP_FONT = font.Font(family="Segoe UI", size=10)

main_frame = tk.Frame(root)
editor_frame = tk.Frame(root)

file_list_container = None
path_entry = None
btn_back = None
btn_menu = None

global_status = tk.Label(root, text="Pronto", anchor="w", relief="flat", bg=THEME["panel"], fg=THEME["text_fg"])
global_status.pack(fill="x", side="bottom")

theme_bar = tk.Frame(root, bg=THEME["bg"])
btn_theme_light = tk.Button(theme_bar, text="☀", width=2, height=1, cursor="hand2")
btn_theme_dark = tk.Button(theme_bar, text="☾", width=2, height=1, cursor="hand2")
version_lbl = tk.Label(theme_bar, text=f"versão {APP_VERSION}", font=font.Font(size=8), fg=THEME["muted"], bg=THEME["bg"])

version_lbl.pack(side="right", padx=(6, 0))
btn_theme_dark.pack(side="right", padx=(4, 0))
btn_theme_light.pack(side="right", padx=(4, 2))
theme_bar.place(relx=0.98, rely=0.01, anchor="ne")

displayed_rows = []
current_files = []

current_editor_state = {
    "mode": None,
    "original_path": None,
    "dirty": False,
    "saved_snapshot": "",
}

search_state = {
    "query": "",
    "matches": [],
    "current_index": -1,
}

editor_top = tk.Frame(editor_frame, bg=THEME["bg2"])
editor_area = tk.Frame(editor_frame, bg=THEME["bg"])
text_widget = scrolledtext.ScrolledText(editor_area, wrap="word", font=APP_FONT, undo=True)
text_widget.config(
    bg=THEME["text_bg"],
    fg=THEME["text_fg"],
    insertbackground=THEME["text_fg"],
    relief="flat",
    highlightthickness=1,
    highlightbackground=THEME["border"],
    highlightcolor=THEME["border"],
)
status_line = tk.Label(editor_frame, text="Caracteres: 0  Palavras: 0  Linha: 1 Col: 0", anchor="w", font=font.Font(size=9), bg=THEME["panel"])
editor_buttons = tk.Frame(editor_frame, bg=THEME["bg"])

find_bar = tk.Frame(editor_frame, relief="groove", bd=1, bg=THEME["panel"])
find_entry = tk.Entry(find_bar, width=30)
find_count_lbl = tk.Label(find_bar, text="0/0", width=8, anchor="w", bg=THEME["panel"])
find_prev_btn = tk.Button(find_bar, text="↑", width=3, cursor="hand2")
find_next_btn = tk.Button(find_bar, text="↓", width=3, cursor="hand2")
find_close_btn = tk.Button(find_bar, text="✕", width=3, cursor="hand2")

title_lbl = tk.Label(editor_top, text="Nenhum arquivo", font=font.Font(size=11, weight="bold"), bg=THEME["bg2"])
btn_save = tk.Button(editor_buttons, text="Salvar", width=12, cursor="hand2")
btn_save_as = tk.Button(editor_buttons, text="Salvar como...", width=12, cursor="hand2")
btn_save_to_folder = tk.Button(editor_buttons, text="Salvar na pasta", width=14, cursor="hand2")
btn_export = tk.Button(editor_buttons, text="Exportar", width=12, cursor="hand2")

_CANVAS = None
_CANVAS_MOUSE_BINDINGS = []
_SCROLLBAR = None

def set_global_status(text):
    global_status.config(text=text)

def _tooltip_text_for_button(btn):
    try:
        text = btn.cget("text")
    except Exception:
        return None
    if not text:
        return None
    text = str(text).strip()
    if not text:
        return None
    return TOOLTIP_TEXTS.get(text, text)

def apply_tooltips(widget):
    for child in widget.winfo_children():
        if isinstance(child, tk.Button):
            if not getattr(child, "_has_tooltip", False):
                tip_text = _tooltip_text_for_button(child)
                if tip_text:
                    child._tooltip = Tooltip(child, tip_text)
                    child._has_tooltip = True
        apply_tooltips(child)

def _apply_theme_to_children(widget):
    for child in widget.winfo_children():
        try:
            if isinstance(child, tk.Frame):
                child.config(bg=THEME["bg"])
            elif isinstance(child, tk.Label):
                child.config(bg=THEME["bg"], fg=THEME["text_fg"])
            elif isinstance(child, tk.Button):
                child.config(
                    bg=THEME["button_bg"],
                    fg=THEME["button_fg"],
                    activebackground=THEME["button_hover"],
                    activeforeground=THEME["button_fg"],
                )
            elif isinstance(child, tk.Entry):
                child.config(
                    bg=THEME["entry_bg"],
                    fg=THEME["text_fg"],
                    highlightbackground=THEME["border"],
                    highlightcolor=THEME["border"],
                )
            elif isinstance(child, tk.Canvas):
                child.config(bg=THEME["bg"], highlightbackground=THEME["bg"])
            elif isinstance(child, tk.Scrollbar):
                child.config(troughcolor=THEME["panel"])
            elif isinstance(child, tk.Text):
                child.config(
                    bg=THEME["text_bg"],
                    fg=THEME["text_fg"],
                    insertbackground=THEME["text_fg"],
                    highlightbackground=THEME["border"],
                    highlightcolor=THEME["border"],
                )
        except Exception:
            pass
        _apply_theme_to_children(child)

def apply_theme_to_widgets():
    apply_theme_defaults(root)
    root.configure(bg=THEME["bg"])
    theme_bar.config(bg=THEME["bg"])
    version_lbl.config(bg=THEME["bg"], fg=THEME["muted"])
    global_status.config(bg=THEME["panel"], fg=THEME["text_fg"])
    main_frame.config(bg=THEME["bg"])
    editor_frame.config(bg=THEME["bg"])

    _apply_theme_to_children(main_frame)
    _apply_theme_to_children(editor_frame)

    editor_top.config(bg=THEME["bg2"])
    editor_area.config(bg=THEME["bg"])
    editor_buttons.config(bg=THEME["bg"])
    status_line.config(bg=THEME["panel"], fg=THEME["text_fg"])
    find_bar.config(bg=THEME["panel"])
    find_count_lbl.config(bg=THEME["panel"], fg=THEME["text_fg"])
    title_lbl.config(bg=THEME["bg2"], fg=THEME["text_fg"])
    text_widget.config(
        bg=THEME["text_bg"],
        fg=THEME["text_fg"],
        insertbackground=THEME["text_fg"],
        highlightbackground=THEME["border"],
        highlightcolor=THEME["border"],
    )
    btn_theme_light.config(
        bg=THEME["button_bg"],
        fg=THEME["button_fg"],
        activebackground=THEME["button_hover"],
        activeforeground=THEME["button_fg"],
        relief="sunken" if CURRENT_THEME == "light" else "flat",
    )
    btn_theme_dark.config(
        bg=THEME["button_bg"],
        fg=THEME["button_fg"],
        activebackground=THEME["button_hover"],
        activeforeground=THEME["button_fg"],
        relief="sunken" if CURRENT_THEME == "dark" else "flat",
    )
    if _CANVAS is not None:
        _CANVAS.config(bg=THEME["bg"], highlightbackground=THEME["bg"])
    if _SCROLLBAR is not None:
        _SCROLLBAR.config(troughcolor=THEME["panel"])
    if file_list_container is not None:
        file_list_container.config(bg=THEME["bg"])
    if path_entry is not None:
        path_entry.config(
            bg=THEME["entry_bg"],
            fg=THEME["text_fg"],
            highlightbackground=THEME["border"],
            highlightcolor=THEME["border"],
        )
    if find_entry is not None:
        find_entry.config(
            bg=THEME["entry_bg"],
            fg=THEME["text_fg"],
            highlightbackground=THEME["border"],
            highlightcolor=THEME["border"],
        )

def set_theme(mode):
    global THEME, CURRENT_THEME
    if mode == CURRENT_THEME:
        return
    if mode == "dark":
        THEME = dict(DARK_THEME)
        CURRENT_THEME = "dark"
    else:
        THEME = dict(LIGHT_THEME)
        CURRENT_THEME = "light"
    apply_theme_to_widgets()

def clear_frame(frame):
    for w in frame.winfo_children():
        w.destroy()

def safe_abs(path):
    return os.path.abspath(path) if path else path

def same_folder(a, b):
    try:
        return os.path.abspath(a) == os.path.abspath(b)
    except Exception:
        return False

def is_inside_folder(path, folder):
    try:
        path = os.path.abspath(path)
        folder = os.path.abspath(folder)
        return os.path.commonpath([path, folder]) == folder
    except Exception:
        return False

def abrir_com_padrao(caminho):
    try:
        if sys.platform.startswith("win"):
            os.startfile(caminho)  # type: ignore[attr-defined]
        else:
            opener = "xdg-open" if sys.platform.startswith("linux") else "open"
            subprocess.Popen([opener, caminho])
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível abrir o arquivo:\n{e}")

def meta_path(folder):
    return os.path.join(folder, META_FILENAME)

def load_meta(folder):
    path = meta_path(folder)
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}

def save_meta(folder, data):
    path = meta_path(folder)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def ensure_meta_for_file(folder, filename):
    folder = safe_abs(folder)
    data = load_meta(folder)
    if filename not in data:
        caminho = os.path.join(folder, filename)
        try:
            ctime = os.path.getctime(caminho)
        except Exception:
            ctime = time.time()
        data[filename] = {"created": int(ctime)}
        save_meta(folder, data)

def get_created_time(folder, filename):
    folder = safe_abs(folder)
    data = load_meta(folder)
    if filename in data and isinstance(data[filename], dict) and "created" in data[filename]:
        return data[filename]["created"]
    caminho = os.path.join(folder, filename)
    try:
        return int(os.path.getctime(caminho))
    except Exception:
        return int(time.time())

def read_text_any(caminho):
    try:
        with open(caminho, "rb") as f:
            raw = f.read()
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return raw.decode("latin-1")
            except Exception:
                return raw.decode("utf-8", errors="replace")
    except Exception:
        return None

def current_text():
    return text_widget.get("1.0", "end-1c")

def sync_dirty_state(event=None):
    global EDITOR_LOADING
    if EDITOR_LOADING:
        try:
            text_widget.edit_modified(False)
        except Exception:
            pass
        return
    dirty = current_text() != current_editor_state.get("saved_snapshot", "")
    current_editor_state["dirty"] = dirty
    update_status_counts()
    refresh_find_highlights()
    try:
        text_widget.edit_modified(False)
    except Exception:
        pass

def update_status_counts(event=None):
    txt = current_text()
    chars = len(txt)
    words = len(txt.split())
    try:
        idx = text_widget.index("insert")
        line, col = idx.split(".")
    except Exception:
        line, col = "1", "0"
    status_line.config(text=f"Caracteres: {chars}  Palavras: {words}  Linha: {line} Col: {col}")

def set_snapshot_and_clean(text_value):
    current_editor_state["saved_snapshot"] = text_value
    current_editor_state["dirty"] = False
    try:
        text_widget.edit_modified(False)
    except Exception:
        pass

def confirm_discard_changes():
    if current_text() == current_editor_state.get("saved_snapshot", ""):
        current_editor_state["dirty"] = False
        return True
    current_editor_state["dirty"] = True
    r = messagebox.askyesnocancel("Salvar alterações?", "O arquivo atual não foi salvo. Deseja salvar antes de continuar?")
    if r is None:
        return None
    if r:
        saved = action_save()
        return True if saved is True else False
    return True

def refresh_find_counts():
    total = len(search_state["matches"])
    if total == 0:
        find_count_lbl.config(text="0/0")
    else:
        idx = search_state["current_index"]
        find_count_lbl.config(text=f"{idx + 1}/{total}")

def clear_search_tags():
    text_widget.tag_remove("search_match", "1.0", tk.END)
    text_widget.tag_remove("search_current", "1.0", tk.END)

def refresh_find_highlights(event=None):
    clear_search_tags()
    query = search_state["query"].strip()
    search_state["matches"] = []
    search_state["current_index"] = -1
    if not query:
        refresh_find_counts()
        return

    start = "1.0"
    qlen = len(query)
    while True:
        idx = text_widget.search(query, start, stopindex=tk.END, nocase=True)
        if not idx:
            break
        end = f"{idx}+{qlen}c"
        search_state["matches"].append((idx, end))
        text_widget.tag_add("search_match", idx, end)
        start = end

    if search_state["matches"]:
        search_state["current_index"] = 0
        idx, end = search_state["matches"][0]
        text_widget.tag_add("search_current", idx, end)
        text_widget.mark_set("insert", idx)
        text_widget.see(idx)

    refresh_find_counts()

def goto_match(index):
    total = len(search_state["matches"])
    if total == 0:
        refresh_find_counts()
        return
    index %= total
    search_state["current_index"] = index
    clear_search_tags()
    for i, (start, end) in enumerate(search_state["matches"]):
        text_widget.tag_add("search_match", start, end)
        if i == index:
            text_widget.tag_add("search_current", start, end)
            text_widget.mark_set("insert", start)
            text_widget.see(start)
    refresh_find_counts()

def find_next(event=None):
    if not search_state["matches"]:
        refresh_find_highlights()
        return "break"
    goto_match(search_state["current_index"] + 1)
    return "break"

def find_prev(event=None):
    if not search_state["matches"]:
        refresh_find_highlights()
        return "break"
    goto_match(search_state["current_index"] - 1)
    return "break"

def show_find_bar(initial_query=""):
    if find_bar.winfo_ismapped():
        find_entry.focus_set()
        return
    if not initial_query:
        try:
            initial_query = text_widget.selection_get()
        except Exception:
            initial_query = search_state.get("query", "")
    find_entry.delete(0, tk.END)
    find_entry.insert(0, initial_query or search_state.get("query", ""))
    find_bar.pack(fill="x", padx=8, pady=(4, 0), before=editor_area)
    find_entry.focus_set()
    find_entry.selection_range(0, tk.END)
    search_state["query"] = find_entry.get()
    refresh_find_highlights()

def hide_find_bar(event=None):
    if find_bar.winfo_ismapped():
        find_bar.pack_forget()
        clear_search_tags()
    return "break"

def on_find_change(event=None):
    search_state["query"] = find_entry.get()
    refresh_find_highlights()

def on_find_enter(event=None):
    return find_next()

def open_any_text_file(caminho, from_folder_guess=None):
    if not os.path.exists(caminho):
        messagebox.showerror("Erro", f"Arquivo não encontrado:\n{caminho}")
        return
    caminho = safe_abs(caminho)
    _, ext = os.path.splitext(caminho)
    if ext.lower() == ".pdf":
        abrir_com_padrao(caminho)
        return

    texto = read_text_any(caminho)
    nome = os.path.basename(caminho)
    mode = "from_folder" if from_folder_guess or same_folder(os.path.dirname(caminho), CURRENT_FOLDER) else "external"
    open_editor_with_content(texto, nome, mode=mode, original_path=caminho)

def on_path_enter(event=None):
    typed = path_entry.get().strip()
    if not typed:
        return
    if not os.path.isabs(typed):
        typed = os.path.abspath(os.path.join(CURRENT_FOLDER, typed))
    typed = safe_abs(typed)
    if not os.path.isdir(typed):
        messagebox.showerror("Erro", f"Pasta inválida:\n{typed}")
        path_entry.delete(0, tk.END)
        path_entry.insert(0, CURRENT_FOLDER)
        return
    change_folder(typed)

def go_parent_folder():
    parent = os.path.dirname(os.path.abspath(CURRENT_FOLDER))
    if not parent or same_folder(parent, CURRENT_FOLDER):
        return
    change_folder(parent)

def go_original_menu():
    change_folder(ORIGINAL_BASE_FOLDER)

def refresh_file_list(filter_text=None):
    global file_list_container, path_entry, btn_back, btn_menu, displayed_rows, current_files, CURRENT_FILTER_TEXT, _CANVAS, _SCROLLBAR

    if filter_text is None:
        filter_text = CURRENT_FILTER_TEXT
    else:
        CURRENT_FILTER_TEXT = filter_text

    clear_frame(main_frame)
    displayed_rows = []
    current_files = []

    top_path = tk.Frame(main_frame)
    top_path.pack(fill="x", pady=6, padx=6)

    tk.Label(top_path, text="Pasta:", font=font.Font(size=10)).pack(side="left", padx=(0, 6))
    path_entry = tk.Entry(top_path, width=52)
    path_entry.pack(side="left", padx=(0, 6))
    path_entry.delete(0, tk.END)
    path_entry.insert(0, CURRENT_FOLDER)
    path_entry.bind("<Return>", on_path_enter)

    def explorar_pasta():
        escolhido = filedialog.askdirectory(initialdir=CURRENT_FOLDER or ORIGINAL_BASE_FOLDER, title="Escolher pasta")
        if escolhido:
            change_folder(escolhido)

    tk.Button(top_path, text="Explorar", command=explorar_pasta, cursor="hand2").pack(side="left", padx=(6, 4))

    btn_back = tk.Button(top_path, text="← Voltar", command=go_parent_folder, cursor="hand2")
    btn_back.pack(side="left", padx=(4, 4))
    btn_menu = tk.Button(top_path, text="Ir para menu", command=go_original_menu, cursor="hand2")
    btn_menu.pack(side="left", padx=(0, 0))

    if same_folder(CURRENT_FOLDER, ORIGINAL_BASE_FOLDER):
        btn_menu.config(state="disabled")
        btn_back.config(state="disabled")
    else:
        btn_menu.config(state="normal")
        btn_back.config(state="normal")

    top_buttons = tk.Frame(main_frame)
    top_buttons.pack(pady=6, anchor="w", padx=6)

    tk.Button(top_buttons, text="Novo", command=novo_arquivo, cursor="hand2").pack(side="left", padx=(0, 6))

    def create_new_folder_button_action():
        nome = simpledialog.askstring("Nova pasta", "Nome da nova pasta:", parent=root)
        if not nome:
            return
        nome = nome.strip()
        if not nome:
            return
        destino = os.path.join(CURRENT_FOLDER, nome)
        try:
            os.makedirs(destino, exist_ok=False)
            _ = load_meta(destino)
            set_global_status(f"Pasta '{nome}' criada")
            refresh_file_list()
        except FileExistsError:
            messagebox.showerror("Erro", "Já existe uma pasta com esse nome.")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível criar a pasta:\n{e}")

    tk.Button(top_buttons, text="Nova pasta", command=create_new_folder_button_action, cursor="hand2").pack(side="left", padx=(0, 6))
    tk.Button(top_buttons, text="Abrir", command=lambda: abrir_editavel(), cursor="hand2").pack(side="left")

    search_frame = tk.Frame(main_frame)
    search_frame.pack(fill="x", padx=6, pady=(8, 0))
    tk.Label(search_frame, text="Pesquisar (filtrar):", font=font.Font(size=10)).pack(side="left", padx=(0, 6))
    search_entry = tk.Entry(search_frame, width=40)
    search_entry.pack(side="left", padx=(0, 6))
    search_entry.delete(0, tk.END)
    search_entry.insert(0, CURRENT_FILTER_TEXT)

    def on_search_key(event=None):
        global CURRENT_FILTER_TEXT
        txt = search_entry.get().strip()
        CURRENT_FILTER_TEXT = txt
        build_file_rows(filter_text=txt)

    search_entry.bind("<KeyRelease>", on_search_key)

    tk.Label(main_frame, text="Itens na pasta", font=font.Font(size=12, weight="bold")).pack(pady=(8, 4))

    canvas = tk.Canvas(main_frame, highlightthickness=0, bg=THEME["bg"])
    scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview, troughcolor=THEME["panel"])
    file_list_container = tk.Frame(canvas, bg=THEME["bg"])

    file_list_container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=file_list_container, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
    scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

    _bind_canvas_scroll(canvas)
    _CANVAS = canvas
    _SCROLLBAR = scrollbar

    build_file_rows(filter_text=filter_text)
    apply_tooltips(main_frame)

def _bind_canvas_scroll(canvas):
    def _on_mousewheel(event):
        try:
            if event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass
        return "break"

    def _on_linux_up(event):
        canvas.yview_scroll(-1, "units")
        return "break"

    def _on_linux_down(event):
        canvas.yview_scroll(1, "units")
        return "break"

    try:
        root.bind_all("<MouseWheel>", _on_mousewheel)
        root.bind_all("<Button-4>", _on_linux_up)
        root.bind_all("<Button-5>", _on_linux_down)
    except Exception:
        pass

def change_folder(new_folder):
    global CURRENT_FOLDER
    if not new_folder:
        return
    CURRENT_FOLDER = safe_abs(new_folder)
    _ = load_meta(CURRENT_FOLDER)
    refresh_file_list()

def abrir_pasta_interna(caminho):
    caminho = safe_abs(caminho)
    if not os.path.isdir(caminho):
        messagebox.showinfo("Abrir", "Pasta não encontrada.")
        return
    change_folder(caminho)

def build_file_rows(filter_text=""):
    global file_list_container
    for w in file_list_container.winfo_children():
        w.destroy()

    try:
        entries = sorted(os.listdir(CURRENT_FOLDER))
    except Exception as e:
        messagebox.showerror("Erro", f"Não consegui listar a pasta:\n{e}")
        entries = []

    q = (filter_text or "").lower()
    items_shown = 0

    for nome in entries:
        if nome == META_FILENAME:
            continue
        caminho = os.path.join(CURRENT_FOLDER, nome)
        if os.path.isdir(caminho):
            if q and q not in nome.lower():
                continue

            row = tk.Frame(file_list_container, pady=2)
            row.pack(fill="x", padx=6, pady=3)

            tk.Label(row, text="📁", width=2).pack(side="left")

            lbl = tk.Label(row, text=nome, anchor="w", width=48, cursor="hand2")
            lbl.pack(side="left", padx=(0, 6))
            lbl.bind("<Double-Button-1>", lambda e, p=caminho: abrir_pasta_interna(p))

            def folder_info(n=nome):
                p = os.path.join(CURRENT_FOLDER, n)
                try:
                    total_size = 0
                    total_count = 0
                    for root_dir, dirs, files in os.walk(p):
                        total_count += len(files)
                        for f in files:
                            try:
                                total_size += os.path.getsize(os.path.join(root_dir, f))
                            except Exception:
                                pass
                    mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(p)))
                except Exception:
                    total_size = 0
                    total_count = 0
                    mtime = "?"
                created_ts = get_created_time(CURRENT_FOLDER, n)
                try:
                    ctime_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_ts))
                except Exception:
                    ctime_str = "?"

                dlg = tk.Toplevel(root)
                dlg.title("Informações da pasta")
                dlg.transient(root)
                dlg.resizable(False, False)

                tk.Label(dlg, text=f"Nome: {n}", anchor="w").pack(fill="x", padx=12, pady=(8, 4))
                frame = tk.Frame(dlg)
                frame.pack(fill="x", padx=12, pady=(0, 8))
                tk.Label(frame, text="Tamanho:", width=12, anchor="w").grid(row=0, column=0, sticky="w")
                tk.Label(frame, text=f"{total_size} bytes", anchor="w").grid(row=0, column=1, sticky="w")
                tk.Label(frame, text="Modificado:", width=12, anchor="w").grid(row=1, column=0, sticky="w")
                tk.Label(frame, text=mtime, anchor="w").grid(row=1, column=1, sticky="w")
                tk.Label(frame, text="Criado:", width=12, anchor="w").grid(row=2, column=0, sticky="w")
                tk.Label(frame, text=ctime_str, anchor="w").grid(row=2, column=1, sticky="w")
                tk.Label(frame, text="Arquivos dentro:", width=12, anchor="w").grid(row=3, column=0, sticky="w")
                tk.Label(frame, text=str(total_count), anchor="w").grid(row=3, column=1, sticky="w")

                btns = tk.Frame(dlg)
                btns.pack(fill="x", padx=12, pady=(0, 12))
                tk.Button(btns, text="Abrir", command=lambda: (dlg.destroy(), abrir_pasta_interna(p))).pack(side="right", padx=(6, 0))
                tk.Button(btns, text="Fechar", command=dlg.destroy).pack(side="right")
                apply_tooltips(dlg)

            tk.Button(row, text="ℹ", width=3, command=folder_info, cursor="hand2").pack(side="left", padx=(6, 4))
            tk.Button(row, text="Abrir", width=8, command=lambda p=caminho: abrir_pasta_interna(p), cursor="hand2").pack(side="left", padx=4)

            def delete_folder_action(n=nome):
                p = os.path.join(CURRENT_FOLDER, n)
                if not os.path.isdir(p):
                    messagebox.showinfo("Info", "Pasta não encontrada.")
                    refresh_file_list()
                    return
                if messagebox.askyesno("Confirmar", f"Deletar pasta '{n}' e todo o seu conteúdo?"):
                    try:
                        shutil.rmtree(p)
                        data = load_meta(CURRENT_FOLDER)
                        if n in data:
                            del data[n]
                            save_meta(CURRENT_FOLDER, data)
                        messagebox.showinfo("Deletado", f"Pasta '{n}' removida.")
                        refresh_file_list()
                    except Exception as e:
                        messagebox.showerror("Erro", f"Não consegui deletar a pasta:\n{e}")

            tk.Button(row, text="🗑", width=3, command=delete_folder_action, cursor="hand2").pack(side="left", padx=4)
            items_shown += 1

    for nome in entries:
        caminho = os.path.join(CURRENT_FOLDER, nome)
        if not os.path.isfile(caminho):
            continue
        _, ext = os.path.splitext(nome)
        if ext.lower() not in EXTS:
            continue
        if q and q not in nome.lower():
            continue

        row = tk.Frame(file_list_container, pady=2)
        row.pack(fill="x", padx=6, pady=3)

        icon = "📄" if ext.lower() in {".txt", ".peg"} else "📦"
        tk.Label(row, text=icon, width=2).pack(side="left")

        lbl = tk.Label(row, text=nome, anchor="w", width=40, cursor="hand2")
        lbl.pack(side="left", padx=(0, 6))
        lbl.bind("<Double-Button-1>", lambda e, n=nome: open_file_from_list(n))

        def mover_para_pasta(n=nome):
            try:
                entries2 = sorted(os.listdir(CURRENT_FOLDER))
            except Exception:
                entries2 = []
            dirs = [d for d in entries2 if os.path.isdir(os.path.join(CURRENT_FOLDER, d))]
            parent_dir = os.path.dirname(os.path.abspath(CURRENT_FOLDER))
            include_parent = parent_dir and os.path.isdir(parent_dir) and not same_folder(parent_dir, CURRENT_FOLDER)
            if not dirs and not include_parent:
                messagebox.showinfo("Mover", "Não há pastas para mover. Crie uma nova pasta primeiro.")
                return

            dlg = tk.Toplevel(root)
            dlg.title("Mover")
            dlg.transient(root)
            dlg.geometry("380x280")
            tk.Label(dlg, text=f"Mover '{n}' para:", anchor="w").pack(fill="x", padx=12, pady=(12, 6))

            btns_frame = tk.Frame(dlg)
            btns_frame.pack(fill="both", expand=True, padx=12, pady=(0, 6))

            def make_move_button(folder_name, special=False):
                def _move():
                    dlg.destroy()
                    move_file_to_folder(n, folder_name)
                kwargs = {"text": folder_name, "width": 32, "command": _move, "cursor": "hand2"}
                if special:
                    kwargs.update({"bg": "#dbeafe", "activebackground": "#bfdbfe", "relief": "raised"})
                return tk.Button(btns_frame, **kwargs)

            if include_parent:
                b = make_move_button(parent_dir, special=True)
                b.pack(pady=3)

            for d in dirs:
                if os.path.abspath(os.path.join(CURRENT_FOLDER, d)) == parent_dir:
                    continue
                b = make_move_button(d)
                b.pack(pady=3)

            tk.Button(dlg, text="Cancelar", command=dlg.destroy).pack(pady=(6, 8))
            apply_tooltips(dlg)

        tk.Button(row, text="Mover", width=8, command=lambda n=nome: mover_para_pasta(n), cursor="hand2").pack(side="left", padx=4)
        tk.Button(row, text="ℹ", width=3, command=lambda n=nome: show_metadata(n), cursor="hand2").pack(side="left", padx=(6, 4))
        tk.Button(row, text="Abrir", width=8, command=lambda n=nome: open_file_from_list(n), cursor="hand2").pack(side="left", padx=4)
        tk.Button(row, text="🗑", width=3, command=lambda n=nome: delete_file(n), cursor="hand2").pack(side="left", padx=4)

        items_shown += 1

    if items_shown == 0:
        tk.Label(file_list_container, text="Nenhum arquivo .txt, .pdf ou .peg nesta pasta.", fg="gray").pack(padx=6, pady=10)
        set_global_status("Nenhum item encontrado.")
    else:
        set_global_status(f"{items_shown} item(ns) listados")

def move_file_to_folder(nome, folder):
    origem = os.path.join(CURRENT_FOLDER, nome)
    destino_dir = safe_abs(folder)
    destino = os.path.join(destino_dir, nome)

    if not os.path.exists(origem):
        messagebox.showinfo("Mover", "Arquivo não encontrado.")
        refresh_file_list()
        return

    if not os.path.isdir(destino_dir):
        messagebox.showerror("Mover", "Pasta de destino não encontrada.")
        refresh_file_list()
        return

    if os.path.exists(destino):
        if not messagebox.askyesno("Confirmar", f"O arquivo '{nome}' já existe em '{os.path.basename(destino_dir)}'. Deseja sobrescrever?"):
            return
        try:
            if os.path.isdir(destino):
                shutil.rmtree(destino)
            else:
                os.remove(destino)
        except Exception:
            pass

    try:
        shutil.move(origem, destino)

        root_meta = load_meta(CURRENT_FOLDER)
        folder_meta = load_meta(destino_dir)
        if nome in root_meta:
            folder_meta[nome] = root_meta.pop(nome)
            save_meta(CURRENT_FOLDER, root_meta)
            save_meta(destino_dir, folder_meta)

        ensure_meta_for_file(destino_dir, nome)
        messagebox.showinfo("Movido", f"Arquivo '{nome}' movido para '{os.path.basename(destino_dir)}'.")
        refresh_file_list()
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao mover:\n{e}")

def show_metadata(nome):
    caminho = os.path.join(CURRENT_FOLDER, nome)
    if not os.path.exists(caminho):
        messagebox.showinfo("Info", "Arquivo não encontrado.")
        refresh_file_list()
        return

    try:
        tamanho = os.path.getsize(caminho)
    except Exception:
        tamanho = 0

    try:
        mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(caminho)))
    except Exception:
        mtime = "?"

    created_ts = get_created_time(CURRENT_FOLDER, nome)
    try:
        ctime_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_ts))
    except Exception:
        ctime_str = "?"

    dlg = tk.Toplevel(root)
    dlg.title("Informações do arquivo")
    dlg.transient(root)
    dlg.resizable(False, False)

    tk.Label(dlg, text=f"Nome: {nome}", anchor="w").pack(fill="x", padx=12, pady=(8, 4))
    frame = tk.Frame(dlg)
    frame.pack(fill="x", padx=12, pady=(0, 8))
    tk.Label(frame, text="Tamanho:", width=12, anchor="w").grid(row=0, column=0, sticky="w")
    tk.Label(frame, text=f"{tamanho} bytes", anchor="w").grid(row=0, column=1, sticky="w")
    tk.Label(frame, text="Modificado:", width=12, anchor="w").grid(row=1, column=0, sticky="w")
    tk.Label(frame, text=mtime, anchor="w").grid(row=1, column=1, sticky="w")
    tk.Label(frame, text="Criado:", width=12, anchor="w").grid(row=2, column=0, sticky="w")
    tk.Label(frame, text=ctime_str, anchor="w").grid(row=2, column=1, sticky="w")

    btns = tk.Frame(dlg)
    btns.pack(fill="x", padx=12, pady=(0, 12))
    tk.Button(btns, text="Abrir", command=lambda: (dlg.destroy(), open_file_from_list(nome))).pack(side="right", padx=(6, 0))
    tk.Button(btns, text="Fechar", command=dlg.destroy).pack(side="right")
    apply_tooltips(dlg)

def delete_file(nome):
    caminho = os.path.join(CURRENT_FOLDER, nome)
    if not os.path.exists(caminho):
        messagebox.showinfo("Info", "Arquivo não encontrado.")
        refresh_file_list()
        return

    cur = current_editor_state.get("original_path")
    if cur and os.path.abspath(cur) == os.path.abspath(caminho) and current_editor_state.get("dirty"):
        r = messagebox.askyesnocancel("Salvar alterações?", "O arquivo atual não foi salvo. Deseja salvar antes de deletar?")
        if r is None:
            return
        if r:
            if action_save() is not True:
                return

    if messagebox.askyesno("Confirmar", f"Deletar '{nome}'?"):
        try:
            os.remove(caminho)
            data = load_meta(CURRENT_FOLDER)
            if nome in data:
                del data[nome]
                save_meta(CURRENT_FOLDER, data)
            messagebox.showinfo("Deletado", f"Arquivo '{nome}' removido.")
            if cur and os.path.abspath(cur) == os.path.abspath(caminho):
                current_editor_state["original_path"] = None
                title_lbl.config(text="Nenhum arquivo")
                current_editor_state["saved_snapshot"] = ""
                current_editor_state["dirty"] = False
                try:
                    text_widget.delete("1.0", tk.END)
                    text_widget.edit_modified(False)
                except Exception:
                    pass
            refresh_file_list()
        except Exception as e:
            messagebox.showerror("Erro", f"Não consegui deletar:\n{e}")

def open_editor_with_content(texto, title, mode, original_path):
    global EDITOR_LOADING

    try:
        root.unbind_all("<MouseWheel>")
        root.unbind_all("<Button-4>")
        root.unbind_all("<Button-5>")
    except Exception:
        pass

    EDITOR_LOADING = True
    try:
        text_widget.delete("1.0", tk.END)
        if texto is not None:
            text_widget.insert("1.0", texto)
        else:
            text_widget.insert("1.0", "")
        try:
            text_widget.edit_modified(False)
        except Exception:
            pass
    finally:
        EDITOR_LOADING = False

    current_editor_state["mode"] = mode
    current_editor_state["original_path"] = original_path
    title_lbl.config(text=title)

    set_snapshot_and_clean(current_text())
    update_status_counts()

    if mode == "from_folder":
        btn_save.config(text="Salvar", command=action_save)
        btn_save_to_folder.config(state="disabled")
        btn_export.config(state="normal", command=action_exportar)
    elif mode == "external":
        btn_save.config(text="Salvar", command=action_save)
        btn_save_to_folder.config(state="normal", command=action_salvar_na_pasta)
        btn_export.config(state="disabled")
    else:
        btn_save.config(text="Salvar", command=action_save)
        btn_save_to_folder.config(state="normal", command=action_salvar_na_pasta)
        btn_export.config(state="disabled")

    try:
        root.unbind_all("<Control-s>")
        root.unbind_all("<Control-S>")
        root.unbind_all("<Control-f>")
        root.unbind_all("<Control-F>")
        root.unbind_all("<F3>")
        root.unbind_all("<Shift-F3>")
    except Exception:
        pass

    root.bind_all("<Control-s>", lambda e: action_save())
    root.bind_all("<Control-S>", lambda e: action_save())
    root.bind_all("<Control-f>", lambda e: (show_find_bar(), "break"))
    root.bind_all("<Control-F>", lambda e: (show_find_bar(), "break"))
    root.bind_all("<F3>", find_next)
    root.bind_all("<Shift-F3>", find_prev)
    root.bind_all("<Escape>", hide_find_bar)
    text_widget.bind("<Control-f>", lambda e: (show_find_bar(), "break"))
    text_widget.bind("<Control-F>", lambda e: (show_find_bar(), "break"))

    main_frame.pack_forget()
    editor_frame.pack(fill="both", expand=True)
    text_widget.focus_set()

def open_file_from_list(nome):
    if confirm_discard_changes() is not True:
        return
    caminho = os.path.join(CURRENT_FOLDER, nome)
    if not os.path.exists(caminho):
        messagebox.showerror("Erro", f"Arquivo não encontrado:\n{caminho}")
        refresh_file_list()
        return
    _, ext = os.path.splitext(caminho)
    if ext.lower() == ".pdf":
        abrir_com_padrao(caminho)
        return
    texto = read_text_any(caminho)
    ensure_meta_for_file(CURRENT_FOLDER, nome)
    open_editor_with_content(texto, nome, mode="from_folder", original_path=caminho)

def abrir_editavel(caminho=None):
    if confirm_discard_changes() is not True:
        return
    if not caminho:
        caminho = filedialog.askopenfilename(
            initialdir=CURRENT_FOLDER,
            filetypes=[
                ("Todos os arquivos", "*.*"),
                ("Peg files", "*.peg"),
                ("Text files", "*.txt"),
            ],
        )
    if not caminho:
        return
    caminho = safe_abs(caminho)
    if not os.path.exists(caminho):
        messagebox.showerror("Erro", f"Arquivo não encontrado:\n{caminho}")
        return
    _, ext = os.path.splitext(caminho)
    if ext.lower() == ".pdf":
        abrir_com_padrao(caminho)
        return
    texto = read_text_any(caminho)
    nome = os.path.basename(caminho)
    mode = "from_folder" if same_folder(os.path.dirname(caminho), CURRENT_FOLDER) else "external"
    open_editor_with_content(texto, nome, mode=mode, original_path=caminho)

def novo_arquivo():
    if confirm_discard_changes() is not True:
        return
    open_editor_with_content("", "Novo arquivo", mode="new", original_path=None)

def _salvar_na_pasta_com_nome(conteudo, nome_arquivo, pasta=ORIGINAL_BASE_FOLDER):
    if not nome_arquivo:
        return None
    pasta = safe_abs(pasta)
    base, ext = os.path.splitext(nome_arquivo)
    if ext == "":
        nome_arquivo = base + ".peg"
    caminho = os.path.join(pasta, nome_arquivo)
    try:
        destino_dir = os.path.dirname(caminho) or pasta
        os.makedirs(destino_dir, exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
        ensure_meta_for_file(destino_dir, os.path.basename(caminho))
        return caminho
    except Exception as e:
        messagebox.showerror("Erro", f"Não consegui salvar na pasta:\n{e}")
        return None

def action_save(event=None):
    mode = current_editor_state.get("mode")
    conteudo = current_text()

    if mode == "from_folder":
        nome = os.path.basename(current_editor_state.get("original_path")) if current_editor_state.get("original_path") else None
        if nome:
            saved = _salvar_na_pasta_com_nome(conteudo, nome, pasta=CURRENT_FOLDER)
            if saved:
                messagebox.showinfo("Sucesso", f"Arquivo salvo em:\n{saved}")
                current_editor_state["original_path"] = saved
                title_lbl.config(text=os.path.basename(saved))
                set_snapshot_and_clean(conteudo)
                refresh_file_list()
                return True
            return False
        return action_salvar_na_pasta()

    if mode == "external":
        if current_editor_state.get("original_path"):
            try:
                with open(current_editor_state["original_path"], "w", encoding="utf-8") as f:
                    f.write(conteudo)
                messagebox.showinfo("Sucesso", f"Arquivo salvo:\n{current_editor_state['original_path']}")
                set_snapshot_and_clean(conteudo)
                saved_dir = os.path.dirname(os.path.abspath(current_editor_state["original_path"]))
                if same_folder(saved_dir, CURRENT_FOLDER):
                    ensure_meta_for_file(CURRENT_FOLDER, os.path.basename(current_editor_state["original_path"]))
                    refresh_file_list()
                return True
            except Exception as e:
                messagebox.showerror("Erro", f"Não consegui salvar:\n{e}")
                return False
        return action_save_as()

    return action_salvar_na_pasta()

def action_save_as(event=None):
    conteudo = current_text()
    caminho = filedialog.asksaveasfilename(
        initialdir=CURRENT_FOLDER,
        defaultextension=".peg",
        filetypes=[
            ("Peg files", "*.peg"),
            ("Text files", "*.txt"),
            ("Todos os arquivos", "*.*"),
        ],
    )
    if caminho:
        try:
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(conteudo)
            messagebox.showinfo("Sucesso", f"Arquivo salvo em:\n{caminho}")
            current_editor_state["original_path"] = caminho
            if same_folder(os.path.dirname(os.path.abspath(caminho)), CURRENT_FOLDER):
                current_editor_state["mode"] = "from_folder"
                ensure_meta_for_file(CURRENT_FOLDER, os.path.basename(caminho))
            else:
                current_editor_state["mode"] = "external"
            title_lbl.config(text=os.path.basename(caminho))
            set_snapshot_and_clean(conteudo)
            refresh_file_list()
            return True
        except Exception as e:
            messagebox.showerror("Erro", f"Não consegui salvar:\n{e}")
            return False
    return False

def action_salvar_na_pasta():
    conteudo = current_text()
    nome = simpledialog.askstring("Salvar na pasta", "Nome do arquivo para salvar na pasta:", parent=root)
    if not nome:
        return False
    nome = nome.strip()
    if not nome:
        return False
    base, ext = os.path.splitext(nome)
    nome_final = nome if ext else (base + ".peg")
    destino_path = os.path.join(CURRENT_FOLDER, nome_final)
    if os.path.exists(destino_path):
        if not messagebox.askyesno("Confirmar", f"O arquivo '{os.path.basename(destino_path)}' já existe na pasta.\nDeseja sobrescrever?"):
            return False
    saved = _salvar_na_pasta_com_nome(conteudo, nome_final, pasta=CURRENT_FOLDER)
    if saved:
        messagebox.showinfo("Sucesso", f"Arquivo salvo em:\n{saved}")
        current_editor_state["original_path"] = saved
        current_editor_state["mode"] = "from_folder"
        title_lbl.config(text=os.path.basename(saved))
        set_snapshot_and_clean(conteudo)
        ensure_meta_for_file(CURRENT_FOLDER, os.path.basename(saved))
        refresh_file_list()
        return True
    return False

def action_exportar():
    if current_editor_state.get("mode") != "from_folder" or not current_editor_state.get("original_path"):
        messagebox.showinfo("Exportar", "Exportar só está disponível para arquivos da pasta do Notepegy.")
        return
    dlg = tk.Toplevel(root)
    dlg.title("Exportar arquivo")
    dlg.transient(root)
    dlg.grab_set()

    tk.Label(dlg, text="Escolha o formato de exportação:").pack(anchor="w", padx=12, pady=(12, 6))
    formato_var = tk.StringVar(value="peg")
    tk.Radiobutton(dlg, text=".peg (original)", variable=formato_var, value="peg").pack(anchor="w", padx=18)
    tk.Radiobutton(dlg, text=".txt", variable=formato_var, value="txt").pack(anchor="w", padx=18)
    tk.Radiobutton(dlg, text="Manter extensão original", variable=formato_var, value="all").pack(anchor="w", padx=18)

    apagar_var = tk.BooleanVar(value=False)
    tk.Checkbutton(dlg, text="Apagar arquivo original após exportar", variable=apagar_var).pack(anchor="w", padx=12, pady=(8, 0))

    btn_frame = tk.Frame(dlg)
    btn_frame.pack(fill="x", pady=12, padx=12)

    def on_ok():
        formato = formato_var.get()
        apagar = apagar_var.get()
        dlg.destroy()
        _do_export(formato, apagar)

    tk.Button(btn_frame, text="Exportar", command=on_ok).pack(side="right", padx=(6, 0))
    tk.Button(btn_frame, text="Cancelar", command=dlg.destroy).pack(side="right")
    apply_tooltips(dlg)

def _do_export(formato, apagar):
    conteudo = current_text()
    origem = current_editor_state["original_path"]
    _, ext_origem = os.path.splitext(os.path.basename(origem))
    if formato == "all":
        ext_dest = ext_origem or ".peg"
    else:
        ext_dest = "." + formato
    destino = filedialog.asksaveasfilename(
        initialdir=os.path.expanduser("~"),
        defaultextension=ext_dest,
        filetypes=[("Todos os arquivos", "*.*")],
    )
    if not destino:
        return
    try:
        with open(destino, "w", encoding="utf-8") as f:
            f.write(conteudo)
        if apagar:
            try:
                os.remove(origem)
                current_editor_state["original_path"] = None
                current_editor_state["saved_snapshot"] = ""
                current_editor_state["dirty"] = False
            except Exception:
                messagebox.showwarning("Aviso", "Não foi possível apagar o arquivo original após exportar.")
        messagebox.showinfo("Exportado", f"Arquivo exportado com sucesso.\nDestino: {destino}")
        refresh_file_list()
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao exportar:\n{e}")

def show_main_menu():
    try:
        root.unbind_all("<Control-s>")
        root.unbind_all("<Control-S>")
        root.unbind_all("<Control-f>")
        root.unbind_all("<Control-F>")
        root.unbind_all("<F3>")
        root.unbind_all("<Shift-F3>")
        root.unbind_all("<Escape>")
    except Exception:
        pass
    if confirm_discard_changes() is None:
        return
    editor_frame.pack_forget()
    refresh_file_list()
    main_frame.pack(fill="both", expand=True)

def on_app_close():
    if confirm_discard_changes() is not True:
        return
    root.destroy()

def on_startup_open_arg():
    if len(sys.argv) <= 1:
        return
    arg = sys.argv[1]
    caminho = safe_abs(arg)
    if os.path.isdir(caminho):
        change_folder(caminho)
        return
    if os.path.isfile(caminho):
        _, ext = os.path.splitext(caminho)
        if ext.lower() == ".pdf":
            abrir_com_padrao(caminho)
            return
        texto = read_text_any(caminho)
        nome = os.path.basename(caminho)
        mode = "from_folder" if same_folder(os.path.dirname(caminho), CURRENT_FOLDER) else "external"
        open_editor_with_content(texto, nome, mode=mode, original_path=caminho)

def enable_windows_drag_drop():
    if not sys.platform.startswith("win"):
        return
    try:
        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32
    except Exception:
        return

    WM_DROPFILES = 0x0233
    GWL_WNDPROC = -4

    DragAcceptFiles = shell32.DragAcceptFiles
    DragAcceptFiles.argtypes = [ctypes.c_void_p, ctypes.c_bool]

    DragQueryFileW = shell32.DragQueryFileW
    DragQueryFileW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint]
    DragQueryFileW.restype = ctypes.c_uint

    DragFinish = shell32.DragFinish
    DragFinish.argtypes = [ctypes.c_void_p]

    CallWindowProcW = user32.CallWindowProcW
    CallWindowProcW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
    CallWindowProcW.restype = ctypes.c_ssize_t

    SetWindowLongPtrW = getattr(user32, "SetWindowLongPtrW", None)
    SetWindowLongW = getattr(user32, "SetWindowLongW", None)

    root.update_idletasks()
    hwnd = root.winfo_id()
    DragAcceptFiles(hwnd, True)

    WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t)
    old_proc = ctypes.c_void_p()
    proc_ref = {"cb": None}

    def wndproc(hwnd_, msg, wparam, lparam):
        if msg == WM_DROPFILES:
            hdrop = wparam
            try:
                count = DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
                files = []
                for i in range(count):
                    length = DragQueryFileW(hdrop, i, None, 0) + 1
                    buff = ctypes.create_unicode_buffer(length)
                    DragQueryFileW(hdrop, i, buff, length)
                    files.append(buff.value)
                if files:
                    dropped = files[0]
                    if os.path.isdir(dropped):
                        if confirm_discard_changes() is True:
                            change_folder(dropped)
                    else:
                        if confirm_discard_changes() is True:
                            open_any_text_file(dropped, from_folder_guess=same_folder(os.path.dirname(dropped), CURRENT_FOLDER))
                DragFinish(hdrop)
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao receber arquivo arrastado:\n{e}")
            return 0
        return CallWindowProcW(old_proc, hwnd_, msg, wparam, lparam)

    cb = WNDPROC(wndproc)
    proc_ref["cb"] = cb

    if SetWindowLongPtrW is not None:
        SetWindowLongPtrW.restype = ctypes.c_void_p
        SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        prev = SetWindowLongPtrW(hwnd, GWL_WNDPROC, cb)
        old_proc.value = prev if prev else 0
    elif SetWindowLongW is not None:
        SetWindowLongW.restype = ctypes.c_long
        SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        prev = SetWindowLongW(hwnd, GWL_WNDPROC, cb)
        old_proc.value = prev if prev else 0

    root._drop_proc_ref = proc_ref  # keep alive

editor_top.pack(fill="x")
btn_back = tk.Button(editor_top, text="←", width=3, command=show_main_menu, cursor="hand2")
btn_find = tk.Button(editor_top, text="🔍", width=3, command=show_find_bar, cursor="hand2")
btn_back.pack(side="left")
btn_find.pack(side="left", padx=(4, 0))
title_lbl.pack(side="left", padx=(8, 0))

find_bar.pack_forget()
tk.Label(find_bar, text="Localizar:", padx=8, bg=THEME["panel"]).pack(side="left")
find_entry.pack(side="left", padx=(0, 6), pady=4)
find_prev_btn.pack(side="left", padx=(0, 2))
find_next_btn.pack(side="left", padx=(0, 6))
find_count_lbl.pack(side="left", padx=(0, 6))
find_close_btn.pack(side="right", padx=6)

find_prev_btn.config(command=find_prev)
find_next_btn.config(command=find_next)
find_close_btn.config(command=hide_find_bar)
find_entry.bind("<KeyRelease>", on_find_change)
find_entry.bind("<Return>", on_find_enter)

editor_area.pack(fill="both", expand=True, pady=(8, 0))
text_widget.pack(fill="both", expand=True)
status_line.pack(fill="x", padx=6, pady=(6, 4))

editor_buttons.pack(fill="x", pady=(0, 8))
btn_save.pack(side="left", padx=(0, 6))
btn_save_as.pack(side="left", padx=(6, 6))
btn_save_to_folder.pack(side="left", padx=(6, 6))
btn_export.pack(side="left", padx=(6, 6))

text_widget.tag_configure("search_match", background="#fff2a8")
text_widget.tag_configure("search_current", background="#ffd166")
text_widget.bind("<<Modified>>", sync_dirty_state)
text_widget.bind("<KeyRelease>", sync_dirty_state)
text_widget.bind("<ButtonRelease>", update_status_counts)

btn_save.config(command=action_save)
btn_save_as.config(command=action_save_as)
btn_save_to_folder.config(command=action_salvar_na_pasta)
btn_export.config(command=action_exportar)

btn_theme_light.config(command=lambda: set_theme("light"))
btn_theme_dark.config(command=lambda: set_theme("dark"))

apply_theme_to_widgets()
apply_tooltips(root)

root.protocol("WM_DELETE_WINDOW", on_app_close)

main_frame.pack(fill="both", expand=True)
refresh_file_list()
enable_windows_drag_drop()
on_startup_open_arg()

root.mainloop()
