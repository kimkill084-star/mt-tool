import os
import time
import threading
from tkinter import messagebox
from config_manager import config
import vt_scanner

class DownloadFolderWatcher:
    _instance = None
    
    def __new__(cls, root=None):
        if cls._instance is None:
            cls._instance = super(DownloadFolderWatcher, cls).__new__(cls)
            cls._instance._init_watcher(root)
        elif root is not None:
            cls._instance.root = root
        return cls._instance

    def _init_watcher(self, root):
        self.root = root
        self.running = False
        self.thread = None
        self.known_files = set()
        self.ignore_exts = {
            '.crdownload', '.tmp', '.part', '.download', '.mtt', '.aria2',
            '.partial', '.opdownload'
        }
        self.lock = threading.Lock()

    def add_known(self, file_path):
        """Skip scanning for files that were explicitly handled elsewhere."""
        with self.lock:
            self.known_files.add(os.path.normpath(file_path).lower())

    def start(self, root=None):
        if root:
            self.root = root
        if self.running:
            return
        
        self.running = True
        # Pre-populate known files so existing files aren't scanned on launch
        folder = config.get('download_folder', os.path.join(os.path.expanduser('~'), 'Downloads'))
        if os.path.exists(folder):
            try:
                for entry in os.scandir(folder):
                    if entry.is_file():
                        self.known_files.add(os.path.normpath(entry.path).lower())
            except Exception as e:
                print(f"[Watcher] Error scanning initial files: {e}")

        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        print(f"[Watcher] Download folder watcher started for: {folder}")

    def stop(self):
        self.running = False

    def _is_file_ready(self, file_path):
        """Checks if file is done being written by the browser or another process."""
        if not os.path.exists(file_path):
            return False
        
        # Check size stability over 1 second
        try:
            initial_size = os.path.getsize(file_path)
            time.sleep(1.0)
            if not os.path.exists(file_path):
                return False
            final_size = os.path.getsize(file_path)
            if initial_size != final_size:
                return False
                
            # Try opening in append mode to confirm write locks are released
            with open(file_path, 'ab'):
                pass
            return True
        except (PermissionError, IOError, OSError):
            return False

    def _watch_loop(self):
        while self.running:
            try:
                folder = config.get('download_folder', os.path.join(os.path.expanduser('~'), 'Downloads'))
                vt_enabled = config.get('vt_enabled', False)
                api_key = config.get('vt_api_key', '').strip()

                if not os.path.exists(folder) or not vt_enabled or not api_key:
                    time.sleep(2.0)
                    continue

                # Scan folder for new files
                current_files = []
                try:
                    for entry in os.scandir(folder):
                        if entry.is_file():
                            current_files.append(entry.path)
                except Exception:
                    time.sleep(2.0)
                    continue

                for file_path in current_files:
                    norm_path = os.path.normpath(file_path).lower()
                    filename = os.path.basename(file_path)
                    ext = os.path.splitext(filename)[1].lower()

                    # Ignore temp download extensions and hidden files
                    if ext in self.ignore_exts or filename.startswith(('~', '.')):
                        continue

                    with self.lock:
                        if norm_path in self.known_files:
                            continue

                    # If this is a new file, check if it's finished writing
                    if not self._is_file_ready(file_path):
                        continue

                    # Mark as known before scanning so we don't process it multiple times
                    with self.lock:
                        self.known_files.add(norm_path)

                    # Launch scan in a separate worker thread
                    threading.Thread(target=self._scan_file, args=(file_path, api_key), daemon=True).start()

            except Exception as e:
                print(f"[Watcher] Loop error: {e}")

            time.sleep(2.0)

    def _scan_file(self, file_path, api_key):
        filename = os.path.basename(file_path)
        mtt_path = file_path + '.mtt'

        try:
            # Quarantine the new file with .mtt extension while scanning
            os.rename(file_path, mtt_path)
            print(f"[Watcher] New file quarantined: {filename} -> {os.path.basename(mtt_path)}")
        except Exception as e:
            print(f"[Watcher] Failed to rename {filename} to .mtt: {e}")
            mtt_path = file_path # Fallback to scanning original path if rename fails

        is_safe, msg = vt_scanner.check_file(mtt_path, api_key)

        if is_safe:
            # Restore original extension
            if mtt_path != file_path:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    os.rename(mtt_path, file_path)
                    print(f"[Watcher] Restored safe file: {filename}")
                except Exception as e:
                    print(f"[Watcher] Failed to restore filename for {filename}: {e}")

            # Notify user on GUI main thread
            if self.root:
                self.root.after(0, lambda: self._show_safe_notification(filename, msg))
        else:
            # Keep as .mtt to protect user
            print(f"[Watcher] MALWARE DETECTED in {filename}: {msg}")
            if self.root:
                self.root.after(0, lambda: self._show_malware_alert(filename, msg))

    def _show_safe_notification(self, filename, msg):
        try:
            # Update app status bar if available
            if hasattr(self.root, 'status_bar'):
                self.root.status_bar.config(text=f"[보안 검사 완료] {filename} - 안전함 확인")
        except:
            pass

    def _show_malware_alert(self, filename, msg):
        try:
            messagebox.showwarning(
                "🚨 악성코드 감지 및 격리",
                f"다운로드 폴더에 새로 유입된 파일에서 악성코드가 감지되었습니다!\n\n"
                f"파일명: {filename}\n"
                f"결과: {msg}\n\n"
                f"시스템 보호를 위해 해당 파일은 실행 불가능한 임시 확장자(.mtt)로 안전하게 격리되었습니다.",
                parent=self.root
            )
        except Exception as e:
            print(f"[Watcher] Alert error: {e}")

# Global watcher instance
watcher = DownloadFolderWatcher()
