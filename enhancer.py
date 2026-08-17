import cv2
import numpy as np
import os
import time

class VideoEnhancer:
    def __init__(self, models_dir="models"):
        self.models_dir = models_dir
        self.networks = {}
        self.has_models = False
        
        # Load DNN models if available
        self.load_models()
        
    def load_models(self):
        """Loads pre-trained super resolution models using OpenCV DNN."""
        espcn_path = os.path.join(self.models_dir, "ESPCN_x4.pb")
        fsrcnn_path = os.path.join(self.models_dir, "FSRCNN_x2.pb")
        
        # Load ESPCN
        if os.path.exists(espcn_path):
            try:
                # Read TF model
                net = cv2.dnn.readNet(espcn_path)
                self.networks["espcn"] = {
                    "net": net,
                    "scale": 4,
                    "name": "espcn"
                }
                print("[OK] Modèle ESPCN_x4.pb chargé avec succès.")
            except Exception as e:
                print(f"[ERREUR] Impossible de charger le modèle ESPCN : {e}")
                
        # Load FSRCNN
        if os.path.exists(fsrcnn_path):
            try:
                net = cv2.dnn.readNet(fsrcnn_path)
                self.networks["fsrcnn"] = {
                    "net": net,
                    "scale": 2,
                    "name": "fsrcnn"
                }
                print("[OK] Modèle FSRCNN_x2.pb chargé avec succès.")
            except Exception as e:
                print(f"[ERREUR] Impossible de charger le modèle FSRCNN : {e}")
                
        self.has_models = len(self.networks) > 0
        if not self.has_models:
            print("[INFO] Aucun modèle IA chargé. Le système fonctionnera en mode d'amélioration traditionnelle (Lanczos4).")

    def run_dnn_superres(self, frame, model_key):
        """Runs manual super-resolution inference on the Y-channel of the image."""
        if model_key not in self.networks:
            return None
            
        model_info = self.networks[model_key]
        net = model_info["net"]
        scale = model_info["scale"]
        
        h, w = frame.shape[:2]
        
        # 1. Convert BGR to YCrCb
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)
        
        # 2. Prepare the Y channel (Luminance) as blob
        # ESPCN/FSRCNN expect normalized [0, 1] inputs of shape 1x1xHxW
        blob = cv2.dnn.blobFromImage(y, 1.0 / 255.0, (w, h), (0,), swapRB=False, crop=False)
        
        # 3. Forward pass through neural network
        net.setInput(blob)
        t0 = time.time()
        out = net.forward()
        inference_time = (time.time() - t0) * 1000  # ms
        
        # 4. Post-process output Y channel
        # Out shape is 1 x 1 x (H*scale) x (W*scale)
        out_y = out[0, 0]
        y_upscaled = (out_y * 255.0).clip(0, 255).astype(np.uint8)
        
        # 5. Resize Cr and Cb channels using traditional Bicubic interpolation
        new_h, new_w = y_upscaled.shape[:2]
        cr_upscaled = cv2.resize(cr, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        cb_upscaled = cv2.resize(cb, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        # 6. Merge channels and convert back to BGR
        ycrcb_upscaled = cv2.merge([y_upscaled, cr_upscaled, cb_upscaled])
        enhanced_bgr = cv2.cvtColor(ycrcb_upscaled, cv2.COLOR_YCrCb2BGR)
        
        return enhanced_bgr, inference_time

    def enhance_frame(self, frame, settings):
        """Applies the selected filters and upscaling techniques on a frame."""
        h, w = frame.shape[:2]
        
        # Track processing times
        metrics = {
            "denoise_time": 0.0,
            "contrast_time": 0.0,
            "sharpness_time": 0.0,
            "upscale_time": 0.0,
            "total_time": 0.0,
            "used_method": "Lanczos4 (Traditionnel)"
        }
        
        t_start = time.time()
        enhanced = frame.copy()
        
        # 1. Bilateral Denoising (Edge-preserving noise reduction)
        if settings.get("enable_denoise", False):
            t0 = time.time()
            strength = settings.get("denoise_strength", 5)
            # Bilateral filter needs odd numbers or standard parameters
            d = 5
            sigma_color = strength * 5
            sigma_space = strength * 5
            enhanced = cv2.bilateralFilter(enhanced, d, sigma_color, sigma_space)
            metrics["denoise_time"] = (time.time() - t0) * 1000 # ms
            
        # 2. Contrast Enhancement (CLAHE in LAB color space)
        if settings.get("enable_contrast", False):
            t0 = time.time()
            clip_limit = settings.get("contrast_limit", 2.0)
            lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l)
            lab_enhanced = cv2.merge([l_enhanced, a, b])
            enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
            metrics["contrast_time"] = (time.time() - t0) * 1000
            
        # 3. Detail Sharpening (Unsharp Masking)
        if settings.get("enable_sharpness", False):
            t0 = time.time()
            strength = settings.get("sharpness_strength", 0.8)
            blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)
            # sharpened = original + strength * (original - blurred)
            enhanced = cv2.addWeighted(enhanced, 1.0 + strength, blurred, -strength, 0)
            metrics["sharpness_time"] = (time.time() - t0) * 1000
            
        # 4. Upscaling / Resolution Enhancement
        target_w, target_h = 960, 540 # Standard display resolution for side-by-side comparison
        
        if settings.get("enable_upscale", False):
            method = settings.get("upscale_method", "traditional")
            model_key = settings.get("selected_model", "espcn")
            
            if method == "ai" and self.has_models and model_key in self.networks:
                t0 = time.time()
                try:
                    # Run AI super resolution
                    ai_result = self.run_dnn_superres(enhanced, model_key)
                    if ai_result is not None:
                        ai_frame, inf_time = ai_result
                        # Resize AI output to target 960x540 display resolution if scale doesn't match perfectly
                        if ai_frame.shape[1] != target_w or ai_frame.shape[0] != target_h:
                            enhanced = cv2.resize(ai_frame, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
                        else:
                            enhanced = ai_frame
                        metrics["used_method"] = f"IA - {model_key.upper()} (x{self.networks[model_key]['scale']})"
                        metrics["upscale_time"] = inf_time
                    else:
                        # Fallback
                        enhanced = cv2.resize(enhanced, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
                except Exception as e:
                    print(f"[ERREUR] Échec inference IA : {e}, fallback Lanczos4")
                    enhanced = cv2.resize(enhanced, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
                    metrics["upscale_time"] = (time.time() - t0) * 1000
            else:
                # Traditional high-quality upscaling
                t0 = time.time()
                enhanced = cv2.resize(enhanced, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
                metrics["upscale_time"] = (time.time() - t0) * 1000
        else:
            # If upscaling disabled, fit to target size using bilinear (standard representation)
            enhanced = cv2.resize(enhanced, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
            
        metrics["total_time"] = (time.time() - t_start) * 1000
        
        # 5. Create Comparison Output
        # Resize original frame to the same display dimensions using simple bilinear (standard low-res stretch)
        original_resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
        
        # Combine side-by-side
        # Double-wide width is 960*2 = 1920, height is 540
        comparison_frame = np.hstack([original_resized, enhanced])
        
        return comparison_frame, metrics

if __name__ == "__main__":
    # Test enhancer
    enhancer = VideoEnhancer()
    test_img = np.random.randint(0, 255, (360, 640, 3), dtype=np.uint8)
    settings = {
        "enable_denoise": True,
        "denoise_strength": 5,
        "enable_contrast": True,
        "contrast_limit": 2.0,
        "enable_sharpness": True,
        "sharpness_strength": 0.8,
        "enable_upscale": True,
        "upscale_method": "traditional"
    }
    
    print("Test du traitement de l'image...")
    comp, metrics = enhancer.enhance_frame(test_img, settings)
    print("Métriques de performance :", metrics)
    print(f"Dimensions de sortie : {comp.shape[1]}x{comp.shape[0]}")
    print("Traitement OK.")
