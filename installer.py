import os
import sys
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
from win32com.client import Dispatch

class SetupWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MT Tool 설치 (Setup)")
        self.geometry("500x350")
        self.resizable(False, False)
        
        # 윈도우 중앙 배치
        self.eval('tk::PlaceWindow . center')
        
        # 아이콘 설정
        icon_path = 'app_icon.ico'
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, 'app_icon.ico')
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')
            
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except:
                pass
            
        self.main_exe = os.path.join(self.base_path, 'mt-tool.exe')
        self.updater_exe = os.path.join(self.base_path, 'updater.exe')
        
        self.create_welcome_page()
        
    def create_welcome_page(self):
        for widget in self.winfo_children():
            widget.destroy()
            
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="MT Tool 설치 마법사", font=("맑은 고딕", 16, "bold")).pack(pady=30)
        
        desc = "이 마법사는 컴퓨터에 'MT Tool'을 설치합니다.\n\n설치되는 동안 열려있는 다른 프로그램들을\n모두 닫아주시는 것을 권장합니다.\n\n설치를 계속하려면 [다음] 버튼을 클릭하세요."
        ttk.Label(frame, text=desc, justify="center", font=("맑은 고딕", 10)).pack(pady=20)
        
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill="x", side="bottom")
        ttk.Button(btn_frame, text="취소", command=self.destroy).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="다음 >", command=self.create_install_page).pack(side="right", padx=5)

    def create_install_page(self):
        # 파일이 정상적으로 패키징되었는지 확인
        if not os.path.exists(self.main_exe) or not os.path.exists(self.updater_exe):
            messagebox.showerror("오류", f"설치 원본 파일을 찾을 수 없습니다.\n경로: {self.base_path}")
            return
            
        for widget in self.winfo_children():
            widget.destroy()
            
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="설치 진행 중...", font=("맑은 고딕", 14, "bold")).pack(pady=20)
        self.status_var = tk.StringVar(value="설치 준비 중...")
        ttk.Label(frame, textvariable=self.status_var).pack(pady=10)
        
        self.progress = ttk.Progressbar(frame, mode='indeterminate')
        self.progress.pack(fill="x", pady=20)
        self.progress.start(10)
        
        self.after(500, self.perform_installation)
        
    def perform_installation(self):
        try:
            target_dir = os.path.join(os.environ.get('LOCALAPPDATA'), 'MT_Tool')
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
                
            self.status_var.set("파일 복사 및 압축 해제 중 (mt-tool.exe)...")
            self.update_idletasks()
            shutil.copy2(self.main_exe, os.path.join(target_dir, 'mt-tool.exe'))
            
            self.status_var.set("파일 복사 중 (updater.exe)...")
            self.update_idletasks()
            shutil.copy2(self.updater_exe, os.path.join(target_dir, 'updater.exe'))
            
            self.status_var.set("바탕화면 및 시작 메뉴 바로가기 생성 중...")
            self.update_idletasks()
            shell = Dispatch('WScript.Shell')
            desktop = shell.SpecialFolders('Desktop')
            shortcut_path = os.path.join(desktop, "MT Tool.lnk")
            
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = os.path.join(target_dir, 'mt-tool.exe')
            shortcut.WorkingDirectory = target_dir
            shortcut.IconLocation = os.path.join(target_dir, 'mt-tool.exe')
            shortcut.save()
            
            # 1초 뒤 완료 화면으로 이동
            self.after(1000, self.create_finish_page)
            
        except Exception as e:
            messagebox.showerror("설치 오류", f"설치 중 시스템 오류가 발생했습니다:\n{e}")
            self.destroy()

    def create_finish_page(self):
        for widget in self.winfo_children():
            widget.destroy()
            
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="설치 완료!", font=("맑은 고딕", 16, "bold"), foreground="green").pack(pady=30)
        ttk.Label(frame, text="MT Tool이 성공적으로 설치되었습니다.\n\n바탕화면의 바로가기를 통해 앱을 실행할 수 있습니다.", justify="center", font=("맑은 고딕", 10)).pack(pady=20)
        
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill="x", side="bottom")
        ttk.Button(btn_frame, text="마침", command=self.destroy).pack(side="right", padx=5)

if __name__ == "__main__":
    app = SetupWizard()
    app.mainloop()
