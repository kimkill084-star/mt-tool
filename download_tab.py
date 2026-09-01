import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yt_dlp
import threading
import os
import re

class DownloadTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        # Settings
        from config_manager import config
        self.download_folder = config.get('download_folder', os.path.join(os.path.expanduser('~'), 'Downloads'))
        
        self.is_downloading = False
        self.download_thread = None
        
        self.create_widgets()

    def create_widgets(self):
        self.columnconfigure(0, weight=1)
        
        # --- Top Options Panel ---
        options_frame = ttk.LabelFrame(self, text="다운로드 설정", padding=10)
        options_frame.grid(row=0, column=0, sticky="nwe", padx=5, pady=5)
        options_frame.columnconfigure(1, weight=1)
        
        # URL Input
        ttk.Label(options_frame, text="동영상 URL:").grid(row=0, column=0, sticky="w", pady=5)
        self.url_entry = ttk.Entry(options_frame)
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky="we", pady=5, padx=5)
        self.url_entry.insert(0, "") # Placeholder
        
        # Output Folder selection
        ttk.Label(options_frame, text="저장 폴더:").grid(row=1, column=0, sticky="w", pady=5)
        self.folder_lbl = ttk.Label(options_frame, text=self.download_folder, font=("Segoe UI", 9, "italic"), width=50, anchor="w")
        self.folder_lbl.grid(row=1, column=1, sticky="we", pady=5, padx=5)
        ttk.Button(options_frame, text="폴더 선택", command=self.choose_folder).grid(row=1, column=2, sticky="e", pady=5, padx=5)
        
        # Format Selection (Video/Audio)
        ttk.Label(options_frame, text="다운로드 형식:").grid(row=2, column=0, sticky="w", pady=5)
        self.format_var = tk.StringVar(value="video")
        video_radio = ttk.Radiobutton(options_frame, text="동영상 (최고 화질 MP4)", variable=self.format_var, value="video")
        video_radio.grid(row=2, column=1, sticky="w", pady=5)
        audio_radio = ttk.Radiobutton(options_frame, text="오디오 전용 (MP3 변환)", variable=self.format_var, value="audio")
        audio_radio.grid(row=2, column=2, sticky="w", pady=5)
        
        # --- Middle Progress Panel ---
        progress_frame = ttk.Frame(self, padding=5)
        progress_frame.grid(row=1, column=0, sticky="we", padx=5, pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        self.progress_bar.grid(row=0, column=0, sticky="we", pady=5)
        
        status_subframe = ttk.Frame(progress_frame)
        status_subframe.grid(row=1, column=0, sticky="we")
        
        self.percent_lbl = ttk.Label(status_subframe, text="0.0%", font=("Segoe UI", 10, "bold"))
        self.percent_lbl.pack(side="left")
        
        self.speed_lbl = ttk.Label(status_subframe, text="대기 중...", foreground="gray")
        self.speed_lbl.pack(side="right")
        
        # --- Bottom Action Button ---
        action_frame = ttk.Frame(self, padding=5)
        action_frame.grid(row=2, column=0, sticky="we", padx=5)
        
        self.download_btn = ttk.Button(action_frame, text="다운로드 시작", command=self.start_download)
        self.download_btn.pack(fill="x", pady=5)
        


    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_folder)
        if folder:
            self.download_folder = folder
            self.folder_lbl.config(text=self.download_folder)
            
            from config_manager import config
            config.set('download_folder', folder)

    def write_log(self, msg):
        print(f"[Downloader Log] {msg}")

    def update_progress_ui(self, percent, speed_str, eta_str):
        self.progress_bar["value"] = percent
        self.percent_lbl.config(text=f"{percent:.1f}%")
        self.speed_lbl.config(text=f"속도: {speed_str} | 남은 시간: {eta_str}")

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            # Calculate percentage
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded_bytes = d.get('downloaded_bytes', 0)
            
            percent = 0.0
            if total_bytes > 0:
                percent = (downloaded_bytes / total_bytes) * 100
                
            speed = d.get('speed')
            if speed:
                # Format speed
                if speed > 1024 * 1024:
                    speed_str = f"{speed / (1024*1024):.2f} MB/s"
                else:
                    speed_str = f"{speed / 1024:.2f} KB/s"
            else:
                speed_str = "--"
                
            eta = d.get('eta')
            if eta is not None:
                mins, secs = divmod(eta, 60)
                eta_str = f"{mins}분 {secs}초" if mins > 0 else f"{secs}초"
            else:
                eta_str = "--"
                
            # Safely schedule UI updates on main thread
            self.parent.after(0, lambda: self.update_progress_ui(percent, speed_str, eta_str))
            
        elif d['status'] == 'finished':
            self.parent.after(0, lambda: self.update_progress_ui(100.0, "완료", "0초"))

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("경고", "다운로드할 동영상 URL을 입력해주세요.")
            return
            
        if self.is_downloading:
            messagebox.showwarning("경고", "이미 다운로드가 진행 중입니다.")
            return
            
        self.is_downloading = True
        self.download_btn.config(state="disabled", text="다운로드 중...")
        self.progress_bar["value"] = 0
        self.percent_lbl.config(text="0.0%")
        self.speed_lbl.config(text="연결 중...", foreground="blue")
        
        # Print start log
        print(f"[Downloader] 다운로드 시작 URL: {url}")
        
        # Run in thread
        self.download_thread = threading.Thread(target=self.run_download, args=(url,), daemon=True)
        self.download_thread.start()

    def run_download(self, url):
        class YtdlLogger:
            def __init__(self, tab):
                self.tab = tab
            def debug(self, msg):
                # Only write useful information, filter out noise
                if "[download]" in msg or "[info]" in msg or "[merger]" in msg or "[Extract]" in msg:
                    # Ignore repetitive progress percentage lines in console log to keep it clean
                    if "%" in msg and ("ETA" in msg or "at" in msg):
                        return
                    self.tab.parent.after(0, lambda: self.tab.write_log(msg))
            def warning(self, msg):
                self.tab.parent.after(0, lambda: self.tab.write_log(f"[경고] {msg}"))
            def error(self, msg):
                self.tab.parent.after(0, lambda: self.tab.write_log(f"[오류] {msg}"))

        download_format = self.format_var.get()
        
        # Get latest download folder from config
        from config_manager import config
        current_folder = config.get('download_folder', os.path.join(os.path.expanduser('~'), 'Downloads'))
        
        # Setup yt-dlp options
        ydl_opts = {
            'outtmpl': os.path.join(current_folder, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'logger': YtdlLogger(self),
            'noprogress': True, # We handle progress reporting ourselves via hooks
        }
        
        # Add postprocessor hook for format conversion (like mp3)
        def post_hook(d):
            if d['status'] == 'finished':
                self.final_filename = d.get('info_dict', {}).get('filepath')
        ydl_opts['postprocessor_hooks'] = [post_hook]
        
        self.final_filename = None
        
        if download_format == 'audio':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            # Best video and best audio merged, but prefer mp4 container
            ydl_opts.update({
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            })
            
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info and download
                info = ydl.extract_info(url, download=True)
                
                if not self.final_filename:
                    self.final_filename = ydl.prepare_filename(info)
                
            self.parent.after(0, lambda: self.handle_post_download(self.final_filename))
        except Exception as e:
            err_msg = str(e)
            self.parent.after(0, lambda: self.download_finished(False, err_msg))

    def handle_post_download(self, final_filename):
        from config_manager import config
        import vt_scanner
        import shutil
        
        if not final_filename or not os.path.exists(final_filename):
            # Fallback if extension changed but hook didn't catch it
            base, ext = os.path.splitext(final_filename) if final_filename else ("unknown", "")
            if os.path.exists(base + ".mkv"): final_filename = base + ".mkv"
            elif os.path.exists(base + ".mp4"): final_filename = base + ".mp4"
            elif os.path.exists(base + ".webm"): final_filename = base + ".webm"
            elif os.path.exists(base + ".mp3"): final_filename = base + ".mp3"
            
            if not final_filename or not os.path.exists(final_filename):
                self.download_finished(False, f"파일을 찾을 수 없습니다: {final_filename}")
                return
            
        vt_enabled = config.get('vt_enabled', False)
        api_key = config.get('vt_api_key', '')
        
        if vt_enabled and api_key:
            # Rename to .mtt
            mtt_filename = final_filename + '.mtt'
            try:
                os.rename(final_filename, mtt_filename)
                self.write_log(f"파일을 임시 확장자(.mtt)로 변경했습니다.")
            except Exception as e:
                self.download_finished(False, f"확장자 변경 실패: {e}")
                return
                
            def scan_thread():
                def progress_cb(msg):
                    self.parent.after(0, lambda: self.write_log(f"[VT] {msg}"))
                    
                is_safe, msg = vt_scanner.check_file(mtt_filename, api_key, progress_cb)
                
                if is_safe:
                    try:
                        from folder_watcher import watcher
                        watcher.add_known(final_filename)
                        if os.path.exists(final_filename):
                            os.remove(final_filename) # Just in case
                        os.rename(mtt_filename, final_filename)
                        self.parent.after(0, lambda: self.write_log(f"검사 통과! 원본 확장자로 복원되었습니다."))
                        self.parent.after(0, lambda: self.download_finished(True, f"다운로드 완료 및 검사 통과:\n{msg}"))
                    except Exception as e:
                        self.parent.after(0, lambda: self.download_finished(False, f"확장자 복원 실패: {e}"))
                else:
                    self.parent.after(0, lambda: self.write_log(f"[경고] 악성코드 의심: {msg} (.mtt 확장자 유지)"))
                    self.parent.after(0, lambda: messagebox.showwarning("보안 경고", f"악성코드가 의심되어 임시 확장자(.mtt) 상태를 유지합니다.\n\n이유: {msg}"))
                    self.parent.after(0, lambda: self.download_finished(False, "다운로드는 완료되었으나 악성코드가 의심됩니다."))
                    
            threading.Thread(target=scan_thread, daemon=True).start()
        else:
            from folder_watcher import watcher
            watcher.add_known(final_filename)
            self.download_finished(True, "다운로드 완료! (보안 검사 비활성화)")

    def download_finished(self, success, message):
        self.is_downloading = False
        self.download_btn.config(state="normal", text="다운로드 시작")
        
        if success:
            self.speed_lbl.config(text="작업 완료", foreground="green")
            self.write_log("=== 작업 완료 ===")
            messagebox.showinfo("완료", message)
        else:
            self.speed_lbl.config(text="오류 발생", foreground="red")
            self.write_log(f"작업 실패: {message}")
            messagebox.showerror("오류", message)
