import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pyttsx3
import edge_tts
import asyncio
import threading
import os
import ctypes
import tempfile
import json
import base64
import urllib.request
import urllib.error
from config_manager import config

class TtsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        # State variables
        self.sapi_voices = []      # List of (display_name, id)
        self.edge_voices = [
            ("한국어 (여성) - 선희 (SunHi)", "ko-KR-SunHiNeural"),
            ("한국어 (남성) - 인준 (InJoon)", "ko-KR-InJoonNeural"),
            ("한국어 (다국어/여성) - 현수 (Hyunsu)", "ko-KR-HyunsuMultilingualNeural"),
            ("영어 (여성) - 제니 (Jenny)", "en-US-JennyNeural"),
            ("영어 (여성) - 아리아 (Aria)", "en-US-AriaNeural"),
            ("영어 (남성) - 가이 (Guy)", "en-US-GuyNeural"),
            ("영어 (남성) - 스테판 (Steffan)", "en-US-SteffanNeural"),
            ("일본어 (여성) - 나나미 (Nanami)", "ja-JP-NanamiNeural"),
            ("일본어 (남성) - 케이타 (Keita)", "ja-JP-KeitaNeural")
        ]
        
        self.google_voices = [
            ("한국어 (여성) - Wavenet A", "ko-KR-Wavenet-A"),
            ("한국어 (여성) - Wavenet B", "ko-KR-Wavenet-B"),
            ("한국어 (남성) - Wavenet C", "ko-KR-Wavenet-C"),
            ("한국어 (남성) - Wavenet D", "ko-KR-Wavenet-D"),
            ("한국어 (여성) - Standard A", "ko-KR-Standard-A"),
            ("한국어 (여성) - Standard B", "ko-KR-Standard-B"),
            ("한국어 (남성) - Standard C", "ko-KR-Standard-C"),
            ("한국어 (남성) - Standard D", "ko-KR-Standard-D")
        ]
        
        self.active_engine = None  # Reference to the active pyttsx3 engine (if using sapi5)
        self.is_speaking = False
        self.temp_mp3 = os.path.join(tempfile.gettempdir(), "edge_tts_temp.mp3")
        
        self.create_widgets()
        self.load_sapi_voices()
        
        # Trigger default UI setup
        self.on_engine_change()

    def create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1) # Text area takes main space
        
        # --- Top Text Input ---
        text_frame = ttk.LabelFrame(self, text="텍스트 입력", padding=10)
        text_frame.grid(row=0, column=0, sticky="nswe", padx=5, pady=5)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        self.text_input = tk.Text(text_frame, wrap="word", font=("Malgun Gothic", 10))
        self.text_input.grid(row=0, column=0, sticky="nswe")
        self.text_input.insert("1.0", "안녕하세요! 이 프로그램은 오프라인 TTS와 온라인 AI 뉴럴 TTS 기능을 모두 지원하는 도구입니다. 여기에 원하는 내용을 입력하고 목소리를 들어보세요.")
        
        scroll = ttk.Scrollbar(text_frame, command=self.text_input.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.text_input.config(yscrollcommand=scroll.set)
        
        # --- Bottom Settings Panel ---
        settings_frame = ttk.LabelFrame(self, text="TTS 설정 및 제어", padding=10)
        settings_frame.grid(row=1, column=0, sticky="we", padx=5, pady=5)
        settings_frame.columnconfigure(1, weight=1)
        
        # 1. Engine Selection Row
        ttk.Label(settings_frame, text="엔진 선택:").grid(row=0, column=0, sticky="w", pady=5)
        self.engine_var = tk.StringVar(value="edge")
        opt_frame = ttk.Frame(settings_frame)
        opt_frame.grid(row=0, column=1, columnspan=2, sticky="w", pady=5, padx=5)
        ttk.Radiobutton(opt_frame, text="온라인 (Edge TTS - 무료)", variable=self.engine_var, value="edge", command=self.on_engine_change).pack(side="left", padx=5)
        ttk.Radiobutton(opt_frame, text="온라인 (Google Cloud - API 필요)", variable=self.engine_var, value="google", command=self.on_engine_change).pack(side="left", padx=5)
        ttk.Radiobutton(opt_frame, text="온라인 (Typecast - API 필요)", variable=self.engine_var, value="typecast", command=self.on_engine_change).pack(side="left", padx=5)
        ttk.Radiobutton(opt_frame, text="오프라인 (SAPI5)", variable=self.engine_var, value="sapi5", command=self.on_engine_change).pack(side="left", padx=5)
        
        # 2. Voice Dropdown Row
        ttk.Label(settings_frame, text="목소리 선택:").grid(row=1, column=0, sticky="w", pady=5)
        self.voice_combo = ttk.Combobox(settings_frame, state="readonly")
        self.voice_combo.grid(row=1, column=1, columnspan=2, sticky="we", pady=5, padx=5)
        
        # 3. Speed Slider Row
        ttk.Label(settings_frame, text="말하기 속도:").grid(row=2, column=0, sticky="w", pady=5)
        self.rate_val = tk.IntVar(value=0)
        self.rate_scale = ttk.Scale(settings_frame, from_=-50, to=50, variable=self.rate_val, orient="horizontal")
        self.rate_scale.grid(row=2, column=1, sticky="we", pady=5, padx=5)
        self.rate_lbl = ttk.Label(settings_frame, text="+0%")
        self.rate_lbl.grid(row=2, column=2, sticky="e", pady=5, padx=5)
        self.rate_scale.bind("<Motion>", self.update_rate_label)
        self.rate_scale.bind("<ButtonRelease-1>", self.update_rate_label)
        
        # 4. Volume Slider Row
        ttk.Label(settings_frame, text="음량 (Volume):").grid(row=3, column=0, sticky="w", pady=5)
        self.vol_val = tk.IntVar(value=100)
        self.vol_scale = ttk.Scale(settings_frame, from_=0, to=100, variable=self.vol_val, orient="horizontal")
        self.vol_scale.grid(row=3, column=1, sticky="we", pady=5, padx=5)
        self.vol_lbl = ttk.Label(settings_frame, text="100%")
        self.vol_lbl.grid(row=3, column=2, sticky="e", pady=5, padx=5)
        self.vol_scale.bind("<Motion>", self.update_vol_label)
        self.vol_scale.bind("<ButtonRelease-1>", self.update_vol_label)
        
        # Action Buttons Row
        btn_frame = ttk.Frame(settings_frame)
        btn_frame.grid(row=4, column=0, columnspan=3, sticky="we", pady=10)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)
        
        self.speak_btn = ttk.Button(btn_frame, text="목소리 듣기 (Speak)", command=self.start_speak)
        self.speak_btn.grid(row=0, column=0, padx=5, sticky="we")
        
        self.stop_btn = ttk.Button(btn_frame, text="정지 (Stop)", command=self.stop_speak, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=5, sticky="we")
        
        self.save_btn = ttk.Button(btn_frame, text="오디오 파일로 저장", command=self.start_save)
        self.save_btn.grid(row=0, column=2, padx=5, sticky="we")
        
        # Status Label Row
        self.status_lbl = ttk.Label(settings_frame, text="준비됨.", foreground="gray")
        self.status_lbl.grid(row=5, column=0, columnspan=3, sticky="w", pady=5)

    def load_sapi_voices(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
            
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            
            self.sapi_voices = []
            for voice in voices:
                name = voice.name
                if "KO-KR" in voice.id.upper() or "KOREAN" in name.upper():
                    name = f"한국어 - {name}"
                elif "EN-US" in voice.id.upper() or "ENGLISH" in name.upper():
                    name = f"영어 - {name}"
                
                lang_suffix = ""
                if hasattr(voice, 'languages') and voice.languages:
                    lang_suffix = f" ({voice.languages[0]})"
                    
                display_name = f"{name}{lang_suffix} [로컬]"
                self.sapi_voices.append((display_name, voice.id))
                
            pythoncom.CoUninitialize()
        except Exception as e:
            # Handle silently, fallback if sapi5 initialization fails
            self.sapi_voices = [("로컬 목소리를 로드하지 못했습니다.", None)]

    def on_engine_change(self):
        engine_mode = self.engine_var.get()
        
        if engine_mode == "edge":
            # Set up combo box for Edge TTS
            combo_values = [v[0] for v in self.edge_voices]
            self.voice_combo["values"] = combo_values
            self.voice_combo.current(0) # SunHi default
            
            # Reconfigure rate slider for Edge TTS: -50% to +50%
            self.rate_scale.config(from_=-50, to=50)
            self.rate_val.set(0)
            self.rate_lbl.config(text="+0%")
            
            # Reconfigure vol slider for Edge: -50% to +50% (percentage adjustments)
            self.vol_scale.config(from_=-50, to=50)
            self.vol_val.set(0)
            self.vol_lbl.config(text="+0%")
            
        elif engine_mode == "google":
            # Set up combo box for Google Cloud TTS
            combo_values = [v[0] for v in self.google_voices]
            self.voice_combo["values"] = combo_values
            self.voice_combo.current(0)
            
            # Rate for Google: 0.25 to 4.0
            self.rate_scale.config(from_=0.25, to=4.0)
            self.rate_val.set(1.0)
            self.rate_lbl.config(text="1.0x")
            
            # Vol for Google: -96.0 to 16.0 (dB)
            self.vol_scale.config(from_=-96, to=16)
            self.vol_val.set(0)
            self.vol_lbl.config(text="0dB")
            
        elif engine_mode == "typecast":
            self.voice_combo["values"] = ["설정창에 입력된 Voice ID 사용"]
            self.voice_combo.current(0)
            
            # Rate for Typecast: 0.5 to 2.0 (example)
            self.rate_scale.config(from_=0.5, to=2.0)
            self.rate_val.set(1.0)
            self.rate_lbl.config(text="1.0x")
            
            # Vol for Typecast
            self.vol_scale.config(from_=-10, to=10)
            self.vol_val.set(0)
            self.vol_lbl.config(text="0")
            
        else: # sapi5
            # Set up combo box for SAPI5
            combo_values = [v[0] for v in self.sapi_voices]
            self.voice_combo["values"] = combo_values
            if combo_values:
                # Find Korean if available
                ko_idx = 0
                for idx, val in enumerate(combo_values):
                    if "한국어" in val:
                        ko_idx = idx
                        break
                self.voice_combo.current(ko_idx)
                
            # Reconfigure rate slider for SAPI5: 100 to 300
            self.rate_scale.config(from_=100, to=300)
            self.rate_val.set(180)
            self.rate_lbl.config(text="180")
            
            # Reconfigure vol slider for SAPI5: 0 to 100
            self.vol_scale.config(from_=0, to=100)
            self.vol_val.set(100)
            self.vol_lbl.config(text="100%")

    def update_rate_label(self, *args):
        val = self.rate_val.get()
        if self.engine_var.get() == "edge":
            text = f"+{int(val)}%" if val >= 0 else f"{int(val)}%"
        elif self.engine_var.get() in ["google", "typecast"]:
            text = f"{val:.2f}x"
        else:
            text = str(int(val))
        self.rate_lbl.config(text=text)

    def update_vol_label(self, *args):
        val = self.vol_val.get()
        if self.engine_var.get() == "edge":
            text = f"+{int(val)}%" if val >= 0 else f"{int(val)}%"
        elif self.engine_var.get() == "google":
            text = f"{int(val)}dB"
        elif self.engine_var.get() == "typecast":
            text = f"{int(val)}"
        else:
            text = f"{int(val)}%"
        self.vol_lbl.config(text=text)

    def get_selected_voice_id(self):
        idx = self.voice_combo.current()
        if idx >= 0:
            engine = self.engine_var.get()
            if engine == "edge":
                return self.edge_voices[idx][1]
            elif engine == "google":
                return self.google_voices[idx][1]
            elif engine == "typecast":
                return config.get('typecast_voice_id', '').strip()
            else:
                return self.sapi_voices[idx][1]
        return None

    # --- MCI Native Playback Helpers ---
    def play_via_mci(self, file_path):
        mci = ctypes.windll.winmm.mciSendStringW
        mci("close myaudio", None, 0, 0)
        
        abs_path = os.path.abspath(file_path).replace('/', '\\')
        
        # MCI needs types depending on extension, MP3 is best loaded as mpegvideo
        if file_path.lower().endswith(".mp3"):
            cmd = f'open "{abs_path}" type mpegvideo alias myaudio'
        else:
            cmd = f'open "{abs_path}" alias myaudio'
            
        ret = mci(cmd, None, 0, 0)
        if ret != 0:
            # Retry without type specifier if it failed
            mci(f'open "{abs_path}" alias myaudio', None, 0, 0)
            
        mci("play myaudio", None, 0, 0)
        
        # Start checking playback status to auto-restore GUI buttons
        self.is_speaking = True
        self.check_mci_status()

    def check_mci_status(self):
        if not self.is_speaking:
            return
            
        mci = ctypes.windll.winmm.mciSendStringW
        buf = ctypes.create_unicode_buffer(128)
        mci("status myaudio mode", buf, 128, 0)
        mode = buf.value.strip()
        
        if mode == "playing":
            # Keep checking every 200ms
            self.parent.after(200, self.check_mci_status)
        else:
            # Finished or stopped
            self.speak_finished()

    def stop_via_mci(self):
        mci = ctypes.windll.winmm.mciSendStringW
        mci("stop myaudio", None, 0, 0)
        mci("close myaudio", None, 0, 0)

    # --- Speaking controls ---
    def start_speak(self):
        text = self.text_input.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning("경고", "읽을 텍스트를 입력해주세요.")
            return
            
        voice_id = self.get_selected_voice_id()
        if not voice_id:
            messagebox.showwarning("경고", "목소리를 선택해주세요.")
            return
            
        self.speak_btn.config(state="disabled")
        self.save_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_lbl.config(text="음성 합성 및 출력 중...", foreground="blue")
        
        engine_mode = self.engine_var.get()
        rate = self.rate_val.get()
        vol = self.vol_val.get()
        
        if engine_mode == "edge":
            # edge-tts is async, run in thread
            threading.Thread(target=self.run_edge_speak, args=(text, voice_id, rate, vol), daemon=True).start()
        elif engine_mode == "google":
            threading.Thread(target=self.run_google_speak, args=(text, voice_id, rate, vol), daemon=True).start()
        elif engine_mode == "typecast":
            threading.Thread(target=self.run_typecast_speak, args=(text, voice_id, rate, vol), daemon=True).start()
        else:
            # SAPI5 local speak, run in thread
            threading.Thread(target=self.run_sapi_speak, args=(text, voice_id, rate, vol), daemon=True).start()

    def run_edge_speak(self, text, voice, rate_val, vol_val):
        try:
            # Format rates/volumes for Edge (e.g. +10% or -5%)
            rate_str = f"+{rate_val}%" if rate_val >= 0 else f"{rate_val}%"
            vol_str = f"+{vol_val}%" if vol_val >= 0 else f"{vol_val}%"
            
            # Clean up old temp file if it exists
            if os.path.exists(self.temp_mp3):
                try:
                    os.remove(self.temp_mp3)
                except Exception:
                    pass
            
            # Generate speech file asynchronously
            async def generate():
                communicate = edge_tts.Communicate(text, voice, rate=rate_str, volume=vol_str)
                await communicate.save(self.temp_mp3)
                
            asyncio.run(generate())
            
            # Safe call play on main thread
            self.parent.after(0, lambda: self.play_via_mci(self.temp_mp3))
            
        except Exception as e:
            err_msg = str(e)
            self.parent.after(0, lambda: self.speak_error(f"AI 음성 합성 실패:\n인터넷 연결을 확인하세요.\n{err_msg}"))

    def run_sapi_speak(self, text, voice_id, rate, vol):
        import pythoncom
        pythoncom.CoInitialize()
        try:
            engine = pyttsx3.init()
            self.active_engine = engine
            engine.setProperty('voice', voice_id)
            engine.setProperty('rate', rate)
            engine.setProperty('volume', vol / 100.0)
            
            # We save SAPI5 to temp WAV file and play it via MCI to allow easy, 
            # reliable asynchronous stopping without COM threading crashes!
            temp_wav = os.path.join(tempfile.gettempdir(), "sapi5_temp.wav")
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass
                    
            engine.save_to_file(text, temp_wav)
            engine.runAndWait()
            
            # Safe call play on main thread
            self.parent.after(0, lambda: self.play_via_mci(temp_wav))
            
        except Exception as e:
            err_msg = str(e)
            self.parent.after(0, lambda: self.speak_error(err_msg))
        finally:
            self.active_engine = None
            pythoncom.CoUninitialize()

    def speak_error(self, err_msg):
        self.speak_finished()
        messagebox.showerror("TTS 오류", err_msg)

    def stop_speak(self):
        self.is_speaking = False
        self.stop_via_mci()
        
        # Also stop SAPI5 engine if active
        if self.active_engine:
            try:
                self.active_engine.stop()
            except Exception:
                pass
                
        self.speak_finished()

    def speak_finished(self):
        self.is_speaking = False
        self.speak_btn.config(state="normal")
        self.save_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_lbl.config(text="준비됨.", foreground="gray")

    # --- Save to file controls ---
    def start_save(self):
        text = self.text_input.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning("경고", "저장할 텍스트를 입력해주세요.")
            return
            
        voice_id = self.get_selected_voice_id()
        if not voice_id:
            messagebox.showwarning("경고", "목소리를 선택해주세요.")
            return
            
        engine_mode = self.engine_var.get()
        def_ext = ".mp3" if engine_mode in ["edge", "google", "typecast"] else ".wav"
        file_types = [("MP3 Audio files", "*.mp3"), ("All files", "*.*")] if engine_mode in ["edge", "google", "typecast"] else [("WAV Audio files", "*.wav"), ("All files", "*.*")]
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=def_ext,
            filetypes=file_types
        )
        if not file_path:
            return
            
        self.speak_btn.config(state="disabled")
        self.save_btn.config(state="disabled")
        self.status_lbl.config(text="오디오 파일 생성 중...", foreground="blue")
        
        rate = self.rate_val.get()
        vol = self.vol_val.get()
        
        if engine_mode == "edge":
            threading.Thread(target=self.run_edge_save, args=(text, voice_id, rate, vol, file_path), daemon=True).start()
        elif engine_mode == "google":
            threading.Thread(target=self.run_google_save, args=(text, voice_id, rate, vol, file_path), daemon=True).start()
        elif engine_mode == "typecast":
            threading.Thread(target=self.run_typecast_save, args=(text, voice_id, rate, vol, file_path), daemon=True).start()
        else:
            threading.Thread(target=self.run_sapi_save, args=(text, voice_id, rate, vol, file_path), daemon=True).start()

    def run_edge_save(self, text, voice, rate_val, vol_val, file_path):
        try:
            rate_str = f"+{rate_val}%" if rate_val >= 0 else f"{rate_val}%"
            vol_str = f"+{vol_val}%" if vol_val >= 0 else f"{vol_val}%"
            
            async def generate():
                communicate = edge_tts.Communicate(text, voice, rate=rate_str, volume=vol_str)
                await communicate.save(file_path)
                
            asyncio.run(generate())
            self.parent.after(0, lambda: self.save_finished(True, file_path))
        except Exception as e:
            err_msg = str(e)
            self.parent.after(0, lambda: self.save_finished(False, f"AI 저장 실패: {err_msg}"))

    def run_sapi_save(self, text, voice_id, rate, vol, file_path):
        import pythoncom
        pythoncom.CoInitialize()
        try:
            engine = pyttsx3.init()
            engine.setProperty('voice', voice_id)
            engine.setProperty('rate', rate)
            engine.setProperty('volume', vol / 100.0)
            
            engine.save_to_file(text, file_path)
            engine.runAndWait()
            
            self.parent.after(0, lambda: self.save_finished(True, file_path))
        except Exception as e:
            err_msg = str(e)
            self.parent.after(0, lambda: self.save_finished(False, err_msg))
        finally:
            pythoncom.CoUninitialize()

    def _call_google_tts_api(self, text, voice_id, rate, vol, out_path):
        api_key = config.get('google_tts_api_key', '').strip()
        if not api_key:
            raise ValueError("설정에서 Google TTS API Key를 먼저 입력해주세요.")
            
        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
        
        payload = {
            "input": {"text": text},
            "voice": {"languageCode": "ko-KR", "name": voice_id},
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": float(rate),
                "volumeGainDb": float(vol)
            }
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                resp_data = json.loads(response.read().decode('utf-8'))
                audio_content = resp_data.get('audioContent')
                if not audio_content:
                    raise ValueError("API 응답에 오디오 데이터가 없습니다.")
                
                with open(out_path, 'wb') as f:
                    f.write(base64.b64decode(audio_content))
                    
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8')
            raise Exception(f"HTTP {e.code}: {err_body}")
            
    def run_google_speak(self, text, voice_id, rate, vol):
        try:
            if os.path.exists(self.temp_mp3):
                try: os.remove(self.temp_mp3)
                except Exception: pass
                
            self._call_google_tts_api(text, voice_id, rate, vol, self.temp_mp3)
            self.parent.after(0, lambda: self.play_via_mci(self.temp_mp3))
            
        except Exception as e:
            err_msg = str(e)
            self.parent.after(0, lambda: self.speak_error(f"Google TTS 실패:\n{err_msg}"))
            
    def run_google_save(self, text, voice_id, rate, vol, file_path):
        try:
            self._call_google_tts_api(text, voice_id, rate, vol, file_path)
            self.parent.after(0, lambda: self.save_finished(True, file_path))
        except Exception as e:
            err_msg = str(e)
            self.parent.after(0, lambda: self.save_finished(False, f"Google TTS 저장 실패:\n{err_msg}"))

    def _call_typecast_api(self, text, voice_id, rate, vol, out_path):
        api_key = config.get('typecast_api_key', '').strip()
        if not api_key:
            raise ValueError("설정에서 Typecast API Key를 먼저 입력해주세요.")
            
        url = "https://api.typecast.ai/v1/text-to-speech"
        
        # Typecast doesn't natively accept rate and volume in the basic request without complex parameters, 
        # but we can try passing them if they are supported, or just pass text and voice_id
        payload = {
            "text": text,
            "voice_id": voice_id
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={
            'Content-Type': 'application/json',
            'X-API-KEY': api_key
        })
        
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                # Based on standard output.wav in their curl example, it returns raw audio bytes, OR json polling url.
                # Let's check Content-Type
                info = response.info()
                content_type = info.get_content_type()
                
                resp_bytes = response.read()
                
                if content_type == 'application/json':
                    # If it returns json, it's probably polling url or result
                    data = json.loads(resp_bytes.decode('utf-8'))
                    raise ValueError(f"Typecast 비동기 API 방식은 아직 지원되지 않습니다. 응답: {data}")
                else:
                    # Raw audio data
                    with open(out_path, 'wb') as f:
                        f.write(resp_bytes)
                        
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8')
            raise Exception(f"HTTP {e.code}: {err_body}")

    def run_typecast_speak(self, text, voice_id, rate, vol):
        try:
            if os.path.exists(self.temp_mp3):
                try: os.remove(self.temp_mp3)
                except Exception: pass
                
            self._call_typecast_api(text, voice_id, rate, vol, self.temp_mp3)
            self.parent.after(0, lambda: self.play_via_mci(self.temp_mp3))
            
        except Exception as e:
            err_msg = str(e)
            self.parent.after(0, lambda: self.speak_error(f"Typecast 실패:\n{err_msg}"))
            
    def run_typecast_save(self, text, voice_id, rate, vol, file_path):
        try:
            self._call_typecast_api(text, voice_id, rate, vol, file_path)
            self.parent.after(0, lambda: self.save_finished(True, file_path))
        except Exception as e:
            err_msg = str(e)
            self.parent.after(0, lambda: self.save_finished(False, f"Typecast 저장 실패:\n{err_msg}"))

    def save_finished(self, success, result):
        self.speak_btn.config(state="normal")
        self.save_btn.config(state="normal")
        self.status_lbl.config(text="준비됨.", foreground="gray")
        
        if success:
            messagebox.showinfo("성공", f"오디오 파일이 저장되었습니다:\n{os.path.basename(result)}")
        else:
            messagebox.showerror("오류", f"오디오 파일 저장 실패:\n{result}")
