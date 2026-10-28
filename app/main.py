# -*- coding: utf-8 -*-
"""Violet Mod Maker — мод своей музыки для второй способности Violet.

Дизайн: Deadlock noir / art-deco (DESIGN.md): угольный фон, латунь, янтарь,
скруглённые карточки, кастомный тайтл-бар, лого-рендер машины.
Сборка: трек, секунда начала лупа, громкость (LUFS, шаг 1, дефолт -10),
модель (Классика / Машина), сохранение через диалог (по умолчанию pak99_dir.vpk).
"""
import ctypes
import os
import sys
import threading
import traceback

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

SOUND_PATH = "sounds/abilities/artist/dubai_chorus_lp.vsnd_c"
SOUNDEVENT_PATH = "soundevents/hero/artist.vsndevts_c"

# ---- Deadlock palette (DESIGN.md)
COL_ABYSS = "#11100F"
COL_SURFACE = "#1A1817"
COL_ELEVATED = "#24211E"
COL_TEXT = "#EAE3D2"
COL_TEXT2 = "#A69F91"
COL_MUTED = "#6E685F"
COL_INV = "#11100F"
COL_BRASS = "#C89D54"
COL_AMBER = "#E58A2E"
COL_AMBER_HI = "#F0983E"
COL_OCCULT = "#45B8AC"
COL_BORDER = "#332E2A"
COL_CRIMSON = "#C93B2B"
COL_VITAL = "#6B9E47"

WIN_W = 640

I18N = {
    "ru": {
        "title": "VIOLET MOD MAKER",
        "subtitle": "Своя музыка для второй способности Violet",
        "track": "ТРЕК",
        "loop": "НАЧАЛО ЛУПА, СЕКУНДА",
        "loop_hint": "Мод играет этот кусок по кругу: поставь секунду, с которой начинается "
                     "нужная часть трека",
        "preview": "ПРОСЛУШАТЬ ФРАГМЕНТ",
        "volume": "ГРОМКОСТЬ",
        "recommended": "рекомендовано",
        "model": "МОДЕЛЬ",
        "preset_classic": "Классика (ванильная щётка)",
        "preset_car": "Машина",
        "build": "СОБРАТЬ МОД",
        "building": "СОБИРАЮ…",
        "save_title": "Куда сохранить мод",
        "save_default": "pak99_dir.vpk",
        "status_track": "Читаю трек…",
        "status_loop": "Собираю луп (громкость %d LUFS)…",
        "status_vpk": "Собираю VPK…",
        "done": "◆  Готово: %s",
        "err_track": "Не удалось открыть трек:\n%s",
        "err_start": "Секунда начала — число, например 28.5",
        "need_track": "Сначала выбери трек.",
        "preview_open": "Фрагмент открыт в плеере по умолчанию (76 секунд).",
        "preview_prepare": "Готовлю фрагмент для прослушивания…",
        "err_title": "Ошибка",
        "info_title": "Violet Mod Maker",
        "cancel": "Отменено",
    },
    "en": {
        "title": "VIOLET MOD MAKER",
        "subtitle": "Custom music for Violet's ability 2",
        "track": "TRACK",
        "loop": "LOOP START, SECOND",
        "loop_hint": "The mod plays this part in a loop: set the second where the section "
                     "you want starts",
        "preview": "PREVIEW THE LOOP",
        "volume": "VOLUME",
        "recommended": "recommended",
        "model": "MODEL",
        "preset_classic": "Classic (vanilla brush)",
        "preset_car": "Car",
        "build": "BUILD MOD",
        "building": "BUILDING…",
        "save_title": "Where to save the mod",
        "save_default": "pak99_dir.vpk",
        "status_track": "Reading the track…",
        "status_loop": "Building the loop (volume %d LUFS)…",
        "status_vpk": "Packing the VPK…",
        "done": "◆  Done: %s",
        "err_track": "Could not open the track:\n%s",
        "err_start": "Loop start must be a number, e.g. 28.5",
        "need_track": "Pick a track first.",
        "preview_open": "The loop opened in your default player (76 seconds).",
        "preview_prepare": "Preparing the preview…",
        "err_title": "Error",
        "info_title": "Violet Mod Maker",
        "cancel": "Cancelled",
    },
}


