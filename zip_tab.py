import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import string
from core.zip_manager import compress_folder_or_file, decompress_zip
from core.password_cracker import crack_zip_password

class ZipTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        self.cancel_flag = False
        
        # Create nested notebook for the three zip features
        self.nested_notebook = ttk.Notebook(self)
        self.nested_notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        self.create_tab_crack()
        self.create_tab_compress()
        self.create_tab_decompress()

    # --- Tab 1: Password Cracker ---
    def create_tab_crack(self):
        tab = ttk.Frame(self.nested_notebook)
        self.nested_notebook.add(tab, text=" 🔑 비밀번호 찾기 (Cracker) ")
        
        # File Selection
        frame_file = ttk.LabelFrame(tab, text="압축 파일 선택", padding=10)
        frame_file.pack(fill='x', padx=10, pady=10)
        
        self.lbl_crack_file = ttk.Label(frame_file, text="선택된 파일: 없음", font=("Segoe UI", 9, "italic"))
        self.lbl_crack_file.pack(side='left', expand=True, fill='x')
        self.crack_file_path = None
        
        btn_select = ttk.Button(frame_file, text="파일 선택", command=self.select_crack_file)
        btn_select.pack(side='right')
        
        # Options
        frame_opts = ttk.LabelFrame(tab, text="무차별 대입 설정", padding=10)
        frame_opts.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(frame_opts, text="최대 비밀번호 길이:").grid(row=0, column=0, sticky='w', pady=5)
        self.entry_crack_len = ttk.Entry(frame_opts, width=8)
        self.entry_crack_len.insert(0, "4")
        self.entry_crack_len.grid(row=0, column=1, sticky='w', padx=10, pady=5)
        
        ttk.Label(frame_opts, text="대입 문자 그룹:").grid(row=1, column=0, sticky='w', pady=5)
        self.var_charset = tk.StringVar(value="num")
        
        charset_subframe = ttk.Frame(frame_opts)
        charset_subframe.grid(row=1, column=1, columnspan=3, sticky='w', padx=5, pady=5)
        
        ttk.Radiobutton(charset_subframe, text="숫자만 (0-9)", variable=self.var_charset, value="num").pack(side="left", padx=5)
        ttk.Radiobutton(charset_subframe, text="소문자 + 숫자", variable=self.var_charset, value="lowernum").pack(side="left", padx=5)
        ttk.Radiobutton(charset_subframe, text="전체 문자 (영대소문자/특수/숫자)", variable=self.var_charset, value="all").pack(side="left", padx=5)
        
        # Status Label
        status_frame = ttk.Frame(tab, padding=5)
        status_frame.pack(fill='x', padx=10, pady=10)
        self.lbl_crack_status = ttk.Label(status_frame, text="대기 중...", font=("Segoe UI", 10, "bold"), foreground="gray")
        self.lbl_crack_status.pack(anchor="center")
        
        # Action Buttons
        frame_action = ttk.Frame(tab)
        frame_action.pack(pady=10)
        
        self.btn_crack_start = ttk.Button(frame_action, text="찾기 시작", command=self.start_crack)
        self.btn_crack_start.pack(side='left', padx=10)
        
        self.btn_crack_stop = ttk.Button(frame_action, text="작업 중지", command=self.stop_crack, state='disabled')
        self.btn_crack_stop.pack(side='left', padx=10)
        
    def select_crack_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Zip files", "*.zip")])
        if file_path:
            self.crack_file_path = file_path
            self.lbl_crack_file.config(text=f"선택된 파일: {os.path.basename(file_path)}")
            self.lbl_crack_status.config(text="시작할 준비가 되었습니다.", foreground="black")
            
    def start_crack(self):
        if not self.crack_file_path:
            messagebox.showwarning("경고", "대입을 실행할 압축 파일을 선택해주세요.")
            return
            
        try:
            max_len = int(self.entry_crack_len.get())
            if max_len <= 0 or max_len > 12:
                raise ValueError("길이는 1에서 12 사이여야 합니다.")
        except ValueError as e:
            messagebox.showwarning("경고", f"올바른 비밀번호 길이를 입력해 주세요 (1-12).\n{e}")
            return
            
        charset_type = self.var_charset.get()
        if charset_type == "num":
            charset = string.digits
        elif charset_type == "lowernum":
            charset = string.ascii_lowercase + string.digits
        else:
            charset = string.ascii_letters + string.digits + string.punctuation
            
        self.cancel_flag = False
        self.btn_crack_start.config(state='disabled')
        self.btn_crack_stop.config(state='normal')
        self.lbl_crack_status.config(text="무차별 대입 분석 시작...", foreground="blue")
        
        thread = threading.Thread(target=self._crack_thread, args=(self.crack_file_path, charset, max_len), daemon=True)
        thread.start()
        
    def _crack_thread(self, zip_path, charset, max_len):
        def progress(pw):
            self.parent.after(0, lambda: self.lbl_crack_status.config(text=f"현재 대입 시도 중: {pw}"))
            
        def check_cancel():
            return self.cancel_flag
            
        success, result = crack_zip_password(zip_path, charset, max_len, progress, check_cancel)
        self.parent.after(0, lambda: self._crack_finished(success, result))
        
    def _crack_finished(self, success, result):
        self.btn_crack_start.config(state='normal')
        self.btn_crack_stop.config(state='disabled')
        if success:
            self.lbl_crack_status.config(text=f"비밀번호 탐색 성공! 비밀번호: {result}", foreground="green")
            messagebox.showinfo("성공", f"비밀번호를 찾았습니다!\n\n비밀번호: {result}")
        else:
            self.lbl_crack_status.config(text=f"작업 완료: {result}", foreground="red")
            messagebox.showinfo("결과", result)
            
    def stop_crack(self):
        self.cancel_flag = True
        self.lbl_crack_status.config(text="중지 요청 중...", foreground="orange")

    # --- Tab 2: Compress ---
    def create_tab_compress(self):
        tab = ttk.Frame(self.nested_notebook)
        self.nested_notebook.add(tab, text=" 📦 압축하기 (Compress) ")
        
        # Source Selection
        frame_src = ttk.LabelFrame(tab, text="압축할 대상 선택", padding=10)
        frame_src.pack(fill='x', padx=10, pady=10)
        
        self.lbl_comp_src = ttk.Label(frame_src, text="선택된 대상: 없음", font=("Segoe UI", 9, "italic"))
        self.lbl_comp_src.pack(side='left', expand=True, fill='x')
        self.comp_src_path = None
        
        btn_sel_file = ttk.Button(frame_src, text="파일 선택", command=lambda: self.select_comp_src(is_file=True))
        btn_sel_file.pack(side='right', padx=3)
        btn_sel_dir = ttk.Button(frame_src, text="폴더 선택", command=lambda: self.select_comp_src(is_file=False))
        btn_sel_dir.pack(side='right', padx=3)
        
        # Options
        frame_opts = ttk.LabelFrame(tab, text="암호화 설정", padding=10)
        frame_opts.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(frame_opts, text="비밀번호 설정 (선택):").grid(row=0, column=0, sticky='w', pady=5)
        self.entry_comp_pw = ttk.Entry(frame_opts, show="*", width=20)
        self.entry_comp_pw.grid(row=0, column=1, sticky='w', padx=10, pady=5)
        
        ttk.Label(frame_opts, text="* 비밀번호 입력 시 강력한 AES-256 방식으로 압축됩니다.", font=("Segoe UI", 8), foreground="gray").grid(row=1, column=0, columnspan=2, sticky='w', pady=2)
        
        # Status Label
        status_frame = ttk.Frame(tab, padding=5)
        status_frame.pack(fill='x', padx=10, pady=10)
        self.lbl_comp_status = ttk.Label(status_frame, text="대기 중...", font=("Segoe UI", 10, "bold"), foreground="gray")
        self.lbl_comp_status.pack(anchor="center")
        
        # Action Button
        self.btn_comp_start = ttk.Button(tab, text="압축 파일 생성 및 시작", command=self.start_compress)
        self.btn_comp_start.pack(pady=10)
        
    def select_comp_src(self, is_file):
        if is_file:
            path = filedialog.askopenfilename()
        else:
            path = filedialog.askdirectory()
            
        if path:
            self.comp_src_path = path
            self.lbl_comp_src.config(text=f"선택된 대상: {os.path.basename(path)}")
            self.lbl_comp_status.config(text="압축할 준비가 되었습니다.", foreground="black")
            
    def start_compress(self):
        if not self.comp_src_path:
            messagebox.showwarning("경고", "압축할 파일이나 폴더를 선택해주세요.")
            return
            
        save_path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("Zip files", "*.zip")])
        if not save_path:
            return
            
        pw = self.entry_comp_pw.get()
        if not pw:
            pw = None
            
        self.btn_comp_start.config(state="disabled")
        self.lbl_comp_status.config(text="압축 진행 중...", foreground="blue")
        
        # Compress in background thread to prevent UI lag
        threading.Thread(target=self._run_compress, args=(self.comp_src_path, save_path, pw), daemon=True).start()

    def _run_compress(self, src_path, save_path, pw):
        success, msg = compress_folder_or_file(src_path, save_path, pw)
        self.parent.after(0, lambda: self._compress_finished(success, msg))
        
    def _compress_finished(self, success, msg):
        self.btn_comp_start.config(state="normal")
        if success:
            self.lbl_comp_status.config(text="압축 완료!", foreground="green")
            messagebox.showinfo("성공", "압축이 성공적으로 완료되었습니다.")
            self.entry_comp_pw.delete(0, tk.END)
        else:
            self.lbl_comp_status.config(text=f"압축 실패: {msg}", foreground="red")
            messagebox.showerror("오류", f"압축 실패:\n{msg}")

    # --- Tab 3: Decompress ---
    def create_tab_decompress(self):
        tab = ttk.Frame(self.nested_notebook)
        self.nested_notebook.add(tab, text=" 📂 압축 풀기 (Decompress) ")
        
        # File Selection
        frame_src = ttk.LabelFrame(tab, text="해제할 압축 파일 선택", padding=10)
        frame_src.pack(fill='x', padx=10, pady=10)
        
        self.lbl_decomp_src = ttk.Label(frame_src, text="선택된 파일: 없음", font=("Segoe UI", 9, "italic"))
        self.lbl_decomp_src.pack(side='left', expand=True, fill='x')
        self.decomp_src_path = None
        
        btn_sel_file = ttk.Button(frame_src, text="파일 선택", command=self.select_decomp_src)
        btn_sel_file.pack(side='right')
        
        # Options
        frame_opts = ttk.LabelFrame(tab, text="암호 설정", padding=10)
        frame_opts.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(frame_opts, text="비밀번호 (암호화된 경우):").grid(row=0, column=0, sticky='w', pady=5)
        self.entry_decomp_pw = ttk.Entry(frame_opts, show="*", width=20)
        self.entry_decomp_pw.grid(row=0, column=1, sticky='w', padx=10, pady=5)
        
        # Status Label
        status_frame = ttk.Frame(tab, padding=5)
        status_frame.pack(fill='x', padx=10, pady=10)
        self.lbl_decomp_status = ttk.Label(status_frame, text="대기 중...", font=("Segoe UI", 10, "bold"), foreground="gray")
        self.lbl_decomp_status.pack(anchor="center")
        
        # Action Button
        self.btn_decomp_start = ttk.Button(tab, text="압축 해제 시작", command=self.start_decompress)
        self.btn_decomp_start.pack(pady=10)
        
    def select_decomp_src(self):
        path = filedialog.askopenfilename(filetypes=[("Zip files", "*.zip")])
        if path:
            self.decomp_src_path = path
            self.lbl_decomp_src.config(text=f"선택된 파일: {os.path.basename(path)}")
            self.lbl_decomp_status.config(text="압축 해제할 준비가 되었습니다.", foreground="black")
            
    def start_decompress(self):
        if not self.decomp_src_path:
            messagebox.showwarning("경고", "압축 해제할 Zip 파일을 선택해주세요.")
            return
            
        extract_path = filedialog.askdirectory(title="압축을 해제할 폴더 선택")
        if not extract_path:
            return
            
        pw = self.entry_decomp_pw.get()
        if not pw:
            pw = None
            
        self.btn_decomp_start.config(state="disabled")
        self.lbl_decomp_status.config(text="압축 해제 중...", foreground="blue")
        
        # Decompress in background thread to prevent GUI freeze
        threading.Thread(target=self._run_decompress, args=(self.decomp_src_path, extract_path, pw), daemon=True).start()

    def _run_decompress(self, zip_path, extract_to, pw):
        success, msg = decompress_zip(zip_path, extract_to, pw)
        self.parent.after(0, lambda: self._decompress_finished(success, msg))
        
    def _decompress_finished(self, success, msg):
        self.btn_decomp_start.config(state="normal")
        if success:
            self.lbl_decomp_status.config(text="압축 해제 완료!", foreground="green")
            messagebox.showinfo("성공", "압축 해제가 완료되었습니다.")
            self.entry_decomp_pw.delete(0, tk.END)
        else:
            self.lbl_decomp_status.config(text=f"해제 실패: {msg}", foreground="red")
            messagebox.showerror("오류", f"압축 해제 실패:\n{msg}")
