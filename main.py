
import os, io, re, json, tokenize, tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont

# Default theme
DEFAULT_THEME = {
    "control":    "#569CD6",
    "definition": "#4EC9B0",
    "import":     "#4EC9B0",
    "exception":  "#FF6E6E",
    "logic":      "#569CD6",
    "constants":  "#B5CEA8",
    "builtin":    "#C586C0",
    "digits":     "#B5CEA8",
    "symbols":    "#D4D4D4",
    "paran":      "#D4D4D4",
    "class_name": "#B8D7A3",
    "func_name":  "#DCDCAA",
    "var_name":   "#9CDCFE",
    "string":     "#F29E74",
    "comment":    "#6A9955",
    "module":     "#A0C4FF",
    "self":       "#E7C547",
    "self_attr":  "#9CDCFE",
    "fstring_prefix": "#E7C547",
    # UI colors
    "editor_bg":  "#1C1B21",
    "editor_fg":  "#D8D8D8",
    "ln_bg":      "#1F1E27",
    "ln_fg":      "#5E5A65",
    "accent":     "#8AB4F8",
    "cursor":     "#FFFFFF",
    "scrollbar_trough": "#2C2C34",
    "scrollbar_slider": "#5E5A65"
}

# Config Files
class ConfigManager:
    def __init__(self, folder="configs"):
        self.folder = folder
        self.available = []
        self.ext_map = {}
        self.scan()

    def scan(self):
        self.available.clear()
        self.ext_map.clear()
        if not os.path.isdir(self.folder):
            return
        for fn in sorted(os.listdir(self.folder)):
            if not fn.lower().endswith(".json"):
                continue
            path = os.path.join(self.folder, fn)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    cfg = json.load(fh)
                if not isinstance(cfg, dict):
                    continue
                exts = cfg.get("extensions", []) or cfg.get("ext", [])
                norm = []
                for e in exts:
                    if not isinstance(e, str): continue
                    if not e.startswith("."): e = "." + e
                    norm.append(e.lower())
                cfg["extensions"] = norm
                self.available.append(cfg)
                for e in norm:
                    if e not in self.ext_map:
                        self.ext_map[e] = cfg
            except Exception as ex:
                print(f"[ConfigManager] skipping {path}: {ex}")

    def detect_for_path(self, path):
        ext = os.path.splitext(path)[1].lower()
        if not ext: return None
        return self.ext_map.get(ext)

