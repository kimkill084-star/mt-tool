import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageGrab, ImageEnhance
import winocr
import threading
import time
import os

class SnippingOverlay(tk.Toplevel):
    def __init__(self, screenshot, callback):
        super().__init__()
        self.screenshot = screenshot
        self.callback = callback
        
        # Borderless, fullscreen, topmost
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.state('zoomed')
        self.config(cursor="cross")
        
        # Get dimensions
        self.update_idletasks()
        self.width = self.winfo_screenwidth()
        self.height = self.winfo_screenheight()
        self.geometry(f"{self.width}x{self.height}+0+0")
        
        # Resize to match logical screen dimensions for DPI scaling compatibility
        self.display_img = screenshot.resize((self.width, self.height), Image.Resampling.NEAREST)
        
        # Dim the screenshot for a professional overlay look
        self.dimmed = ImageEnhance.Brightness(self.display_img).enhance(0.5)
        self.photo = ImageTk.PhotoImage(self.dimmed)
        
        self.canvas = tk.Canvas(self, cursor="cross", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        
        self.rect_id = None
        self.start_x = None
        self.start_y = None
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", lambda e: self.cancel())
        
    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=2)
        
    def on_drag(self, event):
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)
        
    def on_release(self, event):
        end_x = event.x
        end_y = event.y
        self.destroy()
        
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        
        if x2 - x1 > 5 and y2 - y1 > 5:
            # Calculate scale ratios between physical screenshot and logical screen size
            scale_x = self.screenshot.width / self.width
            scale_y = self.screenshot.height / self.height
            
            real_x1 = int(x1 * scale_x)
            real_y1 = int(y1 * scale_y)
            real_x2 = int(x2 * scale_x)
            real_y2 = int(y2 * scale_y)
            
            # Crop the original physical screenshot
            cropped = self.screenshot.crop((real_x1, real_y1, real_x2, real_y2))
            self.callback(cropped)
        else:
            self.callback(None)
            
    def cancel(self):
        self.destroy()
        self.callback(None)


class OcrTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.create_widgets()

    def create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1) # Text area takes main space
        
        # --- Top Options Bar ---
        top_frame = ttk.Frame(self, padding=5)
        top_frame.grid(row=0, column=0, sticky="we", padx=5, pady=5)
        
        self.btn_capture = ttk.Button(top_frame, text="📸 화면 캡처 추출 (Ctrl+Shift+D)", command=self.start_screen_capture)
        self.btn_capture.pack(side="left", padx=5)
        ttk.Button(top_frame, text="📁 이미지 파일 선택", command=self.load_image_file).pack(side="left", padx=5)
        ttk.Button(top_frame, text="📋 클립보드 복사", command=self.copy_to_clipboard).pack(side="right", padx=5)
        ttk.Button(top_frame, text="🧹 비우기", command=self.clear_text).pack(side="right", padx=5)
        
        # --- Middle Text Area ---
        text_frame = ttk.LabelFrame(self, text="추출된 텍스트", padding=10)
        text_frame.grid(row=1, column=0, sticky="nswe", padx=5, pady=5)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        self.text_out = tk.Text(text_frame, wrap="word", font=("Malgun Gothic", 10))
        self.text_out.grid(row=0, column=0, sticky="nswe")
        
        scroll = ttk.Scrollbar(text_frame, command=self.text_out.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.text_out.config(yscrollcommand=scroll.set)
        
        # Default placeholder instruction
        self.text_out.insert("1.0", "단축키 [Ctrl + Shift + D]를 누르면 언제 어디서나 화면을 드래그하여 글자를 추출할 수 있습니다.\n\n또는 상단의 [화면 캡처 추출] 버튼이나 [이미지 파일 선택] 버튼을 이용하여 이미지를 로드해주세요.")
        
        # --- Bottom Status ---
        self.status_lbl = ttk.Label(self, text="준비됨. (단축키 활성화됨)", foreground="gray")
        self.status_lbl.grid(row=2, column=0, sticky="w", padx=10, pady=5)

    def set_status(self, text, color="gray"):
        color_map = {
            "black": "#d4d4d4",
            "gray": "#888888",
            "blue": "#3794ff",
            "green": "#4ec9b0",
            "red": "#f44747",
            "orange": "#ce9178"
        }
        mapped_color = color_map.get(color, color)
        self.status_lbl.config(text=text, foreground=mapped_color)

    def clear_text(self):
        self.text_out.delete("1.0", "end")

    def copy_to_clipboard(self):
        text = self.text_out.get("1.0", "end-1c").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
            self.set_status("텍스트가 클립보드에 복사되었습니다.", "green")
        else:
            messagebox.showwarning("경고", "복사할 텍스트가 없습니다.")

    # --- File OCR ---
    def load_image_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.webp")]
        )
        if not file_path:
            return
            
        try:
            img = Image.open(file_path)
            self.set_status("텍스트 인식 진행 중...", "blue")
            self.run_ocr(img)
        except Exception as e:
            messagebox.showerror("오류", f"이미지 파일을 처리하는 데 실패했습니다:\n{e}")

    # --- Screen Capture OCR ---
    def start_screen_capture(self):
        # 1. Get the app's root window (MultiToolApp) and withdraw it
        root_win = self.winfo_toplevel()
        root_win.withdraw()
        
        # Wait for window to vanish completely
        self.parent.after(250, lambda: self.capture_fullscreen(root_win))

    def capture_fullscreen(self, root_win):
        try:
            # Grab primary screen screenshot to match fullscreen window 1:1
            screenshot = ImageGrab.grab()
            
            # Show snipping overlay
            def on_snipped(cropped_img):
                # Restore main window
                root_win.deiconify()
                root_win.focus_force()
                
                if cropped_img:
                    self.set_status("텍스트 추출 분석 중...", "blue")
                    self.run_ocr(cropped_img)
                else:
                    self.set_status("캡처 취소됨.", "orange")
            
            SnippingOverlay(screenshot, on_snipped)
        except Exception as e:
            root_win.deiconify()
            messagebox.showerror("오류", f"화면 캡처 중 오류가 발생했습니다: {e}")

    # --- Run OCR engine ---
    def run_ocr(self, img):
        # Run in thread to avoid UI lag
        threading.Thread(target=self._ocr_thread, args=(img,), daemon=True).start()

    def _ocr_thread(self, img):
        text = ""
        ko_error = None
        en_error = None
        
        # 1. Try Korean OCR
        try:
            op = winocr.recognize_pil(img, lang="ko")
            result = op.get() if hasattr(op, "get") else op
            text = result.text.strip()
        except Exception as e:
            ko_error = e
            
        # 2. Try English OCR if no text was found
        if not text:
            try:
                op = winocr.recognize_pil(img, lang="en")
                result = op.get() if hasattr(op, "get") else op
                text = result.text.strip()
            except Exception as e:
                en_error = e
                
        # 3. Handle results
        if ko_error and en_error:
            # Both failed (typically means no OCR pack is installed at all)
            err_msg = (
                f"Windows OCR 기능 실행 실패.\n\n"
                f"[한국어 에러]: {ko_error}\n"
                f"[영어 에러]: {en_error}\n\n"
                f"💡 해결방법: PowerShell을 [관리자 권한]으로 실행하고 다음 명령어를 입력하여 OCR 언어 팩을 설치해 주세요:\n"
                f"Add-WindowsCapability -Online -Name \"Language.OCR~~~ko-KR~0.0.1.0\""
            )
            self.parent.after(0, lambda: self.ocr_finished(False, err_msg))
        else:
            # At least one succeeded (even if it found no text)
            self.parent.after(0, lambda: self.ocr_finished(True, text))

    def ocr_finished(self, success, text):
        if success:
            if text:
                self.text_out.delete("1.0", "end")
                self.text_out.insert("1.0", text)
                
                # Auto copy to clipboard
                self.clipboard_clear()
                self.clipboard_append(text)
                self.update()
                
                self.set_status("글자 인식 성공 및 클립보드 자동 복사 완료!", "green")
            else:
                self.set_status("인식된 텍스트가 없습니다.", "orange")
                messagebox.showinfo("결과", "이미지에서 글자를 발견하지 못했습니다.")
        else:
            self.set_status(f"인식 실패: {text}", "red")
            messagebox.showerror("OCR 분석 오류", f"글자 인식 중 오류가 발생했습니다:\n{text}")
