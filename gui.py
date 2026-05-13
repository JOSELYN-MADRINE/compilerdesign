"""
Compiler IDE – Tkinter frontend.

Run:  python gui.py
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, font as tkfont
import os, re
from compiler import Compiler

# ══════════════════════════════════════════════════════════════ colour palette

BG_ROOT   = "#1e1e2e"
BG_PANEL  = "#24273a"
BG_EDITOR = "#1a1a2e"
BG_DARK   = "#181825"
FG_TEXT   = "#cad3f5"
FG_DIM    = "#6e738d"
ACCENT    = "#8aadf4"
SUCCESS   = "#a6da95"
ERROR_C   = "#ed8796"
WARNING   = "#eed49f"
BORDER    = "#363a4f"
KW_COLOR  = "#c6a0f6"   # keywords
TYPE_CLR  = "#8aadf4"   # types
NUM_CLR   = "#f5a97f"   # numbers
STR_CLR   = "#a6da95"   # strings
CMT_CLR   = "#6e738d"   # comments
OP_CLR    = "#91d7e3"   # operators


# ══════════════════════════════════════════════════════════════ sample source

SAMPLE = """\

// Variable declarations
int    x   = 10;
float  pi  = 3.14;
string msg = "Hello, World!";
bool   ok  = true;

// Print a message
print(msg);

// Arithmetic
int result = x * 2 + 5;
print(result);

// if / else
if (x > 5) {
    print(x);
} else {
    print(result);
}

// while loop – print 1 to 5
int i = 1;
while (i <= 5) {
    print(i);
    i = i + 1;
}