def res_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def find_game_addons():
    candidates = [
        r"C:\Program Files (x86)\Steam\steamapps\common\Deadlock\game\citadel\addons",
        r"C:\Program Files\Steam\steamapps\common\Deadlock\game\citadel\addons",
        os.path.expandvars(r"%D%\Steam\steamapps\common\Deadlock\game\citadel\addons"),
        os.path.expanduser(r"~/Steam/steamapps/common/Deadlock/game/citadel/addons"),
    ]
    try:
        cfg = r"C:\Program Files (x86)\Steam\config\libraryfolders.vdf"
        import re
        text = open(cfg, encoding="utf-8", errors="ignore").read()
        for m in re.finditer(r'"path"\s+"([^"]+)"', text):
            p = m.group(1).replace("\\\\", "\\") + r"\steamapps\common\Deadlock\game\citadel\addons"
            if p not in candidates:
                candidates.append(p)
    except Exception:
        pass
    for p in candidates:
        if os.path.isdir(p):
            return p
    return None


def list_presets(lang="ru"):
    t = I18N[lang]
    out = [(t["preset_classic"], "classic"), (t["preset_car"], "car")]
    root = res_path("presets")
    if os.path.isdir(root):
        for name in sorted(os.listdir(root)):
            full = os.path.join(root, name)
            if name.startswith("_") or name == "car" or not os.path.isdir(full):
                continue
            has_files = any(f.endswith("_c") for _, _, fs in os.walk(full) for f in fs)
            if has_files:
                out.append((name, name))
    return out