# Editor
class ConfigEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DamEdit")
        self.iconbitmap("assets\\DamEdit.ico")
        self.geometry("980x700")
        self.minsize(760, 420)

        # state
        self.config_manager = ConfigManager("configs")
        self.lang_config = None
        self.lang_patterns = []
        self.lang_keywords = {}
        self.theme = dict(DEFAULT_THEME)
        self.file_path = None

        # UI colors, read from theme during apply_theme
        self.editor_bg = self.theme.get("editor_bg")
        self.editor_fg = self.theme.get("editor_fg")
        self.ln_bg = self.theme.get("ln_bg")
        self.ln_fg = self.theme.get("ln_fg")
        self.accent = self.theme.get("accent")
        self.cursor = self.theme.get("cursor")

        self._compile_fallbacks()

        # build UI
        self._setup_style()
        self._build_ui()
        self._bind_shortcuts()

        # start with python builtin
        self.load_language_config({"name":"Python (builtin)", "type":"python", "extensions":[".py"], "keywords":{}})
        self._populate_file_list()

        # debounce
        self._highlight_job = None

    # compile small fallbacks
    def _compile_fallbacks(self):
        self._pat_class = re.compile(r"\bclass\s+([A-Za-z_]\w*)")
        self._pat_def   = re.compile(r"\bdef\s+([A-Za-z_]\w*)")
        self._pat_call  = re.compile(r"(?<!\bdef\s)(?<!\bclass\s)\b([A-Za-z_]\w*)(?=\s*\()")
        self._pat_var   = re.compile(r"\b([A-Za-z_]\w*)\s*=(?!=)")
        self._pat_self_attr = re.compile(r"\bself\.([A-Za-z_]\w*)")
        self._pat_self = re.compile(r"\bself\b")

    # UI setup
    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("ToolBar.TFrame", background=self.theme.get("editor_bg", "#1C1B21"))
        style.configure("SideBar.TFrame", background="#25232A")
        style.configure("Round.TButton", background="#25232A", foreground=self.theme.get("editor_fg", "#D8D8D8"), borderwidth=0, padding=6)
        style.map("Round.TButton", background=[("active", "#3A3A4A")])
        style.configure("TScrollbar", troughcolor=self.theme.get("scrollbar_trough"), background=self.theme.get("scrollbar_slider"),
                        arrowcolor=self.theme.get("editor_fg"), relief="flat", borderwidth=0)
        style.map("TScrollbar", background=[("active", self.theme.get("accent"))])
        style.configure("Dark.TEntry", fieldbackground=self.theme.get("ln_bg"), foreground=self.theme.get("editor_fg"), borderwidth=0)

    def _build_ui(self):
        toolbar = ttk.Frame(self, style="ToolBar.TFrame")
        toolbar.grid(row=0, column=0, columnspan=6, sticky="ew")

        file_mb = ttk.Menubutton(toolbar, text="📂 File", style="Round.TButton")
        fm = tk.Menu(file_mb, tearoff=0, bg="#25232A", fg=self.theme.get("editor_fg"))
        fm.add_command(label="Open   Ctrl+O", command=self._open_file)
        fm.add_command(label="Save   Ctrl+S", command=self._save_file)
        fm.add_command(label="Save As", command=self._save_as_file)
        fm.add_separator()
        fm.add_command(label="Exit", command=self.quit)
        file_mb["menu"] = fm
        file_mb.pack(side="left", padx=4, pady=4)

        ttk.Button(toolbar, text="🗂 Filebar", style="Round.TButton", command=self._toggle_filebar).pack(side="left", padx=4, pady=4)

        lang_mb = ttk.Menubutton(toolbar, text="🧩 Language", style="Round.TButton")
        lm = tk.Menu(lang_mb, tearoff=0, bg="#25232A", fg=self.theme.get("editor_fg"))
        lm.add_command(label="Scan configs/ folder", command=lambda: (self.config_manager.scan(), messagebox.showinfo("Scan", f"Found {len(self.config_manager.available)} config(s).")))
        lm.add_command(label="Load language JSON...", command=self._menu_load_language)
        lang_mb["menu"] = lm
        lang_mb.pack(side="left", padx=4, pady=4)

        theme_mb = ttk.Menubutton(toolbar, text="🎨 Theme", style="Round.TButton")
        tm = tk.Menu(theme_mb, tearoff=0, bg="#25232A", fg=self.theme.get("editor_fg"))
        tm.add_command(label="Load Theme JSON...", command=self._menu_load_theme)
        tm.add_command(label="Reset Default Theme", command=lambda: (self.apply_theme(DEFAULT_THEME, merge=False), self._highlight_and_number()))
        theme_mb["menu"] = tm
        theme_mb.pack(side="right", padx=4, pady=4)

        ttk.Button(toolbar, text="🔎 Find", style="Round.TButton", command=self._open_find).pack(side="right", padx=4, pady=4)
        ttk.Button(toolbar, text="A+", style="Round.TButton", command=self._increase_font).pack(side="right", padx=4, pady=4)
        ttk.Button(toolbar, text="A-", style="Round.TButton", command=self._decrease_font).pack(side="right", padx=4, pady=4)

        ttk.Separator(self, orient="horizontal").grid(row=1, column=0, columnspan=6, sticky="ew", pady=2)

        # file list
        self.filebar_container = ttk.Frame(self, style="SideBar.TFrame")
        self.filebar_container.grid(row=2, column=0, sticky="ns")
        self.file_list = tk.Listbox(self.filebar_container, bg=self.theme.get("ln_bg"), fg=self.theme.get("editor_fg"), selectbackground=self.theme.get("accent"), selectforeground=self.theme.get("editor_bg"), font=("Consolas",11), bd=0, highlightthickness=0)
        self.file_list.pack(fill="both", expand=True, padx=4, pady=4)
        self.file_list.bind("<Double-1>", self._open_selected_file)

        ttk.Separator(self, orient="vertical").grid(row=2, column=1, sticky="ns", padx=2)
        ttk.Separator(self, orient="vertical").grid(row=2, column=3, sticky="ns", padx=2)

        # line numbers
        self.linenumbers = tk.Text(self, width=4, bg=self.theme.get("ln_bg"), fg=self.theme.get("ln_fg"), font=("Consolas",12), bd=0, padx=4, takefocus=0, wrap="none", state="disabled", highlightthickness=0)
        self.linenumbers.grid(row=2, column=2, sticky="ns")

        # editor area
        self.text_area = tk.Text(self, font=("Consolas",12), undo=True, bg=self.theme.get("editor_bg"), fg=self.theme.get("editor_fg"), insertbackground=self.theme.get("cursor"), selectbackground=self.theme.get("accent"), selectforeground=self.theme.get("editor_bg"), wrap="none", bd=0, relief="flat", padx=6, pady=4)
        self.text_area.grid(row=2, column=4, sticky="nsew")
        self.rowconfigure(2, weight=1)
        self.columnconfigure(4, weight=1)

        # base tags: ensure they exist
        base_tags = ["control","definition","import","exception","logic","constants","builtin","digits","symbols","paran",
                     "class_name","func_name","var_name","string","comment","module","self","self_attr", "fstring_prefix"]
        for t in base_tags:
            # configure with theme or fallback
            color = self.theme.get(t, DEFAULT_THEME.get(t, "#FFFFFF"))
            self.text_area.tag_configure(t, foreground=color)
        self.text_area.tag_configure("search", background="#44475A", foreground="#F8F8F2")
        self.text_area.tag_configure("active_line", background="#272728")

        # scrollbars
        vs = ttk.Scrollbar(self, orient="vertical", style="TScrollbar", command=self._on_vscroll)
        vs.grid(row=2, column=5, sticky="ns")
        self.text_area.config(yscrollcommand=vs.set)
        self.linenumbers.config(yscrollcommand=vs.set)

        hs = ttk.Scrollbar(self, orient="horizontal", style="TScrollbar", command=self.text_area.xview)
        hs.grid(row=3, column=2, columnspan=3, sticky="ew")
        self.text_area.config(xscrollcommand=hs.set)

        # events
        self.text_area.bind("<KeyRelease>", lambda e: (self._schedule_highlight(), self._highlight_current_line()))
        self.text_area.bind("<ButtonRelease-1>", lambda e: self._highlight_current_line())
        self.text_area.bind("<MouseWheel>", self._on_mousewheel)
        self.text_area.bind("<Button-4>", self._on_mousewheel)
        self.text_area.bind("<Button-5>", self._on_mousewheel)

        # find dialog state & font object
        self.search_win = None
        self._font = tkfont.Font(font=self.text_area["font"])

    # ensure tags exist and set colors
    def ensure_tags(self, tags_iterable):
        for tag in tags_iterable:
            color = self.theme.get(tag, DEFAULT_THEME.get(tag, "#FFFFFF"))
            try:
                self.text_area.tag_configure(tag, foreground=color)
            except Exception:
                pass

    # apply theme
    def apply_theme(self, theme_dict, merge=True):

        if not isinstance(theme_dict, dict):
            return
        if merge:
            self.theme.update(theme_dict)
        else:
            self.theme = dict(DEFAULT_THEME)
            self.theme.update(theme_dict)

        # update UI color vars
        self.editor_bg = self.theme.get("editor_bg", self.editor_bg)
        self.editor_fg = self.theme.get("editor_fg", self.editor_fg)
        self.ln_bg = self.theme.get("ln_bg", self.ln_bg)
        self.ln_fg = self.theme.get("ln_fg", self.ln_fg)
        self.accent = self.theme.get("accent", self.accent)
        self.cursor = self.theme.get("cursor", self.cursor)

        # apply editor colorings
        try:
            self.configure(bg=self.editor_bg)
            self.text_area.config(bg=self.editor_bg, fg=self.editor_fg, insertbackground=self.cursor, selectbackground=self.accent, selectforeground=self.editor_bg)
            self.linenumbers.config(bg=self.ln_bg, fg=self.ln_fg)
            self.file_list.config(bg=self.ln_bg, fg=self.editor_fg, selectbackground=self.accent, selectforeground=self.editor_bg)
            self._setup_style()
        except Exception:
            pass

        self.ensure_tags(set(list(self.theme.keys())))

    # load language config
    def load_language_config(self, cfg):
        try:
            if not isinstance(cfg, dict):
                raise ValueError("Language config must be a dict")
            # copy to avoid mutation
            self.lang_config = dict(cfg)
            ltype = self.lang_config.get("type", "regex")
            self.lang_patterns = []
            self.lang_keywords = {}

            # compile regex patterns
            if ltype == "regex":
                for p in self.lang_config.get("patterns", []):
                    regex = p.get("regex")
                    tag = p.get("tag")
                    group = int(p.get("group", 0)) if p.get("group", 0) else 0
                    flags = 0
                    fstr = p.get("flags", "") or ""
                    if "i" in fstr: flags |= re.IGNORECASE
                    if "m" in fstr: flags |= re.MULTILINE
                    if "s" in fstr: flags |= re.DOTALL
                    try:
                        cre = re.compile(regex, flags)
                        self.lang_patterns.append((tag, cre, group))
                    except Exception as ex:
                        print("[load_language_config] bad regex:", regex, ex)
                for tag, words in self.lang_config.get("keywords", {}).items():
                    if isinstance(words, (list,tuple,set)):
                        self.lang_keywords[tag] = set(words)
            elif ltype == "python":
                # python: optional keywords as fallback
                kws = self.lang_config.get("keywords", {})
                for tag, words in kws.items():
                    if isinstance(words, (list,tuple,set)):
                        self.lang_keywords[tag] = set(words)

            # add tags for keywords & pattern tags and base tags
            tags_used = set(self.lang_keywords.keys())
            for tpl in self.lang_patterns:
                tags_used.add(tpl[0])
            base = {"control","definition","import","exception","logic","constants","builtin","digits","symbols","paran",
                    "class_name","func_name","var_name","string","comment","module","self","self_attr", "fstring_prefix"}
            tags_used.update(base)
            self.ensure_tags(tags_used)

            if "theme" in self.lang_config and isinstance(self.lang_config["theme"], dict):
                self.apply_theme(self.lang_config["theme"], merge=True)
            elif "colors" in self.lang_config and isinstance(self.lang_config["colors"], dict):
                self.apply_theme(self.lang_config["colors"], merge=True)
        except Exception as ex:
            messagebox.showerror("Error", f"Failed to load language config: {ex}")

    # highlight engine
    def _get_token_spans(self, txt):
        string_spans, comment_spans = [], []
        if not txt:
            return string_spans, comment_spans
        lines = txt.splitlines(keepends=True)
        offsets = []; off = 0
        for ln in lines:
            offsets.append(off); off += len(ln)
        def abs_index(pos):
            r,c = pos
            if r-1 >= len(offsets): return len(txt)
            return offsets[r-1] + c
        try:
            for tok in tokenize.generate_tokens(io.StringIO(txt).readline):
                if tok.type == tokenize.STRING:
                    s = abs_index(tok.start); e = abs_index(tok.end)
                    string_spans.append((s,e))
                elif tok.type == tokenize.COMMENT:
                    s = abs_index(tok.start); e = abs_index(tok.end)
                    comment_spans.append((s,e))
        except (tokenize.TokenError, IndentationError):
            pass
        return string_spans, comment_spans

    def _clear_syntax_tags(self):
        for tag in list(self.text_area.tag_names()):
            if tag in ("search","active_line"): continue
            self.text_area.tag_remove(tag, "1.0", tk.END)

    def _highlight_and_number(self):
        txt = self.text_area.get("1.0", "end-1c")
        lang_type = (self.lang_config.get("type") if self.lang_config else "python")
        string_spans, comment_spans = (self._get_token_spans(txt) if lang_type == "python" else ([],[]))

        def in_span(i, spans):
            return any(s <= i < e for s,e in spans)

        self._clear_syntax_tags()

        # strings & comments first
        for s,e in string_spans: self.text_area.tag_add("string", f"1.0+{s}c", f"1.0+{e}c")
        for s,e in comment_spans: self.text_area.tag_add("comment", f"1.0+{s}c", f"1.0+{e}c")

        if lang_type == "python":
            self._tokenize_and_apply_structures(txt)
        else:
            # regex patterns
            for tag, cre, group in self.lang_patterns:
                for m in cre.finditer(txt):
                    if group and m.lastindex and group <= m.lastindex:
                        s, e = m.start(group), m.end(group)
                    else:
                        s, e = m.start(), m.end()
                    if in_span(s, string_spans) or in_span(s, comment_spans): continue
                    self.text_area.tag_add(tag, f"1.0+{s}c", f"1.0+{e}c")
            # keywords
            for tag, words in self.lang_keywords.items():
                if not words: continue
                pattern = r"\b(?:" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r")\b"
                for m in re.finditer(pattern, txt):
                    s, e = m.start(), m.end()
                    if in_span(s, string_spans) or in_span(s, comment_spans): continue
                    self.text_area.tag_add(tag, f"1.0+{s}c", f"1.0+{e}c")
            # fallback constructs
            for m in self._pat_class.finditer(txt):
                i = m.start(1)
                if in_span(i, string_spans) or in_span(i, comment_spans): continue
                self.text_area.tag_add("class_name", f"1.0+{i}c", f"1.0+{m.end(1)}c")
            for m in self._pat_def.finditer(txt):
                i = m.start(1)
                if in_span(i, string_spans) or in_span(i, comment_spans): continue
                self.text_area.tag_add("func_name", f"1.0+{i}c", f"1.0+{m.end(1)}c")
            for m in self._pat_call.finditer(txt):
                i = m.start(1)
                if in_span(i, string_spans) or in_span(i, comment_spans): continue
                self.text_area.tag_add("func_name", f"1.0+{i}c", f"1.0+{m.end(1)}c")
            for m in self._pat_var.finditer(txt):
                i = m.start(1)
                if in_span(i, string_spans) or in_span(i, comment_spans): continue
                self.text_area.tag_add("var_name", f"1.0+{i}c", f"1.0+{m.end(1)}c")

        # update line numbers
        total = int(self.text_area.index("end-1c").split(".")[0])
        nums = "\n".join(str(i) for i in range(1, total+1)) + "\n"
        self.linenumbers.config(state="normal")
        self.linenumbers.delete("1.0", tk.END)
        self.linenumbers.insert("1.0", nums)
        self.linenumbers.config(state="disabled")

        self._highlight_job = None
        self._highlight_current_line()

    def _tokenize_and_apply_structures(self, txt):
        if not txt: return
        lines = txt.splitlines(keepends=True)
        offsets = []
        off = 0
        for ln in lines:
            offsets.append(off); off += len(ln)
        def abs_idx(pos):
            r,c = pos
            if r-1 >= len(offsets): return len(txt)
            return offsets[r-1] + c
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(txt).readline))
        except Exception:
            tokens = []
        n = len(tokens)
        def next_sig(i):
            j = i+1
            while j < n:
                if tokens[j].type not in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER):
                    return j
                j += 1
            return None

        for i, tok in enumerate(tokens):
            ttype, tstr = tok.type, tok.string
            sidx = abs_idx(tok.start); eidx = abs_idx(tok.end)

            if ttype == tokenize.STRING:
                # Handle f-string prefix
                if tstr.startswith(('f"', "f'", 'F"', "F'")):
                    self.text_area.tag_add("fstring_prefix", f"1.0+{sidx}c", f"1.0+{sidx+1}c")
                    self.text_area.tag_add("string", f"1.0+{sidx+1}c", f"1.0+{eidx}c")
                else:
                    self.text_area.tag_add("string", f"1.0+{sidx}c", f"1.0+{eidx}c")
            elif ttype == tokenize.COMMENT:
                self.text_area.tag_add("comment", f"1.0+{sidx}c", f"1.0+{eidx}c")
            elif ttype == tokenize.NAME:
                if tstr == "def":
                    j = next_sig(i)
                    if j and tokens[j].type == tokenize.NAME:
                        fn_s = abs_idx(tokens[j].start); fn_e = abs_idx(tokens[j].end)
                        self.text_area.tag_add("func_name", f"1.0+{fn_s}c", f"1.0+{fn_e}c")
                        # params
                        k = j+1
                        while k < n and tokens[k].string != "(":
                            k += 1
                        if k < n and tokens[k].string == "(":
                            depth = 0; m = k
                            while m < n:
                                tt = tokens[m]
                                if tt.string == "(":
                                    depth += 1
                                elif tt.string == ")":
                                    depth -= 1
                                    if depth == 0: break
                                if depth > 0 and tt.type == tokenize.NAME:
                                    ns = abs_idx(tt.start); ne = abs_idx(tt.end)
                                    self.text_area.tag_add("var_name", f"1.0+{ns}c", f"1.0+{ne}c")
                                m += 1
                    continue
                if tstr == "class":
                    j = next_sig(i)
                    if j and tokens[j].type == tokenize.NAME:
                        cs = abs_idx(tokens[j].start); ce = abs_idx(tokens[j].end)
                        self.text_area.tag_add("class_name", f"1.0+{cs}c", f"1.0+{ce}c")
                    continue
                if tstr == "import":
                    j = next_sig(i)
                    while j and tokens[j].type != tokenize.NEWLINE and tokens[j].string != ";":
                        if tokens[j].type == tokenize.NAME:
                            start_pos = abs_idx(tokens[j].start); end_pos = abs_idx(tokens[j].end)
                            k = j+1
                            while k+1 < n and tokens[k].string == "." and tokens[k+1].type == tokenize.NAME:
                                end_pos = abs_idx(tokens[k+1].end); k += 2
                            self.text_area.tag_add("module", f"1.0+{start_pos}c", f"1.0+{end_pos}c")
                            j = k
                        else:
                            j = next_sig(j)
                    continue
                if tstr == "from":
                    j = next_sig(i)
                    if j and tokens[j].type == tokenize.NAME:
                        start_pos = abs_idx(tokens[j].start); end_pos = abs_idx(tokens[j].end)
                        k = j+1
                        while k+1 < n and tokens[k].string == "." and tokens[k+1].type == tokenize.NAME:
                            end_pos = abs_idx(tokens[k+1].end); k += 2
                        self.text_area.tag_add("module", f"1.0+{start_pos}c", f"1.0+{end_pos}c")
                        # imported names
                        l = k
                        while l < n and tokens[l].string != "import": l += 1
                        if l < n and tokens[l].string == "import":
                            m = l+1
                            while m < n and tokens[m].type != tokenize.NEWLINE and tokens[m].string != ";":
                                if tokens[m].type == tokenize.NAME:
                                    is_ = abs_idx(tokens[m].start); ie_ = abs_idx(tokens[m].end)
                                    self.text_area.tag_add("module", f"1.0+{is_}c", f"1.0+{ie_}c")
                                m += 1
                    continue
                if tstr == "self":
                    if i+2 < n and tokens[i+1].string == "." and tokens[i+2].type == tokenize.NAME:
                        attr = tokens[i+2]; a_s = abs_idx(attr.start); a_e = abs_idx(attr.end)
                        self.text_area.tag_add("self", f"1.0+{sidx}c", f"1.0+{eidx}c")
                        self.text_area.tag_add("self_attr", f"1.0+{a_s}c", f"1.0+{a_e}c")
                    else:
                        self.text_area.tag_add("self", f"1.0+{sidx}c", f"1.0+{eidx}c")
                    continue
                # call detection
                nj = next_sig(i)
                if nj and tokens[nj].type == tokenize.OP and tokens[nj].string == "(":
                    self.text_area.tag_add("func_name", f"1.0+{sidx}c", f"1.0+{eidx}c")
                    continue
                # assignment
                if nj and tokens[nj].type == tokenize.OP and tokens[nj].string == "=":
                    self.text_area.tag_add("var_name", f"1.0+{sidx}c", f"1.0+{eidx}c")
                    continue
                # keywords from config
                for tag, words in self.lang_keywords.items():
                    if isinstance(words, (set, list, tuple)) and tstr in words:
                        self.text_area.tag_add(tag, f"1.0+{sidx}c", f"1.0+{eidx}c")
                        break
    
    # scheduling highlight
    def _schedule_highlight(self):
        if self._highlight_job:
            self.after_cancel(self._highlight_job)
        self._highlight_job = self.after(200, self._highlight_and_number)

    def _highlight_current_line(self, event=None):
        self.text_area.tag_remove("active_line", "1.0", tk.END)
        ls = self.text_area.index("insert linestart")
        le = self.text_area.index("insert lineend +1c")
        self.text_area.tag_add("active_line", ls, le)

    # file list & open/save
    def _populate_file_list(self):
        self.file_list.delete(0, tk.END)
        for fn in sorted(os.listdir(".")):
            if os.path.isfile(fn):
                self.file_list.insert(tk.END, fn)

    def _toggle_filebar(self):
        if self.filebar_container.winfo_viewable():
            self.filebar_container.grid_remove()
        else:
            self.filebar_container.grid()
            self._populate_file_list()

    def _open_file(self):
        p = filedialog.askopenfilename(filetypes=[("All files","*.*")])
        if p: self._load_path(p)

    def _open_selected_file(self, e):
        sel = self.file_list.curselection()
        if sel: self._load_path(self.file_list.get(sel[0]))

    def _load_path(self, path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                txt = fh.read()
        except Exception as ex:
            messagebox.showerror("Error", f"Failed to open file: {ex}")
            return
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", txt)
        self.file_path = path
        self._populate_file_list()
        
        cfg = self.config_manager.detect_for_path(path)
        if not cfg:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".py":
                cfg = {"name":"Python (builtin)", "type":"python", "extensions":[".py"], "keywords":{}}
        
        if cfg:
            self.load_language_config(cfg)
        self._highlight_and_number()

    def _save_file(self):
        if not self.file_path:
            self._save_as_file()
            return
        try:
            with open(self.file_path, "w", encoding="utf-8") as fh:
                fh.write(self.text_area.get("1.0", "end-1c"))
            self._populate_file_list()
        except Exception as ex:
            messagebox.showerror("Error", f"Failed to save file: {ex}")

    def _save_as_file(self):
        ext = ".txt"
        if self.lang_config and self.lang_config.get("extensions"):
            ext = self.lang_config["extensions"][0]
        
        p = filedialog.asksaveasfilename(defaultextension=ext)
        if not p: return
        try:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(self.text_area.get("1.0", "end-1c"))
            self.file_path = p
            self.title(f"DamEdit — {os.path.basename(p)}")
            self._populate_file_list()
        except Exception as ex:
            messagebox.showerror("Error", f"Failed to save file: {ex}")

    # menus to load theme/language
    def _menu_load_language(self):
        p = filedialog.askopenfilename(title="Load language JSON", filetypes=[("JSON","*.json")])
        if not p: return
        try:
            with open(p, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
            self.load_language_config(cfg)
            self._highlight_and_number()
            messagebox.showinfo("Loaded", f"Language: {cfg.get('name','<unnamed>')}")
        except Exception as ex:
            messagebox.showerror("Error", f"Failed to load language JSON: {ex}")

    def _menu_load_theme(self):
        p = filedialog.askopenfilename(title="Load theme JSON", filetypes=[("JSON","*.json")])
        if not p: return
        try:
            with open(p, "r", encoding="utf-8") as fh:
                theme = json.load(fh)
            self.apply_theme(theme, merge=True)
            self._highlight_and_number()
            messagebox.showinfo("Theme", f"Theme loaded from {os.path.basename(p)}")
        except Exception as ex:
            messagebox.showerror("Error", f"Failed to load theme JSON: {ex}")

    # find dialog & helpers
    def _open_find(self):
        if self.search_win:
            self.search_win.lift(); return
        self.search_win = tk.Toplevel(self)
        self.search_win.title("Find"); self.search_win.transient(self); self.search_win.resizable(False, False); self.search_win.iconbitmap("assets\\DamEdit.ico")
        self.search_win.protocol("WM_DELETE_WINDOW", self._close_find)
        frame = ttk.Frame(self.search_win, style="SideBar.TFrame")
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        ttk.Label(frame, text="🔍 Find:", background=self.theme.get("ln_bg"), foreground=self.theme.get("editor_fg")).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.find_entry = ttk.Entry(frame, width=30, style="Dark.TEntry")
        self.find_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        frame.columnconfigure(1, weight=1)
        self.find_entry.focus()
        self.find_entry.bind("<Return>", lambda e: self._find_next())
        self.find_entry.bind("<Shift-Return>", lambda e: self._find_prev())
        self.find_entry.bind("<Escape>", lambda e: self._close_find())
        btns = ttk.Frame(frame, style="SideBar.TFrame")
        btns.grid(row=1, column=0, columnspan=2, pady=(4,0))
        ttk.Button(btns, text="◀ Prev", style="Round.TButton", command=self._find_prev).pack(side="left", padx=2)
        ttk.Button(btns, text="Next ▶", style="Round.TButton", command=self._find_next).pack(side="left", padx=2)
        ttk.Button(btns, text="✖ Close", style="Round.TButton", command=self._close_find).pack(side="left", padx=2)

    def _close_find(self):
        if not self.search_win: return
        self.text_area.tag_remove("search", "1.0", tk.END)
        self.search_win.destroy(); self.search_win = None

    def _find_next(self):
        pat = self.find_entry.get()
        if not pat: return
        self.text_area.tag_remove("search", "1.0", tk.END)
        start = self.text_area.index("insert +1c")
        idx = self.text_area.search(pat, start, tk.END, nocase=True)
        if not idx:
            idx = self.text_area.search(pat, "1.0", start, nocase=True)
        if idx:
            end = f"{idx}+{len(pat)}c"
            self.text_area.tag_add("search", idx, end)
            self.text_area.mark_set("insert", end)
            self.text_area.see(idx)

    def _find_prev(self):
        pat = self.find_entry.get()
        if not pat: return
        self.text_area.tag_remove("search", "1.0", tk.END)
        curr = self.text_area.index("insert")
        idx = self.text_area.search(pat, "1.0", curr, backwards=True, nocase=True)
        if idx:
            end = f"{idx}+{len(pat)}c"
            self.text_area.tag_add("search", idx, end)
            self.text_area.mark_set("insert", idx)
            self.text_area.see(idx)

    # scrolling & font
    def _on_vscroll(self, *args):
        self.text_area.yview(*args); self.linenumbers.yview(*args)

    def _on_mousewheel(self, event):
        if hasattr(event, "delta"):
            delta = int(-1*(event.delta/120))
        else:
            delta = 1 if event.num == 5 else -1
        self.text_area.yview_scroll(delta, "units")
        self.linenumbers.yview_scroll(delta, "units")
        return "break"

    def _increase_font(self):
        size = max(6, self._font['size'] + 2); self._font.config(size=size)
        self.text_area.config(font=self._font); self.linenumbers.config(font=(self._font.actual('family'), self._font.actual('size')))

    def _decrease_font(self):
        size = max(6, self._font['size'] - 2); self._font.config(size=size)
        self.text_area.config(font=self._font); self.linenumbers.config(font=(self._font.actual('family'), self._font.actual('size')))

    # shortcuts
    def _bind_shortcuts(self):
        self.bind_all("<Control-o>", lambda e: self._open_file())
        self.bind_all("<Control-s>", lambda e: self._save_file())
        self.bind_all("<Control-f>", lambda e: self._open_find())
        self.bind_all("<Control-plus>", lambda e: self._increase_font())
        self.bind_all("<Control-equal>", lambda e: self._increase_font())
        self.bind_all("<Control-minus>", lambda e: self._decrease_font())

# run
def main():
    app = ConfigEditor()
    app.mainloop()

if __name__ == "__main__":

    main()
