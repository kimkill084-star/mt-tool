import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import qrcode
import socket
import threading
import os
import re
import urllib.parse
import http.server

# Custom HTTP handler to support Uploads and Downloads in pure Python (Python 3.12+ compatible)
class FileShareHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Serve from the custom configured directory
        root = self.server.share_dir
        # Simple URL decoding
        path = urllib.parse.unquote(path)
        # Prevent path traversal
        path = path.lstrip('/')
        parts = path.split('/')
        new_parts = []
        for part in parts:
            if part in (os.curdir, os.pardir) or not part:
                continue
            new_parts.append(part)
        return os.path.join(root, *new_parts)

    def do_GET(self):
        # If accessing the root, serve a beautiful mobile-friendly index page
        parts = urllib.parse.urlparse(self.path)
        if parts.path in ('/', '/index.html'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = self.generate_html()
            self.wfile.write(html.encode('utf-8'))
        else:
            # Otherwise use default file downloader handler
            super().do_GET()

    def do_POST(self):
        if self.path == '/upload':
            try:
                # Parse upload content type and length
                content_type = self.headers['content-type']
                if not content_type or 'multipart/form-data' not in content_type:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Bad Request: multipart/form-data required")
                    return
                
                boundary = content_type.split("boundary=")[1].encode()
                content_length = int(self.headers['content-length'])
                
                # Read body
                body = self.rfile.read(content_length)
                
                # Parse multipart sections
                parts = body.split(b'--' + boundary)
                uploaded_count = 0
                
                for part in parts:
                    if not part or part.strip() == b'--':
                        continue
                    if b'\r\n\r\n' in part:
                        header, content = part.split(b'\r\n\r\n', 1)
                        if b'filename="' in header:
                            # Extract filename
                            header_str = header.decode('utf-8', errors='ignore')
                            match = re.search(r'filename="([^"]+)"', header_str)
                            if match:
                                filename = os.path.basename(match.group(1))
                                # Clean filename
                                if filename:
                                    # Strip trailing boundary artifacts
                                    if content.endswith(b'\r\n'):
                                        content = content[:-2]
                                    if content.endswith(b'--'):
                                        content = content[:-2]
                                    if content.endswith(b'\r\n'):
                                        content = content[:-2]
                                        
                                    out_path = os.path.join(self.server.share_dir, filename)
                                    with open(out_path, 'wb') as f:
                                        f.write(content)
                                    uploaded_count += 1
                
                # Redirect back to index with success message
                self.send_response(303)
                self.send_header('Location', '/')
                self.end_headers()
                
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Upload failed: {e}".encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def generate_html(self):
        share_dir = self.server.share_dir
        # Get list of files
        files_list = []
        try:
            for item in os.listdir(share_dir):
                full_path = os.path.join(share_dir, item)
                if os.path.isfile(full_path):
                    size = os.path.getsize(full_path)
                    if size > 1024 * 1024:
                        size_str = f"{size / (1024*1024):.2f} MB"
                    else:
                        size_str = f"{size / 1024:.2f} KB"
                    files_list.append((item, size_str))
        except Exception:
            pass
            
        # Generate responsive HTML
        files_html = ""
        if files_list:
            for name, size in files_list:
                enc_name = urllib.parse.quote(name)
                files_html += f"""
                <div class="file-item">
                    <span class="file-name">📄 {name} <span class="file-size">({size})</span></span>
                    <a href="/{enc_name}" class="btn-download" download>다운로드</a>
                </div>
                """
        else:
            files_html = "<p class='no-files'>공유 폴더가 비어 있습니다.</p>"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>무선 파일 공유</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    background-color: #f7f9fa;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background: white;
                    padding: 25px;
                    border-radius: 12px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                }}
                h2 {{
                    margin-top: 0;
                    color: #0076ff;
                    border-bottom: 2px solid #f0f3f5;
                    padding-bottom: 12px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }}
                .upload-section {{
                    background: #f0f7ff;
                    border: 2px dashed #a4c9ff;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 25px;
                    text-align: center;
                }}
                .upload-section h3 {{
                    margin-top: 0;
                    color: #0053b8;
                }}
                .file-list-section h3 {{
                    color: #444;
                    margin-bottom: 15px;
                }}
                .file-item {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px;
                    border-bottom: 1px solid #f0f0f0;
                }}
                .file-name {{
                    font-weight: 500;
                    word-break: break-all;
                    margin-right: 10px;
                }}
                .file-size {{
                    font-size: 0.8em;
                    color: #888;
                    font-weight: normal;
                }}
                .btn-download {{
                    background-color: #0076ff;
                    color: white;
                    text-decoration: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 0.9em;
                    font-weight: 500;
                    white-space: nowrap;
                }}
                .btn-submit {{
                    background-color: #0053b8;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    font-size: 1em;
                    cursor: pointer;
                    font-weight: bold;
                    margin-top: 10px;
                    width: 100%;
                }}
                .no-files {{
                    color: #888;
                    font-style: italic;
                    text-align: center;
                    padding: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>📡 무선 파일 공유</h2>
                
                <!-- Upload form -->
                <div class="upload-section">
                    <h3>PC로 파일 업로드</h3>
                    <form method="POST" enctype="multipart/form-data" action="/upload">
                        <input type="file" name="files" multiple style="width: 100%; max-width: 300px; margin: 10px auto;">
                        <input type="submit" value="업로드 시작" class="btn-submit">
                    </form>
                </div>
                
                <!-- Downloader list -->
                <div class="file-list-section">
                    <h3>공유된 파일 목록</h3>
                    {files_html}
                </div>
            </div>
        </body>
        </html>
        """
        return html


class ShareTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        # State variables
        self.share_folder = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.exists(self.share_folder):
            self.share_folder = os.getcwd()
            
        self.server = None
        self.server_thread = None
        self.is_sharing = False
        self.local_ip = self.get_local_ip()
        self.port = 8080
        self.qr_photo = None
        
        self.create_widgets()

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        
        # Left Panel (Folder Setup and Controls)
        left_panel = ttk.LabelFrame(self, text="파일 공유 설정", padding=15)
        left_panel.grid(row=0, column=0, sticky="nswe", padx=10, pady=10)
        
        ttk.Label(left_panel, text="공유할 폴더 선택:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))
        self.folder_lbl = ttk.Label(left_panel, text=self.share_folder, font=("Segoe UI", 9, "italic"), wraplength=350, anchor="w")
        self.folder_lbl.pack(fill="x", pady=5)
        
        self.btn_select_folder = ttk.Button(left_panel, text="공유 폴더 변경", command=self.select_folder)
        self.btn_select_folder.pack(fill="x", pady=5)
        
        ttk.Separator(left_panel, orient="horizontal").pack(fill="x", pady=15)
        
        # Share Controls
        ttk.Label(left_panel, text="공유 서버 제어:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))
        self.btn_toggle_share = ttk.Button(left_panel, text="공유 시작 (Start Share)", command=self.toggle_share)
        self.btn_toggle_share.pack(fill="x", pady=10)
        
        self.status_lbl = ttk.Label(left_panel, text="공유 비활성화 상태.", font=("Segoe UI", 10, "bold"), foreground="red")
        self.status_lbl.pack(anchor="center", pady=10)
        
        # Guide Info
        self.info_text = ttk.Label(left_panel, text="동일한 공유기(Wi-Fi)에 연결된 휴대폰이나 다른 PC 브라우저에서 아래의 주소로 접속하면 전선 연결 없이 편리하게 파일을 양방향으로 보낼 수 있습니다.", wraplength=350, foreground="gray")
        self.info_text.pack(fill="x", side="bottom", pady=10)
        
        # Right Panel (QR Code and Connection details)
        self.right_panel = ttk.LabelFrame(self, text="접속 정보 (QR 코드)", padding=15)
        self.right_panel.grid(row=0, column=1, sticky="nswe", padx=10, pady=10)
        self.right_panel.columnconfigure(0, weight=1)
        self.right_panel.rowconfigure(1, weight=1)
        
        self.addr_lbl = ttk.Label(self.right_panel, text="공유를 시작하면 주소가 표시됩니다.", font=("Segoe UI", 10, "bold"), foreground="blue", anchor="center")
        self.addr_lbl.grid(row=0, column=0, pady=10, sticky="we")
        
        self.qr_canvas = tk.Canvas(self.right_panel, bg="#f0f0f0", width=250, height=250, highlightthickness=1, highlightbackground="#cccccc")
        self.qr_canvas.grid(row=1, column=0, pady=10)
        self.qr_canvas.create_text(125, 125, text="QR 코드 대기 중", fill="gray")

    def select_folder(self):
        if self.is_sharing:
            messagebox.showwarning("경고", "공유 중에는 폴더를 변경할 수 없습니다. 공유를 먼저 중지해 주세요.")
            return
            
        path = filedialog.askdirectory(initialdir=self.share_folder)
        if path:
            self.share_folder = path
            self.folder_lbl.config(text=self.share_folder)

    def toggle_share(self):
        if not self.is_sharing:
            self.start_server()
        else:
            self.stop_server()

    def start_server(self):
        # Choose a free port
        self.port = 8080
        # Try to find a free port if 8080 is blocked
        for p in range(8080, 8100):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(('', p))
                s.close()
                self.port = p
                break
            except Exception:
                continue
                
        # Start socketserver HTTP in thread
        try:
            handler = FileShareHTTPHandler
            # We configure server attributes directly
            class CustomHTTPServer(http.server.HTTPServer):
                def __init__(self, server_address, RequestHandlerClass, share_dir):
                    super().__init__(server_address, RequestHandlerClass)
                    self.share_dir = share_dir
                    
            self.server = CustomHTTPServer(('', self.port), handler, self.share_folder)
            
            self.is_sharing = True
            self.btn_toggle_share.config(text="공유 중지 (Stop Share)")
            self.btn_select_folder.config(state="disabled")
            
            url = f"http://{self.local_ip}:{self.port}"
            self.status_lbl.config(text="공유 활성화 중!", foreground="green")
            self.addr_lbl.config(text=f"접속 주소: {url}")
            
            # Start background thread
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            # Generate QR code
            self.generate_qr(url)
            
        except Exception as e:
            self.stop_server()
            messagebox.showerror("오류", f"공유 서버 시작 실패: {e}")

    def generate_qr(self, data):
        try:
            qr = qrcode.QRCode(version=1, box_size=6, border=4)
            qr.add_data(data)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to TK PhotoImage
            self.qr_photo = ImageTk.PhotoImage(qr_img)
            
            # Draw on canvas
            self.qr_canvas.delete("all")
            self.qr_canvas.create_image(125, 125, image=self.qr_photo, anchor="center")
        except Exception as e:
            self.qr_canvas.delete("all")
            self.qr_canvas.create_text(125, 125, text="QR 생성 실패", fill="red")

    def stop_server(self):
        self.is_sharing = False
        self.btn_toggle_share.config(text="공유 시작 (Start Share)")
        self.btn_select_folder.config(state="normal")
        self.status_lbl.config(text="공유 비활성화 상태.", foreground="red")
        self.addr_lbl.config(text="공유를 시작하면 주소가 표시됩니다.", foreground="black")
        
        # Clear QR Canvas
        self.qr_canvas.delete("all")
        self.qr_canvas.create_text(125, 125, text="QR 코드 대기 중", fill="gray")
        self.qr_photo = None
        
        if self.server:
            # Shutdown server
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            self.server = None
            self.server_thread = None
