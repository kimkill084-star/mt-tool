import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageEnhance
import threading
import os

class ImageTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        # State variables
        self.original_image = None  # Original loaded image
        self.processed_image = None # Image with edits applied (crop, rembg, upscale)
        self.preview_image = None   # Scaled image for display
        self.photo_image = None     # ImageTk object for canvas
        
        # Image coordinates mapping
        self.scale_x = 1.0
        self.scale_y = 1.0
        
        # Crop variables
        self.crop_start_x = None
        self.crop_start_y = None
        self.crop_rect_id = None
        self.is_cropping = False
        
        # Adjustment variables (temporary settings for sliders)
        self.bright_val = tk.DoubleVar(value=1.0)
        self.contrast_val = tk.DoubleVar(value=1.0)
        self.sat_val = tk.DoubleVar(value=1.0)
        self.sharp_val = tk.DoubleVar(value=1.0)
        
        # Background removal cache and map
        self.model_map = {
            "일반 (u2net)": "u2net",
            "경량 일반 (u2netp)": "u2netp",
            "인물용 (u2net_human)": "u2net_human_seg",
            "의류용 (u2net_cloth)": "u2net_cloth_seg",
            "일반 고화질 (isnet)": "isnet-general-use",
            "애니메이션 (isnet-anime)": "isnet-anime",
            "실루엣 (silueta)": "silueta"
        }
        self.rembg_sessions = {}
        
        self.create_widgets()

    def create_widgets(self):
        # 3-column layout: Left Controls, Middle Preview Canvas, Right Adjustments
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        
        # --- Left Panel (Controls) ---
        left_panel = ttk.LabelFrame(self, text="파일 및 작업", padding=10)
        left_panel.grid(row=0, column=0, sticky="nswe", padx=5, pady=5)
        
        ttk.Button(left_panel, text="이미지 불러오기", command=self.load_image).pack(fill="x", pady=5)
        ttk.Button(left_panel, text="이미지 저장하기", command=self.save_image).pack(fill="x", pady=5)
        
        ttk.Separator(left_panel, orient="horizontal").pack(fill="x", pady=10)
        
        # Background Removal Options Frame
        bg_frame = ttk.LabelFrame(left_panel, text="배경 제거", padding=8)
        bg_frame.pack(fill="x", pady=5)
        
        # Model Selection
        ttk.Label(bg_frame, text="세그멘테이션 모델:").pack(anchor="w", pady=(0, 2))
        self.bg_model_var = tk.StringVar(value="일반 (u2net)")
        self.bg_model_combo = ttk.Combobox(bg_frame, textvariable=self.bg_model_var, state="readonly")
        self.bg_model_combo["values"] = list(self.model_map.keys())
        self.bg_model_combo.pack(fill="x", pady=(0, 5))
        
        # Options variables
        self.alpha_matting_var = tk.BooleanVar(value=False)
        self.only_mask_var = tk.BooleanVar(value=False)
        self.post_process_mask_var = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(bg_frame, text="경계 세분화 (Matting)", variable=self.alpha_matting_var, command=self.toggle_alpha_ui).pack(anchor="w", pady=2)
        
        # Alpha parameter frame (grid layout)
        self.alpha_ui_frame = ttk.Frame(bg_frame)
        self.fg_threshold_var = tk.IntVar(value=240)
        self.bg_threshold_var = tk.IntVar(value=10)
        self.erode_size_var = tk.IntVar(value=10)
        
        ttk.Label(self.alpha_ui_frame, text="전경 임계:").grid(row=0, column=0, sticky="w", pady=1)
        self.fg_scale = ttk.Scale(self.alpha_ui_frame, from_=0, to=255, variable=self.fg_threshold_var, orient="horizontal")
        self.fg_scale.grid(row=0, column=1, sticky="we", pady=1, padx=2)
        
        ttk.Label(self.alpha_ui_frame, text="배경 임계:").grid(row=1, column=0, sticky="w", pady=1)
        self.bg_scale = ttk.Scale(self.alpha_ui_frame, from_=0, to=255, variable=self.bg_threshold_var, orient="horizontal")
        self.bg_scale.grid(row=1, column=1, sticky="we", pady=1, padx=2)
        
        ttk.Label(self.alpha_ui_frame, text="브러시 크기:").grid(row=2, column=0, sticky="w", pady=1)
        self.erode_scale = ttk.Scale(self.alpha_ui_frame, from_=1, to=50, variable=self.erode_size_var, orient="horizontal")
        self.erode_scale.grid(row=2, column=1, sticky="we", pady=1, padx=2)
        
        # Pack other options
        ttk.Checkbutton(bg_frame, text="마스크 채널만 추출", variable=self.only_mask_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(bg_frame, text="마스크 후처리 실행", variable=self.post_process_mask_var).pack(anchor="w", pady=2)
        
        # Action button
        self.bg_btn = ttk.Button(bg_frame, text="배경 제거 실행", command=self.start_bg_removal)
        self.bg_btn.pack(fill="x", pady=(5, 0))
        
        ttk.Separator(left_panel, orient="horizontal").pack(fill="x", pady=10)
        
        # Crop controls
        self.crop_btn = ttk.Button(left_panel, text="자르기 시작", command=self.toggle_crop)
        self.crop_btn.pack(fill="x", pady=5)
        self.apply_crop_btn = ttk.Button(left_panel, text="자르기 적용", command=self.apply_crop, state="disabled")
        self.apply_crop_btn.pack(fill="x", pady=5)
        
        # Status Label
        self.status_lbl = ttk.Label(left_panel, text="이미지를 불러와 주세요.", wraplength=150, foreground="gray")
        self.status_lbl.pack(fill="x", side="bottom", pady=10)
        
        # --- Middle Panel (Preview Canvas) ---
        mid_panel = ttk.Frame(self, padding=5)
        mid_panel.grid(row=0, column=1, sticky="nswe", padx=5, pady=5)
        mid_panel.columnconfigure(0, weight=1)
        mid_panel.rowconfigure(0, weight=1)
        
        self.canvas = tk.Canvas(mid_panel, bg="#2d2d2d", highlightthickness=1, highlightbackground="#3c3c3c")
        self.canvas.grid(row=0, column=0, sticky="nswe")
        
        # Scrollbars for canvas (if image is large, though we fit-to-screen by default)
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        
        # Bind crop events
        self.canvas.bind("<ButtonPress-1>", self.on_crop_start)
        self.canvas.bind("<B1-Motion>", self.on_crop_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_crop_end)
        
        # --- Right Panel (Adjustments / 보정) ---
        right_panel = ttk.LabelFrame(self, text="이미지 보정", padding=10)
        right_panel.grid(row=0, column=2, sticky="nswe", padx=5, pady=5)
        
        # Brightness Slider
        ttk.Label(right_panel, text="밝기 (Brightness)").pack(anchor="w", pady=(5,0))
        self.bright_scale = ttk.Scale(right_panel, from_=0.0, to=3.0, variable=self.bright_val, command=self.on_slider_change)
        self.bright_scale.pack(fill="x", pady=5)
        self.bright_lbl = ttk.Label(right_panel, text="1.00")
        self.bright_lbl.pack(anchor="e")
        
        # Contrast Slider
        ttk.Label(right_panel, text="대비 (Contrast)").pack(anchor="w", pady=(10,0))
        self.contrast_scale = ttk.Scale(right_panel, from_=0.0, to=3.0, variable=self.contrast_val, command=self.on_slider_change)
        self.contrast_scale.pack(fill="x", pady=5)
        self.contrast_lbl = ttk.Label(right_panel, text="1.00")
        self.contrast_lbl.pack(anchor="e")
        
        # Saturation Slider
        ttk.Label(right_panel, text="채도 (Saturation)").pack(anchor="w", pady=(10,0))
        self.sat_scale = ttk.Scale(right_panel, from_=0.0, to=3.0, variable=self.sat_val, command=self.on_slider_change)
        self.sat_scale.pack(fill="x", pady=5)
        self.sat_lbl = ttk.Label(right_panel, text="1.00")
        self.sat_lbl.pack(anchor="e")
        
        # Sharpness Slider
        ttk.Label(right_panel, text="선명도 (Sharpness)").pack(anchor="w", pady=(10,0))
        self.sharp_scale = ttk.Scale(right_panel, from_=0.0, to=3.0, variable=self.sharp_val, command=self.on_slider_change)
        self.sharp_scale.pack(fill="x", pady=5)
        self.sharp_lbl = ttk.Label(right_panel, text="1.00")
        self.sharp_lbl.pack(anchor="e")
        
        ttk.Separator(right_panel, orient="horizontal").pack(fill="x", pady=15)
        
        ttk.Button(right_panel, text="보정 적용", command=self.apply_adjustments).pack(fill="x", pady=5)
        ttk.Button(right_panel, text="초기화 (Reset)", command=self.reset_adjustments).pack(fill="x", pady=5)
        
        ttk.Separator(right_panel, orient="horizontal").pack(fill="x", pady=15)
        
        # Upscaling Frame inside Right Panel
        upscale_frame = ttk.LabelFrame(right_panel, text="크기 조절 및 업스케일", padding=8)
        upscale_frame.pack(fill="x", pady=5)
        
        ttk.Label(upscale_frame, text="란초스(Lanczos) 필터 확대:").pack(anchor="w", pady=(0, 2))
        ttk.Button(upscale_frame, text="2배 확대 (2x)", command=lambda: self.upscale_image(2)).pack(fill="x", pady=2)
        ttk.Button(upscale_frame, text="4배 확대 (4x)", command=lambda: self.upscale_image(4)).pack(fill="x", pady=2)

    # --- Loading & Display ---
    def load_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.webp *.tiff")]
        )
        if not file_path:
            return
            
        try:
            # Load original image
            img = Image.open(file_path)
            # Standardize color profile/mode
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            
            self.original_image = img
            self.processed_image = img.copy()
            
            self.reset_sliders_ui()
            self.show_image()
            self.set_status(f"이미지 로드 완료: {os.path.basename(file_path)} ({img.width}x{img.height})")
        except Exception as e:
            messagebox.showerror("오류", f"이미지를 불러오는 데 실패했습니다: {e}")

    def show_image(self):
        if self.processed_image is None:
            return
            
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # If canvas is not yet rendered, use defaults
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 500
            canvas_height = 500
            
        # Rescale working image to preview size
        img_width, img_height = self.processed_image.size
        
        ratio = min(canvas_width / img_width, canvas_height / img_height)
        new_width = max(1, int(img_width * ratio))
        new_height = max(1, int(img_height * ratio))
        
        # Apply temporary adjustment filters to preview if sliders are changed
        preview_img = self.processed_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        preview_img = self.enhance_pil_image(preview_img, 
                                             self.bright_val.get(),
                                             self.contrast_val.get(),
                                             self.sat_val.get(),
                                             self.sharp_val.get())
        
        self.preview_image = preview_img
        
        # Keep track of scaling ratios to convert canvas coords back to actual pixels
        self.scale_x = img_width / new_width
        self.scale_y = img_height / new_height
        
        self.photo_image = ImageTk.PhotoImage(self.preview_image)
        
        # Render on Canvas centered
        self.canvas.delete("all")
        # Center coordinates
        cx = canvas_width / 2
        cy = canvas_height / 2
        self.canvas.create_image(cx, cy, image=self.photo_image, anchor="center")
        
        # Store bounding coordinates of image in canvas space for crop constraints
        self.img_x_offset = cx - (new_width / 2)
        self.img_y_offset = cy - (new_height / 2)
        self.preview_w = new_width
        self.preview_h = new_height

    def on_canvas_resize(self, event):
        if self.processed_image:
            self.show_image()

    def set_status(self, text, color="#d4d4d4"):
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

    # --- Cropping Logic ---
    def toggle_crop(self):
        if self.processed_image is None:
            messagebox.showwarning("경고", "먼저 이미지를 불러오세요.")
            return
            
        if not self.is_cropping:
            self.is_cropping = True
            self.crop_btn.config(text="자르기 취소")
            self.set_status("마우스 드래그로 자를 영역을 선택하세요.")
            self.canvas.config(cursor="cross")
        else:
            self.is_cropping = False
            self.crop_btn.config(text="자르기 시작")
            self.apply_crop_btn.config(state="disabled")
            self.canvas.config(cursor="")
            if self.crop_rect_id:
                self.canvas.delete(self.crop_rect_id)
                self.crop_rect_id = None
            self.set_status("자르기 취소됨.")

    def on_crop_start(self, event):
        if not self.is_cropping:
            return
        
        # Check if click is inside the preview image bounds
        if (self.img_x_offset <= event.x <= self.img_x_offset + self.preview_w and
            self.img_y_offset <= event.y <= self.img_y_offset + self.preview_h):
            self.crop_start_x = event.x
            self.crop_start_y = event.y
            
            if self.crop_rect_id:
                self.canvas.delete(self.crop_rect_id)
                
            self.crop_rect_id = self.canvas.create_rectangle(
                self.crop_start_x, self.crop_start_y, self.crop_start_x, self.crop_start_y,
                outline="red", width=2, dash=(4, 4)
            )

    def on_crop_drag(self, event):
        if not self.is_cropping or self.crop_start_x is None:
            return
            
        # Constrain drag within image preview boundaries
        x = max(self.img_x_offset, min(event.x, self.img_x_offset + self.preview_w))
        y = max(self.img_y_offset, min(event.y, self.img_y_offset + self.preview_h))
        
        self.canvas.coords(self.crop_rect_id, self.crop_start_x, self.crop_start_y, x, y)

    def on_crop_end(self, event):
        if not self.is_cropping or self.crop_start_x is None:
            return
            
        self.apply_crop_btn.config(state="normal")

    def apply_crop(self):
        if not self.crop_rect_id:
            return
            
        coords = self.canvas.coords(self.crop_rect_id)
        # Convert coords to relative image coordinates
        x1 = min(coords[0], coords[2]) - self.img_x_offset
        y1 = min(coords[1], coords[3]) - self.img_y_offset
        x2 = max(coords[0], coords[2]) - self.img_x_offset
        y2 = max(coords[1], coords[3]) - self.img_y_offset
        
        # Safety checks
        if x2 - x1 < 5 or y2 - y1 < 5:
            messagebox.showwarning("경고", "영역이 너무 작습니다.")
            return
            
        # Map to original image size coordinates
        real_x1 = int(x1 * self.scale_x)
        real_y1 = int(y1 * self.scale_y)
        real_x2 = int(x2 * self.scale_x)
        real_y2 = int(y2 * self.scale_y)
        
        # Apply crop
        try:
            # First, commit current adjustments to original size processed image,
            # then crop it, to prevent losing adjustments. Or just crop and keep adjustments.
            # We crop the processed image.
            cropped_img = self.processed_image.crop((real_x1, real_y1, real_x2, real_y2))
            self.processed_image = cropped_img
            
            # Disable cropping UI
            self.is_cropping = False
            self.crop_btn.config(text="자르기 시작")
            self.apply_crop_btn.config(state="disabled")
            self.canvas.config(cursor="")
            self.crop_rect_id = None
            
            self.show_image()
            self.set_status(f"이미지 자르기 완료 ({self.processed_image.width}x{self.processed_image.height})")
        except Exception as e:
            messagebox.showerror("오류", f"이미지 자르기 중 오류 발생: {e}")

    # --- Adjustments/Enhancements (보정) ---
    def on_slider_change(self, *args):
        # Update text labels
        self.bright_lbl.config(text=f"{self.bright_val.get():.2f}")
        self.contrast_lbl.config(text=f"{self.contrast_val.get():.2f}")
        self.sat_lbl.config(text=f"{self.sat_val.get():.2f}")
        self.sharp_lbl.config(text=f"{self.sharp_val.get():.2f}")
        
        # Show real-time preview (cheap resize display update)
        if self.processed_image:
            self.show_image()

    def enhance_pil_image(self, img, bright, contrast, sat, sharp):
        if bright != 1.0:
            img = ImageEnhance.Brightness(img).enhance(bright)
        if contrast != 1.0:
            img = ImageEnhance.Contrast(img).enhance(contrast)
        if sat != 1.0:
            img = ImageEnhance.Color(img).enhance(sat)
        if sharp != 1.0:
            img = ImageEnhance.Sharpness(img).enhance(sharp)
        return img

    def apply_adjustments(self):
        if self.processed_image is None:
            return
        
        # Commit slider changes to full-res working image
        self.processed_image = self.enhance_pil_image(self.processed_image,
                                                     self.bright_val.get(),
                                                     self.contrast_val.get(),
                                                     self.sat_val.get(),
                                                     self.sharp_val.get())
        # Reset sliders to 1.0
        self.reset_sliders_ui()
        self.show_image()
        self.set_status("보정이 이미지에 적용되었습니다.")

    def reset_adjustments(self):
        if self.processed_image is None:
            return
        self.reset_sliders_ui()
        self.show_image()
        self.set_status("보정이 초기화되었습니다.")

    def reset_sliders_ui(self):
        self.bright_val.set(1.0)
        self.contrast_val.set(1.0)
        self.sat_val.set(1.0)
        self.sharp_val.set(1.0)
        self.bright_lbl.config(text="1.00")
        self.contrast_lbl.config(text="1.00")
        self.sat_lbl.config(text="1.00")
        self.sharp_lbl.config(text="1.00")

    # --- Background Removal ---
    def toggle_alpha_ui(self):
        if self.alpha_matting_var.get():
            self.alpha_ui_frame.pack(fill="x", pady=2, padx=10)
        else:
            self.alpha_ui_frame.pack_forget()

    def start_bg_removal(self):
        if self.processed_image is None:
            messagebox.showwarning("경고", "먼저 이미지를 불러오세요.")
            return
            
        self.bg_btn.config(state="disabled")
        self.set_status("배경 제거 진행 중...", "blue")
        
        # Run in thread
        threading.Thread(target=self.run_bg_removal, daemon=True).start()

    def run_bg_removal(self):
        try:
            from rembg import remove, new_session
            import os
            
            # 1. Get selected model session
            selected_display_name = self.bg_model_var.get()
            model_key = self.model_map.get(selected_display_name, "u2net")
            
            # Check if model file already exists in user's home folder
            u2net_home = os.environ.get("U2NET_HOME", os.path.expanduser(os.path.join("~", ".u2net")))
            model_path = os.path.join(u2net_home, f"{model_key}.onnx")
            model_exists = os.path.exists(model_path)
            
            # Get session from cache
            if model_key not in self.rembg_sessions:
                if not model_exists:
                    self.parent.after(0, lambda: self.set_status(f"배경 제거 모델({model_key}) 최초 다운로드 중 (인터넷에서 다운 중, 약 30초~1분 소요)...", "orange"))
                else:
                    self.parent.after(0, lambda: self.set_status(f"배경 제거 모델({model_key}) 로딩 중...", "blue"))
                
                self.rembg_sessions[model_key] = new_session(model_key)
                
            session = self.rembg_sessions[model_key]
            
            self.parent.after(0, lambda: self.set_status("이미지 보정 적용 및 배경 제거 분석 중...", "blue"))
            
            # Apply any current slider values to the image before background removal
            img_to_process = self.enhance_pil_image(self.processed_image,
                                                     self.bright_val.get(),
                                                     self.contrast_val.get(),
                                                     self.sat_val.get(),
                                                     self.sharp_val.get())
            
            # Parameters
            alpha_matting = self.alpha_matting_var.get()
            fg_threshold = self.fg_threshold_var.get()
            bg_threshold = self.bg_threshold_var.get()
            erode_size = self.erode_size_var.get()
            only_mask = self.only_mask_var.get()
            post_process_mask = self.post_process_mask_var.get()
            
            output_img = remove(
                img_to_process,
                session=session,
                alpha_matting=alpha_matting,
                alpha_matting_foreground_threshold=fg_threshold,
                alpha_matting_background_threshold=bg_threshold,
                alpha_matting_erode_size=erode_size,
                only_mask=only_mask,
                post_process_mask=post_process_mask
            )
            
            # UI update in safe thread mainloop
            self.parent.after(0, lambda: self.finish_bg_removal(output_img))
        except Exception as e:
            err_msg = str(e)
            self.parent.after(0, lambda: self.finish_bg_removal_error(err_msg))

    def finish_bg_removal(self, output_img):
        self.processed_image = output_img
        self.reset_sliders_ui() # Sliders are baked into output_img
        self.bg_btn.config(state="normal")
        self.show_image()
        self.set_status("배경 제거가 완료되었습니다.", "green")

    def finish_bg_removal_error(self, err):
        self.bg_btn.config(state="normal")
        self.set_status("배경 제거 실패.", "red")
        messagebox.showerror("오류", f"배경 제거 중 오류가 발생했습니다.\n상세오류: {err}")

    # --- Upscaling ---
    def upscale_image(self, multiplier):
        if self.processed_image is None:
            messagebox.showwarning("경고", "먼저 이미지를 불러오세요.")
            return
            
        w, h = self.processed_image.size
        new_w, new_h = w * multiplier, h * multiplier
        
        try:
            self.set_status(f"이미지 업스케일링 중 ({multiplier}x)...", "blue")
            # Apply adjustments before upscaling to keep speed high
            self.processed_image = self.enhance_pil_image(self.processed_image,
                                                         self.bright_val.get(),
                                                         self.contrast_val.get(),
                                                         self.sat_val.get(),
                                                         self.sharp_val.get())
            self.reset_sliders_ui()
            
            upscaled = self.processed_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.processed_image = upscaled
            self.show_image()
            self.set_status(f"업스케일링 완료: {new_w}x{new_h}", "green")
        except Exception as e:
            self.set_status("업스케일링 실패", "red")
            messagebox.showerror("오류", f"업스케일링 중 오류 발생: {e}")

    # --- Save Image ---
    def save_image(self):
        if self.processed_image is None:
            messagebox.showwarning("경고", "저장할 이미지가 없습니다.")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
        )
        if not file_path:
            return
            
        try:
            # Commit adjustments
            final_img = self.enhance_pil_image(self.processed_image,
                                               self.bright_val.get(),
                                               self.contrast_val.get(),
                                               self.sat_val.get(),
                                               self.sharp_val.get())
            
            # Save
            # If saving as JPEG, and it has an alpha channel (rembg), convert to RGB
            if file_path.lower().endswith(('.jpg', '.jpeg')) and final_img.mode == "RGBA":
                # Create white background
                bg = Image.new("RGB", final_img.size, (255, 255, 255))
                bg.paste(final_img, mask=final_img.split()[3]) # 3 is alpha
                final_img = bg
                
            final_img.save(file_path)
            self.set_status(f"이미지 저장 완료: {os.path.basename(file_path)}")
            messagebox.showinfo("성공", "이미지가 성공적으로 저장되었습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"이미지 저장에 실패했습니다: {e}")
