import os
import sys
import json
import urllib.request
import tempfile
import threading
import subprocess
from tkinter import messagebox

# Current version of the app
CURRENT_VERSION = "1.0.0"

def get_github_api_url():
    owner = 'kimkill084-star'
    repo = 'mt-tool'
    return f"https://api.github.com/repos/{owner}/{repo}/releases/latest"

def check_for_updates(parent_window, manual=False):
    """
    Checks for updates asynchronously and prompts the user if one is found.
    If manual=True, it will alert the user even if there are no updates.
    """
    def _check():
        try:
            api_url = get_github_api_url()
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                
                latest_version = data.get('tag_name', '').lstrip('v')
                if not latest_version:
                    if manual: parent_window.after(0, lambda: messagebox.showinfo("업데이트", "최신 버전 정보를 가져올 수 없습니다.", parent=parent_window))
                    return

                # Very basic version string comparison (assuming semantic versioning x.y.z)
                if _is_newer(CURRENT_VERSION, latest_version):
                    # Find zip asset
                    zip_url = None
                    for asset in data.get('assets', []):
                        if asset.get('name', '').endswith('.zip'):
                            zip_url = asset.get('browser_download_url')
                            break
                    
                    if zip_url:
                        parent_window.after(0, lambda: _prompt_update(parent_window, latest_version, zip_url))
                    elif manual:
                        parent_window.after(0, lambda: messagebox.showinfo("업데이트", "새 버전이 릴리즈 되었으나 업데이트 파일(.zip)이 없습니다.", parent=parent_window))
                elif manual:
                    parent_window.after(0, lambda: messagebox.showinfo("업데이트", f"이미 최신 버전입니다 (v{CURRENT_VERSION}).", parent=parent_window))
        except Exception as e:
            err_msg = str(e)
            if manual: parent_window.after(0, lambda msg=err_msg: messagebox.showerror("오류", f"업데이트 확인 중 오류가 발생했습니다:\n{msg}", parent=parent_window))
            else: print(f"Update check failed: {err_msg}")

    threading.Thread(target=_check, daemon=True).start()

def _is_newer(current, latest):
    try:
        curr_parts = [int(x) for x in current.split('.')]
        latest_parts = [int(x) for x in latest.split('.')]
        return latest_parts > curr_parts
    except:
        return current != latest

def _prompt_update(parent_window, latest_version, zip_url):
    result = messagebox.askyesno(
        "업데이트 알림",
        f"새로운 버전(v{latest_version})이 출시되었습니다!\n현재 버전: v{CURRENT_VERSION}\n\n지금 업데이트하시겠습니까?"
    )
    if result:
        _download_and_apply_update(parent_window, zip_url)

def _download_and_apply_update(parent_window, zip_url):
    import tkinter as tk
    from tkinter import ttk
    
    # Show downloading dialog
    dl_win = tk.Toplevel(parent_window)
    dl_win.title("업데이트 다운로드 중...")
    dl_win.geometry("300x100")
    dl_win.transient(parent_window)
    dl_win.grab_set()
    
    ttk.Label(dl_win, text="최신 버전을 다운로드 중입니다. 잠시만 기다려주세요.").pack(pady=10)
    progress = ttk.Progressbar(dl_win, mode='indeterminate')
    progress.pack(fill='x', padx=20, pady=5)
    progress.start()

    def _download():
        try:
            # Download to temp file
            temp_zip_fd, temp_zip_path = tempfile.mkstemp(suffix='.zip')
            os.close(temp_zip_fd)
            
            req = urllib.request.Request(zip_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(temp_zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            
            # Apply update
            dl_win.after(0, lambda: _run_updater(temp_zip_path))
            
        except Exception as e:
            dl_win.after(0, dl_win.destroy)
            dl_win.after(0, lambda: messagebox.showerror("업데이트 오류", f"업데이트 다운로드 중 오류가 발생했습니다:\n{e}"))
            
    import shutil
    threading.Thread(target=_download, daemon=True).start()

def _run_updater(zip_path):
    # Determine app directory and executable name
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        app_dir = os.path.dirname(sys.executable)
        executable_name = os.path.basename(sys.executable)
        updater_path = os.path.join(app_dir, 'updater.exe')
    else:
        # Running from source
        app_dir = os.path.dirname(os.path.abspath(__file__))
        executable_name = 'main.py'
        updater_path = sys.executable # python.exe
        
    if getattr(sys, 'frozen', False) and not os.path.exists(updater_path):
        messagebox.showerror("오류", "updater.exe를 찾을 수 없어 업데이트를 진행할 수 없습니다.")
        return
        
    try:
        if getattr(sys, 'frozen', False):
            subprocess.Popen([updater_path, app_dir, zip_path, executable_name])
        else:
            # Running from source, launch updater.py directly
            updater_script = os.path.join(app_dir, 'updater.py')
            subprocess.Popen([updater_path, updater_script, app_dir, zip_path, executable_name])
            
        # Exit current app
        sys.exit(0)
    except Exception as e:
        messagebox.showerror("오류", f"업데이터 실행 중 오류가 발생했습니다:\n{e}")
