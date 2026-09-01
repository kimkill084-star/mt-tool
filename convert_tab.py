import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image
import threading
import os
import subprocess

class ConvertTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        # State variables
        self.selected_images = []  # List of selected image paths
        self.selected_media = None # Selected video/audio path
        
        # Create nested notebook
        self.nested_notebook = ttk.Notebook(self)
        self.nested_notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        self.create_image_tab()
        self.create_media_tab()

    # --- Tab 1: Image Converter ---
    def create_image_tab(self):
        tab = ttk.Frame(self.nested_notebook)
        self.nested_notebook.add(tab, text=" 🖼️ 이미지 포맷 변환 ")
        
        # File Selection Frame
        frame_files = ttk.LabelFrame(tab, text="변환할 이미지 선택 (다중 선택 가능)", padding=10)
        frame_files.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.list_images = tk.Listbox(frame_files, height=6, font=("Segoe UI", 9))
        self.list_images.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        scroll = ttk.Scrollbar(frame_files, command=self.list_images.yview)
        scroll.pack(side="left", fill="y")
        self.list_images.config(yscrollcommand=scroll.set)
        
        btn_frame = ttk.Frame(frame_files)
        btn_frame.pack(side="right", fill="y", padx=5)
        
        ttk.Button(btn_frame, text="파일 추가", command=self.select_images).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="목록 비우기", command=self.clear_image_list).pack(fill="x", pady=2)
        
        # Options Frame
        frame_opts = ttk.LabelFrame(tab, text="변환 옵션", padding=10)
        frame_opts.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(frame_opts, text="출력 포맷 선택:").grid(row=0, column=0, sticky='w', pady=5)
        self.img_format_var = tk.StringVar(value="PNG")
        self.img_format_combo = ttk.Combobox(frame_opts, textvariable=self.img_format_var, state="readonly", width=12)
        self.img_format_combo["values"] = ("PNG", "JPEG", "WEBP", "BMP", "ICO")
        self.img_format_combo.grid(row=0, column=1, sticky='w', padx=10, pady=5)
        
        # Status
        self.lbl_img_status = ttk.Label(tab, text="대기 중...", font=("Segoe UI", 9, "bold"), foreground="gray")
        self.lbl_img_status.pack(pady=5)
        
        # Start Button
        self.btn_convert_img = ttk.Button(tab, text="이미지 변환 시작", command=self.start_image_conversion)
        self.btn_convert_img.pack(pady=10)

    def select_images(self):
        files = filedialog.askopenfilenames(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.webp *.tiff")]
        )
        if files:
            for file in files:
                if file not in self.selected_images:
                    self.selected_images.append(file)
                    self.list_images.insert("end", os.path.basename(file))
            self.lbl_img_status.config(text=f"{len(self.selected_images)}개 이미지 선택됨.", foreground="black")

    def clear_image_list(self):
        self.selected_images.clear()
        self.list_images.delete(0, "end")
        self.lbl_img_status.config(text="대기 중...", foreground="gray")

    def start_image_conversion(self):
        if not self.selected_images:
            messagebox.showwarning("경고", "변환할 이미지 파일을 추가해 주세요.")
            return
            
        output_dir = filedialog.askdirectory(title="변환된 파일을 저장할 폴더 선택")
        if not output_dir:
            return
            
        target_format = self.img_format_var.get()
        
        self.btn_convert_img.config(state="disabled")
        self.lbl_img_status.config(text="이미지 변환 중...", foreground="blue")
        
        # Run conversion in background thread
        threading.Thread(target=self.run_image_conversion, args=(output_dir, target_format), daemon=True).start()

    def run_image_conversion(self, output_dir, target_format):
        success_count = 0
        ext_map = {
            "PNG": ".png",
            "JPEG": ".jpg",
            "WEBP": ".webp",
            "BMP": ".bmp",
            "ICO": ".ico"
        }
        
        ext = ext_map.get(target_format, ".png")
        
        for file in self.selected_images:
            try:
                img = Image.open(file)
                base_name = os.path.splitext(os.path.basename(file))[0]
                out_path = os.path.join(output_dir, base_name + ext)
                
                # ICO conversion details
                if target_format == "ICO":
                    # ICO requires specific square sizes or resizing
                    img = img.resize((256, 256), Image.Resampling.LANCZOS)
                
                # JPEG requires RGB mode (cannot save RGBA alpha channel directly as JPEG)
                if target_format == "JPEG" and img.mode in ("RGBA", "LA"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3] if img.mode == "RGBA" else img.split()[1])
                    img = background
                    
                img.save(out_path)
                success_count += 1
            except Exception as e:
                print(f"[Image Convert Error] Failed {file}: {e}")
                
        self.parent.after(0, lambda: self.image_conversion_finished(success_count, len(self.selected_images)))

    def image_conversion_finished(self, success_count, total_count):
        self.btn_convert_img.config(state="normal")
        self.lbl_img_status.config(text=f"작업 완료: {success_count}/{total_count} 이미지 성공.", foreground="green")
        messagebox.showinfo("성공", f"이미지 변환이 완료되었습니다!\n\n성공: {success_count} / {total_count}")
        self.clear_image_list()

    # --- Tab 2: Media Converter (FFmpeg) ---
    def create_media_tab(self):
        tab = ttk.Frame(self.nested_notebook)
        self.nested_notebook.add(tab, text=" 🎬 미디어 포맷 변환 (FFmpeg) ")
        
        # File Selection Frame
        frame_file = ttk.LabelFrame(tab, text="변환할 미디어 파일 선택 (동영상 / 오디오)", padding=10)
        frame_file.pack(fill='x', padx=10, pady=10)
        
        self.lbl_media_file = ttk.Label(frame_file, text="선택된 파일: 없음", font=("Segoe UI", 9, "italic"))
        self.lbl_media_file.pack(side='left', expand=True, fill='x')
        
        btn_select = ttk.Button(frame_file, text="파일 선택", command=self.select_media_file)
        btn_select.pack(side='right')
        
        # Options Frame
        frame_opts = ttk.LabelFrame(tab, text="변환 옵션", padding=10)
        frame_opts.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(frame_opts, text="출력 포맷 선택:").grid(row=0, column=0, sticky='w', pady=5)
        self.media_format_var = tk.StringVar(value="MP4 (동영상)")
        self.media_format_combo = ttk.Combobox(frame_opts, textvariable=self.media_format_var, state="readonly", width=16)
        self.media_format_combo["values"] = ("MP4 (동영상)", "MP3 (오디오)", "WAV (오디오)", "MKV (동영상)", "AVI (동영상)")
        self.media_format_combo.grid(row=0, column=1, sticky='w', padx=10, pady=5)
        
        # Status Label
        self.lbl_media_status = ttk.Label(tab, text="대기 중...", font=("Segoe UI", 9, "bold"), foreground="gray")
        self.lbl_media_status.pack(pady=10)
        
        # Action Button
        self.btn_convert_media = ttk.Button(tab, text="미디어 변환 시작", command=self.start_media_conversion)
        self.btn_convert_media.pack(pady=10)

    def select_media_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Media files", "*.mp4 *.avi *.mkv *.mov *.flv *.mp3 *.wav *.m4a *.wma *.ogg")]
        )
        if file_path:
            self.selected_media = file_path
            self.lbl_media_file.config(text=f"선택된 파일: {os.path.basename(file_path)}")
            self.lbl_media_status.config(text="변환할 준비가 되었습니다.", foreground="black")

    def start_media_conversion(self):
        if not self.selected_media:
            messagebox.showwarning("경고", "변환할 미디어 파일을 선택해 주세요.")
            return
            
        selected_fmt = self.media_format_var.get()
        ext_map = {
            "MP4 (동영상)": ".mp4",
            "MP3 (오디오)": ".mp3",
            "WAV (오디오)": ".wav",
            "MKV (동영상)": ".mkv",
            "AVI (동영상)": ".avi"
        }
        ext = ext_map.get(selected_fmt, ".mp4")
        
        save_path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(f"{selected_fmt} files", f"*{ext}"), ("All files", "*.*")],
            initialfile=os.path.splitext(os.path.basename(self.selected_media))[0] + ext
        )
        if not save_path:
            return
            
        self.btn_convert_media.config(state="disabled")
        self.lbl_media_status.config(text="미디어 변환 진행 중 (FFmpeg)...", foreground="blue")
        
        # Run FFmpeg conversion in background thread
        threading.Thread(target=self.run_media_conversion, args=(self.selected_media, save_path, selected_fmt), daemon=True).start()

    def run_media_conversion(self, in_file, out_file, fmt_type):
        try:
            # Build FFmpeg command based on format
            if fmt_type == "MP3 (오디오)":
                # Convert video/audio to high-quality MP3
                cmd = ["ffmpeg", "-y", "-i", in_file, "-vn", "-acodec", "libmp3lame", "-ab", "192k", out_file]
            elif fmt_type == "WAV (오디오)":
                # Extract WAV audio
                cmd = ["ffmpeg", "-y", "-i", in_file, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", out_file]
            else:
                # Video format transcode (e.g. mp4, mkv, avi)
                # We let FFmpeg automatically choose safe output codecs for container compatibility
                cmd = ["ffmpeg", "-y", "-i", in_file, out_file]
                
            # Execute FFmpeg subprocess silently (hide window on Windows)
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            result = subprocess.run(cmd, startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                self.parent.after(0, lambda: self.media_conversion_finished(True, "변환 성공"))
            else:
                # Capture stderr log
                self.parent.after(0, lambda: self.media_conversion_finished(False, result.stderr))
                
        except Exception as e:
            err_msg = str(e)
            self.parent.after(0, lambda: self.media_conversion_finished(False, err_msg))

    def media_conversion_finished(self, success, msg):
        self.btn_convert_media.config(state="normal")
        if success:
            self.lbl_media_status.config(text="미디어 변환 완료!", foreground="green")
            messagebox.showinfo("성공", "미디어 변환이 완료되었습니다.")
            self.selected_media = None
            self.lbl_media_file.config(text="선택된 파일: 없음")
        else:
            self.lbl_media_status.config(text="미디어 변환 실패.", foreground="red")
            messagebox.showerror("오류", f"미디어 변환 중 오류가 발생했습니다:\n{msg}")