// Nested condition
if (ok && x > 0) {
    string done = "Done!";
    print(done);
}
"""


# ══════════════════════════════════════════════════════════════════════ GUI ══

class CompilerIDE:
    def __init__(self) -> None:
        self.compiler = Compiler()

        self.root = tk.Tk()
        self.root.title("Python Compiler IDE")
        self.root.geometry("1280x820")
        self.root.configure(bg=BG_ROOT)
        self.root.minsize(960, 620)

        self._fonts()
        self._build_toolbar()
        self._build_main()
        self._build_statusbar()
        self._load_sample()

    # ─────────────────────────────────────────────────── fonts ───────────────

    def _fonts(self) -> None:
        self.mono   = tkfont.Font(family="Courier New",  size=11)
        self.mono_s = tkfont.Font(family="Courier New",  size=9)
        self.sans   = tkfont.Font(family="Helvetica",    size=10)
        self.sans_b = tkfont.Font(family="Helvetica",    size=10, weight="bold")
        self.head   = tkfont.Font(family="Helvetica",    size=12, weight="bold")

    # ─────────────────────────────────────────────────── toolbar ─────────────

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self.root, bg=BG_PANEL, height=50)
        bar.pack(fill=tk.X, padx=6, pady=(6, 0))
        bar.pack_propagate(False)

        # ── title ────────────────────────────────────────────────────────────
        tk.Label(bar, text="Compiler IDE", bg=BG_PANEL, fg=ACCENT,
                 font=self.head).pack(side=tk.LEFT, padx=14, pady=10)

        self._sep(bar)

        # Parser mode is fixed to top-down recursive descent.
        self.parser_var = tk.StringVar(value="topdown")

        # ── action buttons ───────────────────────────────────────────────────
        self._btn(bar, "▶  Run All Phases", self.run_all,
                  bg=ACCENT, fg=BG_DARK, padx=16)
        self._btn(bar, "⚡  Run Code",       self.run_code,
                  bg="#a6da95", fg=BG_DARK, padx=14)
        self._sep(bar)
        self._btn(bar, "Lexer Only",    self.run_lexer,    padx=10)
        self._btn(bar, "Parser Only",   self.run_parser,   padx=10)
        self._btn(bar, "Semantic Only", self.run_semantic, padx=10)
        self._sep(bar)
        self._btn(bar, "Open",   self.open_file,    padx=10)
        self._btn(bar, "Save",   self.save_file,    padx=10)
        self._btn(bar, "Sample", self._load_sample, padx=10)
        self._btn(bar, "Clear",  self.clear_all,    padx=10)

    def _sep(self, parent: tk.Frame) -> None:
        tk.Frame(parent, bg=BORDER, width=1).pack(
            side=tk.LEFT, fill=tk.Y, pady=8)

    def _btn(self, parent: tk.Frame, text: str, cmd,
             bg: str = BG_DARK, fg: str = FG_TEXT, padx: int = 12) -> tk.Button:
        b = tk.Button(parent, text=text, command=cmd,
                      bg=bg, fg=fg, relief=tk.FLAT,
                      padx=padx, pady=6,
                      font=self.sans, cursor="hand2",
                      activebackground=BORDER, activeforeground=FG_TEXT,
                      bd=0)
        b.pack(side=tk.LEFT, padx=3, pady=8)
        return b

    # ─────────────────────────────────────────────────── main area ───────────

    def _build_main(self) -> None:
        self.pane = tk.PanedWindow(
            self.root, orient=tk.HORIZONTAL,
            bg=BORDER, sashwidth=5, sashrelief=tk.FLAT,
        )
        self.pane.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self._build_editor()
        self._build_output()

    # ─────────────────────────────────────────────────── editor ──────────────

    def _build_editor(self) -> None:
        frame = tk.Frame(self.pane, bg=BG_ROOT)
        self.pane.add(frame, minsize=320, width=520)

        hdr = tk.Frame(frame, bg=BG_PANEL, height=28)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Source Code Editor", bg=BG_PANEL,
                 fg=FG_DIM, font=self.mono_s).pack(side=tk.LEFT, padx=10, pady=5)

        edit_row = tk.Frame(frame, bg=BG_EDITOR)
        edit_row.pack(fill=tk.BOTH, expand=True)

        # line-number gutter
        self.gutter = tk.Text(
            edit_row, width=4, bg=BG_DARK, fg=FG_DIM,
            font=self.mono, state=tk.DISABLED, relief=tk.FLAT,
            padx=4, pady=4, cursor="arrow", selectbackground=BG_DARK,
        )
        self.gutter.pack(side=tk.LEFT, fill=tk.Y)

        self.editor = scrolledtext.ScrolledText(
            edit_row, font=self.mono, bg=BG_EDITOR, fg=FG_TEXT,
            insertbackground=ACCENT, selectbackground=BORDER,
            relief=tk.FLAT, padx=8, pady=4,
            wrap=tk.NONE, undo=True, tabs=("1c",),
        )
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # highlight tags
        self.editor.tag_configure("kw",  foreground=KW_COLOR)
        self.editor.tag_configure("tp",  foreground=TYPE_CLR)
        self.editor.tag_configure("num", foreground=NUM_CLR)
        self.editor.tag_configure("str", foreground=STR_CLR)
        self.editor.tag_configure("cmt", foreground=CMT_CLR)
        self.editor.tag_configure("op",  foreground=OP_CLR)

        self.editor.bind("<KeyRelease>", self._on_edit)
        self.editor.bind("<ButtonRelease>", self._on_edit)

    # ─────────────────────────────────────────────────── output tabs ─────────

    def _build_output(self) -> None:
        frame = tk.Frame(self.pane, bg=BG_ROOT)
        self.pane.add(frame, minsize=320)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("C.TNotebook",       background=BG_ROOT, borderwidth=0)
        style.configure("C.TNotebook.Tab",   background=BG_PANEL, foreground=FG_DIM,
                        padding=[14, 5], font=("Helvetica", 9))
        style.map("C.TNotebook.Tab",
                  background=[("selected", BG_ROOT)],
                  foreground=[("selected", ACCENT)])

        self.nb = ttk.Notebook(frame, style="C.TNotebook")
        self.nb.pack(fill=tk.BOTH, expand=True)

        tabs = [
            ("  Console  ",     "w_console"),
            ("  Tokens  ",      "w_tokens"),
            ("  Parse Steps  ", "w_steps"),
            ("  AST  ",         "w_ast"),
            ("  Semantic  ",    "w_semantic"),
            ("  Symbol Table  ","w_symbols"),
            ("  Summary  ",     "w_summary"),
        ]
        for title, attr in tabs:
            tab_frame = tk.Frame(self.nb, bg=BG_ROOT)
            self.nb.add(tab_frame, text=title)

            # Console tab gets a special layout with an input bar
            if attr == "w_console":
                self._build_console_tab(tab_frame)
                continue

            w = scrolledtext.ScrolledText(
                tab_frame, font=self.mono_s, bg=BG_PANEL, fg=FG_TEXT,
                relief=tk.FLAT, padx=10, pady=6, state=tk.DISABLED,
                wrap=tk.WORD, insertbackground=ACCENT,
            )
            w.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            # tag styles for output panes
            w.tag_configure("hdr",   foreground=ACCENT,   font=self.sans_b)
            w.tag_configure("ok",    foreground=SUCCESS)
            w.tag_configure("err",   foreground=ERROR_C)
            w.tag_configure("warn",  foreground=WARNING)
            w.tag_configure("dim",   foreground=FG_DIM)
            w.tag_configure("tt",    foreground=KW_COLOR)
            w.tag_configure("tv",    foreground=STR_CLR)
            w.tag_configure("bold",  font=self.sans_b)
            w.tag_configure("shift", foreground=SUCCESS)
            w.tag_configure("reduce",foreground=WARNING)
            w.tag_configure("accept",foreground=ACCENT)
            setattr(self, attr, w)

    def _build_console_tab(self, parent: tk.Frame) -> None:
        """Console output panel with execution trace toggle."""
        # output display
        self.w_console = scrolledtext.ScrolledText(
            parent, font=self.mono, bg="#0d1117", fg="#e6edf3",
            relief=tk.FLAT, padx=12, pady=8, state=tk.DISABLED,
            wrap=tk.WORD, insertbackground=ACCENT,
        )
        self.w_console.pack(fill=tk.BOTH, expand=True, padx=2, pady=(2, 0))
        self.w_console.tag_configure("prompt",  foreground="#58a6ff",
                                     font=self.sans_b)
        self.w_console.tag_configure("output",  foreground="#e6edf3",
                                     font=self.mono)
        self.w_console.tag_configure("err",     foreground="#f85149")
        self.w_console.tag_configure("dim",     foreground="#8b949e")
        self.w_console.tag_configure("ok",      foreground="#3fb950")
        self.w_console.tag_configure("warn",    foreground="#d29922")
        self.w_console.tag_configure("hdr",     foreground="#58a6ff",
                                     font=self.sans_b)

        # bottom bar: trace toggle + clear button
        bar = tk.Frame(parent, bg=BG_PANEL, height=30)
        bar.pack(fill=tk.X, padx=2, pady=(0, 2))
        bar.pack_propagate(False)

        self.show_trace_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            bar, text="Show execution trace",
            variable=self.show_trace_var,
            bg=BG_PANEL, fg=FG_DIM, selectcolor=BG_DARK,
            activebackground=BG_PANEL, activeforeground=FG_TEXT,
            font=self.mono_s, relief=tk.FLAT,
            command=self._refresh_console,
        ).pack(side=tk.LEFT, padx=10, pady=4)

        tk.Button(bar, text="Clear Console", command=self._clear_console,
                  bg=BG_DARK, fg=FG_DIM, relief=tk.FLAT,
                  font=self.mono_s, cursor="hand2",
                  padx=8, pady=2).pack(side=tk.RIGHT, padx=8, pady=4)

        self._last_exe_results: dict = {}

    # ─────────────────────────────────────────────────── status bar ──────────

    def _build_statusbar(self) -> None:
        bar = tk.Frame(self.root, bg=BG_PANEL, height=24)
        bar.pack(fill=tk.X, padx=6, pady=(0, 4))
        bar.pack_propagate(False)

        self.status_lbl = tk.Label(bar, text="Ready", bg=BG_PANEL,
                                   fg=FG_DIM, font=self.mono_s)
        self.status_lbl.pack(side=tk.LEFT, padx=10)

        self.cursor_lbl = tk.Label(bar, text="Ln 1, Col 1",
                                   bg=BG_PANEL, fg=FG_DIM, font=self.mono_s)
        self.cursor_lbl.pack(side=tk.RIGHT, padx=10)

    def _set_status(self, msg: str, color: str = FG_DIM) -> None:
        self.status_lbl.config(text=msg, fg=color)

    # ─────────────────────────────────────────────────── editor helpers ───────

    def _on_edit(self, _event=None) -> None:
        self._update_gutter()
        self._update_cursor()
        self._highlight()

    def _update_gutter(self) -> None:
        content    = self.editor.get("1.0", tk.END)
        line_count = content.count('\n')
        self.gutter.config(state=tk.NORMAL)
        self.gutter.delete("1.0", tk.END)
        for i in range(1, line_count + 1):
            self.gutter.insert(tk.END, f"{i:>3}\n")
        self.gutter.config(state=tk.DISABLED)

    def _update_cursor(self) -> None:
        pos  = self.editor.index(tk.INSERT)
        ln, col = pos.split('.')
        self.cursor_lbl.config(text=f"Ln {ln}, Col {int(col)+1}")

    def _highlight(self) -> None:
        t = self.editor
        src = t.get("1.0", tk.END)
        for tag in ("kw", "tp", "num", "str", "cmt", "op"):
            t.tag_remove(tag, "1.0", tk.END)

        patterns = [
            ("cmt", r"//.*$"),
            ("str", r'"[^"\n]*"'),
            ("tp",  r'\b(int|float|string|bool)\b'),
            ("kw",  r'\b(if|else|while|print|true|false)\b'),
            ("num", r'\b\d+\.?\d*\b'),
            ("op",  r'[+\-*/=<>!&|%]+'),
        ]
        for tag, pat in patterns:
            for m in re.finditer(pat, src, re.MULTILINE):
                t.tag_add(tag,
                          f"1.0 + {m.start()} chars",
                          f"1.0 + {m.end()} chars")

    # ─────────────────────────────────────────────────── output writers ───────

    def _clear_output(self, w: scrolledtext.ScrolledText) -> None:
        w.config(state=tk.NORMAL)
        w.delete("1.0", tk.END)

    def _finish_output(self, w: scrolledtext.ScrolledText) -> None:
        w.config(state=tk.DISABLED)

    def _write(self, w, text: str, tag: str = "") -> None:
        if tag:
            w.insert(tk.END, text, tag)
        else:
            w.insert(tk.END, text)

    # ─────────────────────────────────────────────────── run actions ──────────

    def run_all(self) -> None:
        src = self.editor.get("1.0", tk.END).strip()
        if not src:
            messagebox.showinfo("Empty", "Please enter some source code first.")
            return
        pt = self.parser_var.get()
        self._set_status("Compiling…", WARNING)
        self.root.update()
        res = self.compiler.compile(src, pt, execute=False)
        self._render_all(res)

        if res['success']:
            self._set_status("Compilation SUCCESSFUL — click 'Run Code' to execute", SUCCESS)
        elif res['sem_errors']:
            self._set_status(f"Semantic errors: {len(res['sem_errors'])}", ERROR_C)
        elif res['parse_errors']:
            self._set_status(f"Parse errors: {len(res['parse_errors'])}", ERROR_C)
        else:
            self._set_status(f"Lexer errors: {len(res['lex_errors'])}", ERROR_C)

    def run_code(self) -> None:
        """Compile AND execute; output appears in the Console tab."""
        src = self.editor.get("1.0", tk.END).strip()
        if not src:
            messagebox.showinfo("Empty", "Please enter some source code first.")
            return
        pt = self.parser_var.get()
        self._set_status("Compiling & running…", WARNING)
        self.root.update()
        res = self.compiler.compile(src, pt, execute=True)
        self._render_all(res)
        self._render_console(res)
        self.nb.select(0)   # jump to Console tab

        if res.get('exe_errors'):
            self._set_status(
                f"Runtime error: {res['exe_errors'][0]}", ERROR_C)
        elif res.get('executed'):
            n = len(res['exe_output'])
            self._set_status(
                f"Program finished — {n} line(s) of output", SUCCESS)
        elif not res['success']:
            self._set_status("Fix compilation errors before running", ERROR_C)

    def run_lexer(self) -> None:
        src = self.editor.get("1.0", tk.END).strip()
        if not src:
            return
        from lexer import Lexer
        toks, errs = Lexer(src).tokenize()
        blank = dict(ast=None, ast_text='', parse_errors=[], parse_steps=[],
                     sem_errors=[], sem_warnings=[], symbol_table={}, sem_log=[],
                     success=False, exe_output=[], exe_errors=[], exe_log=[],
                     executed=False)
        res = dict(tokens=toks, lex_errors=errs, parser_type=self.parser_var.get(),
                   **blank)
        self._render_all(res)
        self.nb.select(1)
        self._set_status(
            f"Lexer: {len(toks)} tokens, {len(errs)} error(s)",
            SUCCESS if not errs else ERROR_C)

    def run_parser(self) -> None:
        src = self.editor.get("1.0", tk.END).strip()
        if not src:
            return
        from lexer     import Lexer
        from parser_td import TopDownParser
        from compiler  import format_ast
        toks, lex_errs = Lexer(src).tokenize()
        pt = 'topdown'
        parser = TopDownParser(toks)
        ast, p_errs, steps = parser.parse()
        res = dict(tokens=toks, lex_errors=lex_errs, parser_type=pt,
                   ast=ast, ast_text=format_ast(ast) if ast else '',
                   parse_errors=p_errs, parse_steps=steps,
                   sem_errors=[], sem_warnings=[], symbol_table={}, sem_log=[],
                   success=not p_errs, exe_output=[], exe_errors=[],
                   exe_log=[], executed=False)
        self._render_all(res)
        self.nb.select(2)
        self._set_status(
            f"Parser: {len(p_errs)} error(s)",
            SUCCESS if not p_errs else ERROR_C)

    def run_semantic(self) -> None:
        self.run_all()
        self.nb.select(4)

    # ─────────────────────────────────────────────────── renderers ───────────

    def _render_all(self, res: dict) -> None:
        self._render_tokens(res)
        self._render_steps(res)
        self._render_ast(res)
        self._render_semantic(res)
        self._render_symbols(res)
        self._render_summary(res)

    # ── console ───────────────────────────────────────────────────────────────

    def _render_console(self, res: dict) -> None:
        self._last_exe_results = res
        self._refresh_console()

    def _refresh_console(self) -> None:
        res = self._last_exe_results
        w   = self.w_console
        w.config(state=tk.NORMAL)
        w.delete("1.0", tk.END)

        w.insert(tk.END, "CONSOLE OUTPUT\n", "hdr")
        w.insert(tk.END, "─" * 48 + "\n", "dim")

        if not res:
            w.insert(tk.END, "No program executed yet.\n", "dim")
            w.config(state=tk.DISABLED)
            return

        if not res.get('success') and not res.get('executed'):
            w.insert(tk.END, "Cannot run: compilation errors must be fixed first.\n\n", "warn")
            all_errs = res.get('lex_errors', []) + res.get('parse_errors', []) + res.get('sem_errors', [])
            for e in all_errs:
                w.insert(tk.END, f"  {e}\n", "err")
            w.config(state=tk.DISABLED)
            return

        # program output lines
        output = res.get('exe_output', [])
        if output:
            w.insert(tk.END, "\n")
            for line in output:
                w.insert(tk.END, f"  {line}\n", "output")
            w.insert(tk.END, "\n")
        else:
            w.insert(tk.END, "\n  (no output produced)\n\n", "dim")

        # runtime errors
        exe_errs = res.get('exe_errors', [])
        if exe_errs:
            w.insert(tk.END, "Runtime Errors:\n", "err")
            for e in exe_errs:
                w.insert(tk.END, f"  {e}\n", "err")
            w.insert(tk.END, "\n")

        # execution trace (optional)
        if self.show_trace_var.get():
            w.insert(tk.END, "─" * 48 + "\n", "dim")
            w.insert(tk.END, "Execution Trace:\n", "hdr")
            for line in res.get('exe_log', []):
                if '╔' in line or '╚' in line or '║' in line:
                    w.insert(tk.END, line + "\n", "hdr")
                elif '[RUNTIME ERROR]' in line:
                    w.insert(tk.END, line + "\n", "err")
                elif 'print' in line:
                    w.insert(tk.END, line + "\n", "ok")
                elif 'decl' in line or 'assign' in line:
                    w.insert(tk.END, line + "\n", "output")
                elif 'while' in line or 'if' in line:
                    w.insert(tk.END, line + "\n", "warn")
                else:
                    w.insert(tk.END, line + "\n", "dim")

        w.config(state=tk.DISABLED)

    def _clear_console(self) -> None:
        self._last_exe_results = {}
        w = self.w_console
        w.config(state=tk.NORMAL)
        w.delete("1.0", tk.END)
        w.config(state=tk.DISABLED)

    def _render_tokens(self, res: dict) -> None:
        w = self.w_tokens
        self._clear_output(w)
        self._write(w, "LEXICAL ANALYSIS\n\n", "hdr")

        errs = res.get('lex_errors', [])
        if errs:
            self._write(w, "Errors:\n", "bold")
            for e in errs:
                self._write(w, f"  {e}\n", "err")
            self._write(w, "\n")

        toks = res.get('tokens', [])
        if toks:
            self._write(w,
                f"{'#':<5}{'Type':<24}{'Value':<22}{'Line':<6}Col\n",
                "dim")
            self._write(w, "─" * 65 + "\n", "dim")
            for i, tok in enumerate(toks, 1):
                self._write(w, f"{i:<5}", "dim")
                self._write(w, f"{tok.type.name:<24}", "tt")
                val = repr(tok.value)
                if len(val) > 20:
                    val = val[:17] + "…'"
                self._write(w, f"{val:<22}", "tv")
                self._write(w, f"{tok.line:<6}{tok.col}\n", "dim")
        self._finish_output(w)

    def _render_steps(self, res: dict) -> None:
        w = self.w_steps
        self._clear_output(w)
        label = "Top-Down (Recursive Descent)"
        self._write(w, f"SYNTAX ANALYSIS  –  {label}\n\n", "hdr")

        for e in res.get('parse_errors', []):
            self._write(w, f"  {e}\n", "err")
        if res.get('parse_errors'):
            self._write(w, "\n")

        for line in res.get('parse_steps', []):
            if '╔' in line or '╚' in line or '║' in line:
                self._write(w, line + "\n", "hdr")
            elif 'SHIFT' in line:
                self._write(w, line + "\n", "shift")
            elif 'REDUCE' in line:
                self._write(w, line + "\n", "reduce")
            elif 'ACCEPT' in line:
                self._write(w, line + "\n", "accept")
            elif 'ERROR' in line:
                self._write(w, line + "\n", "err")
            elif line.startswith('  ►') or line.startswith('  ✓'):
                self._write(w, line + "\n", "ok")
            elif line.startswith('  '):
                self._write(w, line + "\n", "dim")
            else:
                self._write(w, line + "\n")
        self._finish_output(w)

    def _render_ast(self, res: dict) -> None:
        w = self.w_ast
        self._clear_output(w)
        self._write(w, "ABSTRACT SYNTAX TREE\n\n", "hdr")
        ast_txt = res.get('ast_text', '')
        if ast_txt:
            self._write(w, ast_txt)
        elif res.get('parse_errors'):
            self._write(w, "AST not generated (parse errors present).\n", "err")
        else:
            self._write(w, "No AST generated.\n", "dim")
        self._finish_output(w)

    def _render_semantic(self, res: dict) -> None:
        w = self.w_semantic
        self._clear_output(w)
        self._write(w, "SEMANTIC ANALYSIS\n\n", "hdr")

        errs  = res.get('sem_errors',   [])
        warns = res.get('sem_warnings', [])
        if errs:
            self._write(w, f"Errors ({len(errs)}):\n", "bold")
            for e in errs:
                self._write(w, f"  {e}\n", "err")
            self._write(w, "\n")
        if warns:
            self._write(w, f"Warnings ({len(warns)}):\n", "bold")
            for wn in warns:
                self._write(w, f"  {wn}\n", "warn")
            self._write(w, "\n")

        for line in res.get('sem_log', []):
            if '╔' in line or '╚' in line or '║' in line:
                self._write(w, line + "\n", "hdr")
            elif '[ERROR]' in line:
                self._write(w, line + "\n", "err")
            elif '[WARN]' in line:
                self._write(w, line + "\n", "warn")
            elif '──►' in line or '◄──' in line:
                self._write(w, line + "\n", "dim")
            elif 'Defined' in line:
                self._write(w, line + "\n", "ok")
            else:
                self._write(w, line + "\n", "dim")
        self._finish_output(w)

    def _render_symbols(self, res: dict) -> None:
        w = self.w_symbols
        self._clear_output(w)
        self._write(w, "SYMBOL TABLE\n\n", "hdr")
        syms = res.get('symbol_table', {})
        if syms:
            self._write(w, f"{'Variable':<20}Type Info\n", "dim")
            self._write(w, "─" * 48 + "\n", "dim")
            for name, info in syms.items():
                self._write(w, f"  {name:<18}", "tv")
                self._write(w, f"{info}\n", "tt")
        else:
            self._write(w, "No symbols declared, or semantic phase not run.\n", "dim")
        self._finish_output(w)

    def _render_summary(self, res: dict) -> None:
        w = self.w_summary
        self._clear_output(w)
        self._write(w, "COMPILATION SUMMARY\n\n", "hdr")

        label = "Top-Down (Recursive Descent)"
        self._write(w, f"Parser used:  {label}\n\n", "dim")

        # Phase 1
        lex_ok = not res.get('lex_errors')
        self._write(w, "Phase 1 – Lexical Analysis    ", "bold")
        if lex_ok:
            self._write(w, f"PASS  ({len(res.get('tokens', []))} tokens)\n", "ok")
        else:
            self._write(w, f"FAIL  ({len(res['lex_errors'])} error(s))\n", "err")

        # Phase 2
        p_errs  = res.get('parse_errors', [])
        p_steps = res.get('parse_steps',  [])
        self._write(w, "Phase 2 – Syntax Analysis     ", "bold")
        if res.get('ast') and not p_errs:
            self._write(w, "PASS  (AST built)\n", "ok")
        elif p_errs:
            self._write(w, f"FAIL  ({len(p_errs)} error(s))\n", "err")
        else:
            self._write(w, "SKIPPED\n", "warn")

        # Phase 3
        s_errs  = res.get('sem_errors',   [])
        s_warns = res.get('sem_warnings', [])
        s_log   = res.get('sem_log',      [])
        self._write(w, "Phase 3 – Semantic Analysis   ", "bold")
        if s_log and not s_errs:
            self._write(w, "PASS", "ok")
            if s_warns:
                self._write(w, f"  ({len(s_warns)} warning(s))\n", "warn")
            else:
                self._write(w, "\n")
        elif s_errs:
            self._write(w, f"FAIL  ({len(s_errs)} error(s))\n", "err")
        else:
            self._write(w, "SKIPPED\n", "warn")

        self._write(w, "\n")
        if res.get('success'):
            self._write(w, "  COMPILATION SUCCESSFUL\n", "ok")
        else:
            self._write(w, "  COMPILATION FAILED\n", "err")

        # ── all issues ──
        all_issues = (
            [(e, "err")  for e in res.get('lex_errors',   [])] +
            [(e, "err")  for e in res.get('parse_errors', [])] +
            [(e, "err")  for e in res.get('sem_errors',   [])] +
            [(e, "warn") for e in res.get('sem_warnings', [])]
        )
        if all_issues:
            self._write(w, "\nAll Issues:\n", "bold")
            for msg, tag in all_issues:
                prefix = "[ERROR]  " if tag == "err" else "[WARN]   "
                self._write(w, f"  {prefix}{msg}\n", tag)

        self._finish_output(w)

    # ─────────────────────────────────────────────────── file actions ─────────

    def open_file(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Source files", "*.txt *.c *.lang"),
                       ("All files", "*.*")])
        if not path:
            return
        with open(path, 'r') as f:
            src = f.read()
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", src)
        self._on_edit()
        self._set_status(f"Opened: {os.path.basename(path)}")

    def save_file(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        with open(path, 'w') as f:
            f.write(self.editor.get("1.0", tk.END))
        self._set_status(f"Saved: {os.path.basename(path)}", SUCCESS)

    def clear_all(self) -> None:
        self.editor.delete("1.0", tk.END)
        for attr in ("w_tokens", "w_steps", "w_ast",
                     "w_semantic", "w_symbols", "w_summary"):
            w = getattr(self, attr)
            w.config(state=tk.NORMAL)
            w.delete("1.0", tk.END)
            w.config(state=tk.DISABLED)
        self._clear_console()
        self._update_gutter()
        self._set_status("Ready")

    def _load_sample(self) -> None:
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", SAMPLE)
        self._on_edit()
        self._set_status("Sample code loaded – click 'Run All Phases' to compile")

    # ─────────────────────────────────────────────────── entry point ─────────

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    app = CompilerIDE()
    app.run()
