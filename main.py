# Suppress rembg "No onnxruntime backend found" warning message on startup
import os
os.environ["REMBG_BACKEND"] = "onnxruntime"
import warnings
warnings.filterwarnings("ignore", message=".*onnxruntime.*")

# Enable DPI awareness on Windows to prevent scaling issues on high-resolution screens (necessary for accurate Snipping coordinate calculations)
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1) # PROCESS_SYSTEM_DPI_Aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import tkinter as tk
from tkinter import ttk, messagebox
from image_tab import ImageTab
from download_tab import DownloadTab
from tts_tab import TtsTab
from zip_tab import ZipTab
from ocr_tab import OcrTab
from share_tab import ShareTab
from convert_tab import ConvertTab
import os
import sys
import threading
from folder_watcher import watcher

class MultiToolApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("MT Tool")
        self.geometry("1150x720")
        self.minsize(900, 600)
        self.configure(bg="#1e1e1e") # Dark background for main window
        
        # Set Window Icon
        icon_path = 'app_icon.ico'
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, 'app_icon.ico')
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except:
                pass
        
        # Configure Styles
        self.setup_styles()
        
        # Top Bar (Settings & Update)
        self.create_top_bar()
        
        # Create Notebook (Tabs container)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # Add Tabs
        self.image_tab = ImageTab(self.notebook)
        self.download_tab = DownloadTab(self.notebook)
        self.tts_tab = TtsTab(self.notebook)
        self.zip_tab = ZipTab(self.notebook)
        self.ocr_tab = OcrTab(self.notebook)
        self.share_tab = ShareTab(self.notebook)
        self.convert_tab = ConvertTab(self.notebook)
        
        self.notebook.add(self.image_tab, text=" 🖼️ 이미지 처리 ")
        self.notebook.add(self.download_tab, text=" 📥 동영상 다운로더 ")
        self.notebook.add(self.tts_tab, text=" 🔊 로컬 TTS (말하기) ")
        self.notebook.add(self.zip_tab, text=" 📦 압축 관리 ")
        self.notebook.add(self.ocr_tab, text=" 🔍 텍스트 추출 (OCR) ")
        self.notebook.add(self.share_tab, text=" 📡 무선 파일 공유 ")
        self.notebook.add(self.convert_tab, text=" 🔄 포맷 변환 ")
        
        # Status Bar at bottom
        self.status_bar = ttk.Label(self, text="MT Tool v1.0 | 단축키 [Ctrl+Shift+D] 전역 텍스트 캡처 지원", relief="sunken", anchor="w", padding=(5, 2))
        self.status_bar.pack(fill="x", side="bottom")
        
        # Center Window
        self.center_window()

        # Register Windows Global Hotkey for screen OCR (Ctrl + Shift + D)
        self.register_global_hotkey()
        
        # Start background real-time folder watcher for VirusTotal
        watcher.start(self)

    def create_top_bar(self):
        # Create a top bar frame for settings
        top_bar = ttk.Frame(self)
        top_bar.pack(fill="x", side="top", padx=10, pady=(10, 0))
        
        # Add settings button
        settings_btn = ttk.Button(top_bar, text="⚙️ 설정", command=self.open_settings)
        settings_btn.pack(side="right")
        
    def open_settings(self):
        from config_manager import config
        from tkinter import filedialog
        
        set_win = tk.Toplevel(self)
        set_win.title("환경 설정")
        set_win.geometry("500x440")
        set_win.transient(self)
        set_win.grab_set()
        
        # UI Setup
        frame = ttk.Frame(set_win, padding=20)
        frame.pack(fill="both", expand=True)
        
        # --- VirusTotal Settings ---
        ttk.Label(frame, text="[보안 설정]", font=("맑은 고딕", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        vt_var = tk.BooleanVar(value=config.get('vt_enabled', False))
        ttk.Checkbutton(frame, text="다운로드 폴더 실시간 감시 및 VirusTotal 자동 검사 (.mtt 격리)", variable=vt_var).pack(anchor="w", pady=2)
        
        vt_frame = ttk.Frame(frame)
        vt_frame.pack(fill="x", pady=2)
        ttk.Label(vt_frame, text="VirusTotal API Key:", width=20).pack(side="left")
        api_var = tk.StringVar(value=config.get('vt_api_key', ''))
        ttk.Entry(vt_frame, textvariable=api_var, width=40).pack(side="left")
        
        # --- Google Cloud & Typecast TTS Settings ---
        gtts_frame = ttk.Frame(frame)
        gtts_frame.pack(fill="x", pady=5)
        ttk.Label(gtts_frame, text="Google TTS API Key:", width=20).pack(side="left")
        gtts_api_var = tk.StringVar(value=config.get('google_tts_api_key', ''))
        ttk.Entry(gtts_frame, textvariable=gtts_api_var, width=40).pack(side="left")
        
        typecast_frame1 = ttk.Frame(frame)
        typecast_frame1.pack(fill="x", pady=2)
        ttk.Label(typecast_frame1, text="Typecast API Key:", width=20).pack(side="left")
        typecast_api_var = tk.StringVar(value=config.get('typecast_api_key', ''))
        ttk.Entry(typecast_frame1, textvariable=typecast_api_var, width=40).pack(side="left")
        
        typecast_frame2 = ttk.Frame(frame)
        typecast_frame2.pack(fill="x", pady=2)
        ttk.Label(typecast_frame2, text="Typecast Voice ID:", width=20).pack(side="left")
        typecast_voice_var = tk.StringVar(value=config.get('typecast_voice_id', ''))
        ttk.Entry(typecast_frame2, textvariable=typecast_voice_var, width=40).pack(side="left")
        
        # --- Download Folder Settings ---
        ttk.Label(frame, text="[기본 다운로드 경로]", font=("맑은 고딕", 10, "bold")).pack(anchor="w", pady=(15, 5))
        folder_frame = ttk.Frame(frame)
        folder_frame.pack(fill="x")
        
        folder_var = tk.StringVar(value=config.get('download_folder', ''))
        ttk.Entry(folder_frame, textvariable=folder_var, state='readonly').pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        def browse_folder():
            folder = filedialog.askdirectory(initialdir=folder_var.get())
            if folder:
                folder_var.set(folder)
                
        ttk.Button(folder_frame, text="찾아보기", command=browse_folder).pack(side="right")
        
        def save():
            config.set('vt_enabled', vt_var.get())
            config.set('vt_api_key', api_var.get())
            config.set('google_tts_api_key', gtts_api_var.get())
            config.set('typecast_api_key', typecast_api_var.get())
            config.set('typecast_voice_id', typecast_voice_var.get())
            config.set('download_folder', folder_var.get())
            messagebox.showinfo("설정", "설정이 저장되었습니다.", parent=set_win)
            set_win.destroy()
            
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(side="bottom", fill="x", pady=(20, 0))
        ttk.Button(btn_frame, text="저장", command=save).pack(side="right")
        ttk.Button(btn_frame, text="취소", command=set_win.destroy).pack(side="right", padx=5)

    def setup_styles(self):
        self.style = ttk.Style(self)
        
        # We must use 'clam' theme because it is the most customizable cross-platform theme in Tkinter
        self.style.theme_use("clam")
        
        # Palette configuration (VS Code / Modern Dark UI)
        bg_main = "#1e1e1e"       # Background
        bg_card = "#252526"       # Panels / Cards
        bg_active = "#2d2d2d"     # Active tabs / Hover
        fg_text = "#d4d4d4"       # Normal text
        fg_bright = "#ffffff"     # White text
        accent = "#0e639c"        # Accent Blue
        accent_hover = "#1177bb"  # Accent Hover Blue
        border_color = "#3c3c3c"  # Borders
        
        # Configure global options
        self.option_add("*background", bg_main)
        self.option_add("*foreground", fg_text)
        
        self.option_add("*Text.background", bg_main)
        self.option_add("*Text.foreground", fg_bright)
        self.option_add("*Text.insertBackground", fg_bright)
        self.option_add("*Text.selectBackground", accent)
        self.option_add("*Text.selectForeground", fg_bright)
        self.option_add("*Text.font", ("Malgun Gothic", 10))
        
        self.option_add("*Listbox.background", bg_card)
        self.option_add("*Listbox.foreground", fg_text)
        self.option_add("*Listbox.selectBackground", accent)
        self.option_add("*Listbox.selectForeground", fg_bright)
        
        self.option_add("*Canvas.background", bg_active)
        self.option_add("*Canvas.highlightThickness", "0")
        
        # Configure ttk styles
        self.style.configure(".", background=bg_main, foreground=fg_text, font=("Segoe UI", 10))
        
        # Notebook (Tabs)
        self.style.configure("TNotebook", background=bg_card, borderwidth=0, tabmargins=[2, 4, 2, 0])
        self.style.configure("TNotebook.Tab", background=bg_card, foreground="#858585", borderwidth=1, bordercolor=border_color, padding=[16, 8], font=("Segoe UI", 10, "bold"))
        self.style.map("TNotebook.Tab",
                       background=[("selected", bg_main), ("active", bg_active)],
                       foreground=[("selected", fg_bright), ("active", fg_bright)],
                       bordercolor=[("selected", border_color)])
        
        # Frame
        self.style.configure("TFrame", background=bg_main)
        
        # LabelFrame
        self.style.configure("TLabelframe", background=bg_main, bordercolor=border_color, borderwidth=1)
        self.style.configure("TLabelframe.Label", background=bg_main, foreground=fg_bright, font=("Segoe UI", 10, "bold"))
        
        # Button
        self.style.configure("TButton", background=accent, foreground=fg_bright, borderwidth=0, padding=[12, 6], font=("Segoe UI", 10, "bold"))
        self.style.map("TButton",
                       background=[("active", accent_hover), ("disabled", "#3c3c3c")],
                       foreground=[("disabled", "#757575")])
        
        # Label
        self.style.configure("TLabel", background=bg_main, foreground=fg_text)
        
        # Checkbutton & Radiobutton
        self.style.configure("TCheckbutton", background=bg_main, foreground=fg_text)
        self.style.configure("TRadiobutton", background=bg_main, foreground=fg_text)
        self.style.map("TCheckbutton", background=[("active", bg_active)])
        self.style.map("TRadiobutton", background=[("active", bg_active)])
        
        # Entry
        self.style.configure("TEntry", fieldbackground="#2d2d2d", foreground=fg_bright, bordercolor=border_color, lightcolor=border_color, darkcolor=border_color)
        
        # Combobox
        self.style.configure("TCombobox", fieldbackground="#2d2d2d", background=bg_main, foreground=fg_bright, bordercolor=border_color, arrowcolor=fg_text)
        self.style.map("TCombobox", fieldbackground=[("readonly", "#2d2d2d")], foreground=[("readonly", fg_bright)])
        
        # Progressbar
        self.style.configure("Horizontal.TProgressbar", background=accent, troughcolor=bg_card, bordercolor=border_color)
        
        # Scale
        self.style.configure("Horizontal.TScale", background=bg_main, troughcolor=bg_card, bordercolor=border_color)

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    # --- Windows Global Hotkey Registration ---
    # --- Windows Global Hotkey Registration ---
    def register_global_hotkey(self):
        def hotkey_loop():
            user32 = ctypes.windll.user32
            from ctypes import wintypes
            
            # Candidates to try in order (ID, modifiers, vk, name)
            # Modifiers: Control (0x0002) + Shift (0x0004) = 6. Alt (0x0001) + Shift (0x0004) = 5.
            candidates = [
                (101, 6, 0x44, "Ctrl+Shift+D"),
                (102, 6, 0x4F, "Ctrl+Shift+O"),
                (103, 5, 0x44, "Alt+Shift+D"),
                (104, 6, 0x58, "Ctrl+Shift+X")
            ]
            
            registered_id = None
            registered_name = None
            
            for hid, mods, vk, name in candidates:
                if user32.RegisterHotKey(None, hid, mods, vk):
                    registered_id = hid
                    registered_name = name
                    break
                    
            if registered_name:
                status_text = f"Antigravity Multi-Tool App v1.3 | 단축키 [{registered_name}] 전역 텍스트 캡처 지원"
                if registered_name != "Ctrl+Shift+D":
                    status_text = f"Antigravity Multi-Tool App v1.3 | [Ctrl+Shift+D] 중복으로 인해 [{registered_name}]로 단축키 대체 등록됨"
                    
                self.after(0, lambda st=status_text, name=registered_name: self._on_hotkey_registered(st, name))
                
                try:
                    msg = wintypes.MSG()
                    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                        if msg.message == 0x0312: # WM_HOTKEY
                            if msg.wParam == registered_id:
                                # Trigger OCR capture function safely on main thread
                                self.after(0, self.trigger_global_ocr)
                        user32.TranslateMessage(ctypes.byref(msg))
                        user32.DispatchMessageW(ctypes.byref(msg))
                finally:
                    user32.UnregisterHotKey(None, registered_id)
            else:
                self.after(0, lambda: self.status_bar.config(text="Antigravity Multi-Tool App v1.3 | 전역 단축키 등록 실패", foreground="#f44747"))
                
        # Start daemon thread so it terminates when the application exits
        threading.Thread(target=hotkey_loop, daemon=True).start()

    def _on_hotkey_registered(self, status_text, hotkey_name):
        self.status_bar.config(text=status_text)
        try:
            self.ocr_tab.btn_capture.config(text=f"📸 화면 캡처 추출 ({hotkey_name})")
        except Exception as e:
            print("[Hotkey update UI error]", e)

    def trigger_global_ocr(self):
        # 1. Switch active tab to OCR Tab
        self.notebook.select(self.ocr_tab)
        # 2. Trigger screen capture
        self.ocr_tab.start_screen_capture()

if __name__ == "__main__":
    try:
        app = MultiToolApp()
        app.mainloop()
    except Exception as e:
        # Emergency error dialog if application crashes on boot
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Fatal Error", f"프로그램 실행 중 치명적인 오류가 발생했습니다:\n{e}")