def round_poly(cv, x0, y0, x1, y1, r, **kw):
    pts = [x0+r, y0, x1-r, y0, x1, y0, x1, y0+r, x1, y1-r, x1, y1,
           x1-r, y1, x0+r, y1, x0, y1, x0, y1-r, x0, y0+r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


class App:
    def __init__(self, root):
        self.root = root
        root.overrideredirect(True)
        root.configure(bg=COL_ABYSS)
        self.lang = "en"
        self.track = tk.StringVar()
        self.start = tk.StringVar(value="0")
        self.lufs = tk.IntVar(value=-10)
        self.preset = tk.StringVar(value="car")
        self.building = False
        self._style()
        self._build_ui()
        self._center()
        self._round_corners()

    # ------------------------------------------------------------ window
    def _center(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry("+%d+%d" % ((sw - w) // 2, max(0, (sh - h) // 3)))
        # appear above whatever is open, but don't stay forced on top
        self.root.attributes("-topmost", True)
        self.root.after(600, lambda: self.root.attributes("-topmost", False))

    def _round_corners(self):
        try:
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetAncestor(self.root.winfo_id(), 2)  # GA_ROOT
            if not hwnd:
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            pref = ctypes.c_int(2)          # DWMWCP_ROUND
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(pref), 4)
            # WS_EX_APPWINDOW so the borderless window still lands in the taskbar
            style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, -20)
            ctypes.windll.user32.SetWindowLongPtrW(hwnd, -20, style | 0x00040000)
            # frame change notification so the shell picks up the new style
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                              0x0001 | 0x0002 | 0x0004 | 0x0020)
            self.root.after(300, lambda: ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4))
        except Exception:
            pass

    def _start_move(self, e):
        self._dx = e.x
        self._dy = e.y

    def _do_move(self, e):
        self.root.geometry("+%d+%d" % (e.x_root - self._dx, e.y_root - self._dy))

    def _minimize(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            ctypes.windll.user32.ShowWindow(hwnd, 6)   # SW_MINIMIZE
        except Exception:
            self.root.iconify()

    # ------------------------------------------------------------ style
    def _style(self):
        st = ttk.Style(self.root)
        st.theme_use("clam")
        st.configure(".", background=COL_SURFACE, foreground=COL_TEXT,
                     font=("Segoe UI", 10), bordercolor=COL_BORDER)
        st.configure("TEntry", fieldbackground=COL_ABYSS, foreground=COL_TEXT,
                     insertcolor=COL_TEXT, bordercolor=COL_BORDER,
                     lightcolor=COL_BRASS, darkcolor=COL_BRASS,
                     borderwidth=1, padding=5)
        st.configure("Deco.Horizontal.TScale", troughcolor=COL_ELEVATED,
                     background=COL_BRASS, bordercolor=COL_BORDER, lightcolor=COL_BRASS,
                     darkcolor=COL_BRASS, gripcount=0)

    # ------------------------------------------------------------ pieces
    def _ghost(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd, bg=COL_ELEVATED, fg=COL_TEXT,
                         activebackground="#3a352e", activeforeground=COL_TEXT,
                         relief="flat", bd=0, highlightthickness=1,
                         highlightbackground=COL_BRASS, highlightcolor=COL_BRASS,
                         font=("Segoe UI", 9, "bold"), cursor="hand2")

    def _card(self, parent, title, height):
        """A rounded card on a canvas; returns the content frame inside it."""
        cv = tk.Canvas(parent, width=WIN_W - 36, height=height,
                       bg=COL_ABYSS, highlightthickness=0, bd=0)
        cv.pack(padx=18, pady=7)
        round_poly(cv, 1, 1, WIN_W - 38, height - 2, 14,
                   fill=COL_SURFACE, outline=COL_BORDER, width=1)
        # brass accent line + diamond title
        cv.create_line(14, 12, WIN_W - 52, 12, fill=COL_BRASS, width=1)
        cv.create_text(14, 26, text="◆  " + title, anchor="w",
                       fill=COL_BRASS, font=("Segoe UI Semibold", 10, "bold"))
        body = tk.Frame(cv, bg=COL_SURFACE)
        cv.create_window(16, 44, window=body, anchor="nw",
                         width=WIN_W - 70, height=height - 56)
        return body

    # ------------------------------------------------------------ ui
    def _build_ui(self):
        t = I18N[self.lang]
        for w in self.root.winfo_children():
            w.destroy()

        # ---- custom title bar
        bar = tk.Frame(self.root, bg=COL_ABYSS, height=42)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        try:
            self._logo_img = tk.PhotoImage(file=res_path("logo.png")).subsample(24, 24)
            tk.Label(bar, image=self._logo_img, bg=COL_ABYSS).pack(side="left", padx=(14, 8))
        except Exception:
            pass
        tbox = tk.Frame(bar, bg=COL_ABYSS)
        tbox.pack(side="left")
        tk.Label(tbox, text=t["title"], bg=COL_ABYSS, fg=COL_BRASS,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(tbox, text=t["subtitle"], bg=COL_ABYSS, fg=COL_TEXT2,
                 font=("Segoe UI", 8)).pack(anchor="w")
        # window buttons: close is rightmost, minimize next, languages left of them
        tk.Button(bar, text="✕", command=self.root.destroy, width=4,
                  bg=COL_ABYSS, fg=COL_TEXT2, activebackground=COL_CRIMSON,
                  activeforeground="white", relief="flat", bd=0,
                  font=("Segoe UI", 10), cursor="hand2")            .pack(side="right", fill="y", padx=(2, 4))
        tk.Button(bar, text="—", command=self._minimize, width=4,
                  bg=COL_ABYSS, fg=COL_TEXT2, activebackground=COL_ELEVATED,
                  activeforeground=COL_TEXT, relief="flat", bd=0,
                  font=("Segoe UI", 10), cursor="hand2")            .pack(side="right", fill="y", padx=2)
        langbox = tk.Frame(bar, bg=COL_ABYSS)
        langbox.pack(side="right", padx=(0, 4))
        for code, label in (("ru", "RU"), ("en", "EN")):
            cur = self.lang == code
            tk.Button(langbox, text=label, command=lambda c=code: self._set_lang(c),
                      bg=COL_ELEVATED if cur else COL_ABYSS,
                      fg=COL_BRASS if cur else COL_MUTED,
                      activebackground=COL_ELEVATED, activeforeground=COL_BRASS,
                      relief="flat", bd=0, highlightthickness=1,
                      highlightbackground=COL_BORDER, highlightcolor=COL_BORDER,
                      padx=8, pady=4, font=("Segoe UI", 8, "bold"), cursor="hand2")                .pack(side="left", padx=3)
        for w in (bar, tbox):
            w.bind("<Button-1>", self._start_move)
            w.bind("<B1-Motion>", self._do_move)

        # ---- cards
        body = tk.Frame(self.root, bg=COL_ABYSS)
        body.pack(fill="x")

        c = self._card(body, "1 · " + t["track"], 132)
        ttk.Entry(c, textvariable=self.track, width=44, state="readonly",
                  style="TEntry", font=("Segoe UI", 10))\
            .grid(row=0, column=0, sticky="we", ipady=3)
        self._ghost(c, "…", self.pick_track).grid(row=0, column=1, padx=(10, 0))
        self._ghost(c, t["preview"], self.preview).grid(row=1, column=0, sticky="w",
                                                        pady=(10, 0))

        c = self._card(body, "2 · " + t["loop"], 138)
        ttk.Entry(c, textvariable=self.start, width=8, style="TEntry",
                  font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", ipady=3)
        tk.Label(c, text=t["loop_hint"], bg=COL_SURFACE, fg=COL_TEXT2,
                 font=("Segoe UI", 9), wraplength=440, justify="left")\
            .grid(row=1, column=0, sticky="w", pady=(9, 0))

        c = self._card(body, "3 · " + t["volume"], 92)
        mid = tk.Frame(c, bg=COL_SURFACE)
        mid.pack(fill="x", pady=(2, 0))
        ttk.Scale(mid, from_=-25, to=0, variable=self.lufs, length=330,
                  style="Deco.Horizontal.TScale", command=self._lufs_changed)\
            .pack(side="left", fill="x", expand=True)
        self.lufs_val = tk.Label(mid, text="", bg=COL_SURFACE, fg=COL_BRASS,
                                 font=("Consolas", 11, "bold"), width=10, anchor="w")
        self.lufs_val.pack(side="left")
        self.lufs_reco = tk.Label(mid, text="◆ " + t["recommended"], bg=COL_SURFACE,
                                  fg=COL_SURFACE, font=("Segoe UI", 9))
        self.lufs_reco.pack(side="left")
        self._lufs_changed()

        c = self._card(body, "4 · " + t["model"], 84)
        box = tk.Frame(c, bg=COL_SURFACE)
        box.pack(anchor="w", pady=(2, 0))
        for i, (label, val) in enumerate(list_presets(self.lang)):
            tk.Radiobutton(box, text=label, value=val, variable=self.preset,
                           bg=COL_SURFACE, fg=COL_TEXT,
                           activebackground=COL_SURFACE, activeforeground=COL_AMBER,
                           selectcolor=COL_ABYSS, highlightthickness=0, bd=0,
                           font=("Segoe UI", 10), cursor="hand2")\
                .grid(row=0, column=i, sticky="w", padx=(0, 26))

        # ---- build + status
        bottom = tk.Frame(self.root, bg=COL_ABYSS)
        bottom.pack(fill="x", padx=18, pady=(8, 14))
        self.go = tk.Button(bottom, text=t["build"], command=self.build,
                            bg=COL_AMBER, fg=COL_INV,
                            activebackground=COL_AMBER_HI, activeforeground=COL_INV,
                            relief="flat", bd=0, highlightthickness=0,
                            font=("Segoe UI Semibold", 12, "bold"), cursor="hand2")
        self.go.pack(ipadx=80, ipady=7)
        self.status = tk.Label(bottom, text="", bg=COL_ABYSS, fg=COL_TEXT2,
                               font=("Segoe UI", 9), wraplength=WIN_W - 60,
                               justify="left")
        self.status.pack(anchor="w", pady=(9, 0))

    def _set_lang(self, code):
        self.lang = code
        self._build_ui()

    def _lufs_changed(self, *_):
        t = I18N[self.lang]
        v = int(round(self.lufs.get()))
        if abs(self.lufs.get() - v) > 1e-6:
            self.lufs.set(v)
        if hasattr(self, "lufs_val"):
            self.lufs_val.config(text="%d LUFS" % v)
            # keep the badge packed but invisible unless it applies, so the
            # layout never jumps while dragging
            self.lufs_reco.config(fg=COL_BRASS if v == -10 else COL_SURFACE)

    def pick_track(self):
        t = I18N[self.lang]
        p = filedialog.askopenfilename(
            title=t["track"],
            filetypes=[("Аудио / Audio", "*.mp3 *.wav"), ("All", "*.*")])
        if p:
            self.track.set(p)

    def _status(self, text, color=COL_TEXT2):
        self.root.after(0, lambda: self.status.config(text=text, fg=color))

    def _check(self):
        t = I18N[self.lang]
        if self.building:
            return None
        if not self.track.get():
            messagebox.showinfo(t["info_title"], t["need_track"])
            return None
        try:
            start = float(self.start.get().replace(",", "."))
            if start < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(t["err_title"], t["err_start"])
            return None
        return start

    def preview(self):
        t = I18N[self.lang]
        args = self._check()
        if not args:
            return
        try:
            self._status(t["preview_prepare"])
            import audio
            x = audio.decode(self.track.get())
            seg = audio.build_loop(x, args, self.lufs.get())
            import tempfile
            path = os.path.join(tempfile.gettempdir(), "violet_mod_preview.wav")
            open(path, "wb").write(audio.loop_to_wav_bytes(seg))
            os.startfile(path)
            self._status(t["preview_open"], COL_VITAL)
        except Exception as e:
            self._status("")
            messagebox.showerror(t["err_title"], t["err_track"] % e)

    def build(self):
        t = I18N[self.lang]
        args = self._check()
        if not args:
            return
        path = filedialog.asksaveasfilename(
            title=t["save_title"], defaultextension=".vpk",
            initialfile=t["save_default"],
            filetypes=[("VPK", "*.vpk"), ("All", "*.*")])
        if not path:
            self._status(t["cancel"])
            return
        self.building = True
        self.go.config(state="disabled", text=t["building"])
        threading.Thread(target=self._build_worker, args=(args, path), daemon=True).start()

    def _build_worker(self, start, path):
        t = I18N[self.lang]
        try:
            self._status(t["status_track"])
            import audio, vsnd, vpk
            x = audio.decode(self.track.get())
            self._status(t["status_loop"] % int(self.lufs.get()))
            seg = audio.build_loop(x, start, self.lufs.get())
            wav = audio.loop_to_wav_bytes(seg)
            pcm = wav[wav.index(b"data") + 8:]

            header = open(res_path(os.path.join("core", "_reference_header.bin")), "rb").read()
            vsnd_c = vsnd.build_vsnd_c(header, pcm, wav)
            se = open(res_path(os.path.join("core", "soundevent", "artist.vsndevts_c")), "rb").read()

            entries = {SOUND_PATH: vsnd_c, SOUNDEVENT_PATH: se}
            preset = self.preset.get()
            if preset and preset != "classic":
                root = res_path(os.path.join("presets", preset))
                for dirpath, _, files in os.walk(root):
                    for f in files:
                        full = os.path.join(dirpath, f)
                        rel = os.path.relpath(full, root).replace("\\", "/")
                        entries[rel] = open(full, "rb").read()

            self._status(t["status_vpk"])
            vpk.build(entries, path)
            self._status(t["done"] % path, COL_VITAL)
        except Exception as e:
            traceback.print_exc()
            self._status("⚠ %s" % e, COL_CRIMSON)
        finally:
            self.building = False
            self.root.after(0, lambda: self.go.config(
                state="normal", text=I18N[self.lang]["build"]))


def main():
    if "--selftest" in sys.argv:
        import numpy as np
        import audio
        sr = audio.SR
        t = np.arange(sr * 80, dtype=np.float32) / sr
        x = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32).reshape(-1, 1)
        x = np.repeat(x, 2, axis=1)
        seg = audio.build_loop(x, 1.0, -10.0)
        import pyloudnorm as pyln
        meter = pyln.Meter(sr)
        print("SELFTEST loudness %.2f LUFS frames %d" %
              (meter.integrated_loudness(np.ascontiguousarray(seg.astype(np.float64))), len(seg)))
        return
    root = tk.Tk()
    try:
        root.iconbitmap(res_path("logo.ico"))
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
