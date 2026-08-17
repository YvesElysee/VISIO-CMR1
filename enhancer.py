import cv2
import numpy as np
import os
import time

class VideoEnhancer:
    def __init__(self, models_dir="models"):
        self.models_dir = models_dir
        self.networks = {}
        self.has_models = False
        self.load_models()
        
    def load_models(self):
        """Loads pre-trained super resolution models using OpenCV DNN."""
        espcn_path = os.path.join(self.models_dir, "ESPCN_x4.pb")
        fsrcnn_path = os.path.join(self.models_dir, "FSRCNN_x2.pb")
        
        if os.path.exists(espcn_path):
            try:
                net = cv2.dnn.readNet(espcn_path)
                self.networks["espcn"] = {"net": net, "scale": 4, "name": "espcn"}
                print("[OK] Modèle ESPCN_x4.pb chargé avec succès.")
            except Exception as e:
                print(f"[ERREUR] Impossible de charger ESPCN : {e}")
                
        if os.path.exists(fsrcnn_path):
            try:
                net = cv2.dnn.readNet(fsrcnn_path)
                self.networks["fsrcnn"] = {"net": net, "scale": 2, "name": "fsrcnn"}
                print("[OK] Modèle FSRCNN_x2.pb chargé avec succès.")
            except Exception as e:
                print(f"[ERREUR] Impossible de charger FSRCNN : {e}")
                
        self.has_models = len(self.networks) > 0

    def run_dnn_superres(self, frame, model_key):
        """Runs manual super-resolution inference on the Y-channel."""
        if model_key not in self.networks:
            return None
            
        model_info = self.networks[model_key]
        net = model_info["net"]
        
        h, w = frame.shape[:2]
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)
        
        blob = cv2.dnn.blobFromImage(y, 1.0 / 255.0, (w, h), (0,), swapRB=False, crop=False)
        net.setInput(blob)
        t0 = time.time()
        out = net.forward()
        inference_time = (time.time() - t0) * 1000  # ms
        
        out_y = out[0, 0]
        y_upscaled = (out_y * 255.0).clip(0, 255).astype(np.uint8)
        
        new_h, new_w = y_upscaled.shape[:2]
        cr_upscaled = cv2.resize(cr, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        cb_upscaled = cv2.resize(cb, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        ycrcb_upscaled = cv2.merge([y_upscaled, cr_upscaled, cb_upscaled])
        enhanced_bgr = cv2.cvtColor(ycrcb_upscaled, cv2.COLOR_YCrCb2BGR)
        
        return enhanced_bgr, inference_time

    def enhance_frame(self, frame, settings):
        """Applies adaptive filtering, contrast boost, kernel sharpening, and upscaling."""
        h, w = frame.shape[:2]
        
        metrics = {
            "denoise_time": 0.0,
            "contrast_time": 0.0,
            "sharpness_time": 0.0,
            "upscale_time": 0.0,
            "total_time": 0.0,
            "used_method": "Lanczos4 (Traditionnel HD)"
        }
        
        t_start = time.time()
        enhanced = frame.copy()
        
        # 1. Edge-Preserving Denoising (Fast & Sharp)
        if settings.get("enable_denoise", False):
            t0 = time.time()
            strength = settings.get("denoise_strength", 5)
            d = 3
            sigma = max(10, strength * 4)
            enhanced = cv2.bilateralFilter(enhanced, d, sigma, sigma)
            metrics["denoise_time"] = (time.time() - t0) * 1000
            
        # 2. Adaptive Contrast Boost (CLAHE in LAB color space)
        if settings.get("enable_contrast", False):
            t0 = time.time()
            clip_limit = max(1.5, settings.get("contrast_limit", 2.0) * 1.2)
            lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l)
            lab_enhanced = cv2.merge([l_enhanced, a, b])
            enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
            metrics["contrast_time"] = (time.time() - t0) * 1000
            
        # 3. High-Definition Detail Sharpening (Unsharp Mask + Laplacian Kernel)
        if settings.get("enable_sharpness", False):
            t0 = time.time()
            strength = settings.get("sharpness_strength", 0.8)
            # Unsharp mask
            blurred = cv2.GaussianBlur(enhanced, (0, 0), 3)
            sharpened_um = cv2.addWeighted(enhanced, 1.0 + strength * 1.5, blurred, -strength * 1.5, 0)
            
            # Sharpness matrix filter for fine text/edges
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
            sharpened_kernel = cv2.filter2D(enhanced, -1, kernel)
            
            enhanced = cv2.addWeighted(sharpened_um, 0.7, sharpened_kernel, 0.3, 0)
            metrics["sharpness_time"] = (time.time() - t0) * 1000
            
        # 4. High-Quality Upscaling
        target_w, target_h = 960, 540
        
        if settings.get("enable_upscale", False):
            method = settings.get("upscale_method", "traditional")
            model_key = settings.get("selected_model", "espcn")
            
            if method == "ai" and self.has_models and model_key in self.networks:
                t0 = time.time()
                try:
                    ai_result = self.run_dnn_superres(enhanced, model_key)
                    if ai_result is not None:
                        ai_frame, inf_time = ai_result
                        enhanced = cv2.resize(ai_frame, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
                        metrics["used_method"] = f"IA - {model_key.upper()} (x{self.networks[model_key]['scale']})"
                        metrics["upscale_time"] = inf_time
                    else:
                        enhanced = cv2.resize(enhanced, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
                except Exception:
                    enhanced = cv2.resize(enhanced, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
                    metrics["upscale_time"] = (time.time() - t0) * 1000
            else:
                t0 = time.time()
                enhanced = cv2.resize(enhanced, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
                metrics["upscale_time"] = (time.time() - t0) * 1000
        else:
            enhanced = cv2.resize(enhanced, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
            
        metrics["total_time"] = (time.time() - t_start) * 1000
        
        # 5. Build Side-by-Side Comparison
        original_resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
        
        # Draw HUD Banners on Top of Original and Enhanced sides
        # Left Side HUD (Original)
        cv2.rectangle(original_resized, (0, 0), (target_w, 40), (15, 23, 42), -1)
        cv2.putText(original_resized, "FLUX ORIGINAL BRUT (Basse Res)", (20, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 116, 139), 2)
        
        # Right Side HUD (Enhanced)
        cv2.rectangle(enhanced, (0, 0), (target_w, 40), (6, 78, 59), -1)
        cv2.putText(enhanced, f"FLUX AMELIORE IA & HD [{metrics['used_method']}]", (20, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (52, 211, 153), 2)
        
        # Combine horizontally
        comparison_frame = np.hstack([original_resized, enhanced])
        
        # Draw central divider line
        cv2.line(comparison_frame, (target_w, 0), (target_w, target_h), (16, 185, 129), 3)
        
        return comparison_frame, metrics
