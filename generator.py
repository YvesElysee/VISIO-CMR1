import cv2
import numpy as np
import time
import math

class CameroonianTVGenerator:
    def __init__(self, width=640, height=360):
        self.width = width
        self.height = height
        self.fps = 25
        self.start_time = time.time()
        
        # News ticker text
        self.ticker_text = "  *** DIRECT YAOUNDE : SOUTENANCE DE LICENCE 3 EN INFORMATIQUE ***  PROJET : AMPLIFICATEUR DE SIGNAL ET OPTIMISATION DE FLUX VIDÉO POUR LES CHAÎNES LOCALES (VISIO-CMR)  ***  AMÉLIORATION DU SIGNAL EN TEMPS RÉEL PAR IA  ***  RÉDUCTION DE LA BANDE PASSANTE DE 50% GRÂCE AUX CODECS H.265/AV1  ***  CRTV, CANAL 2, VISION 4 : ANALYSE DES DEFAUTS DE FLUX... "
        self.ticker_pos = 0
        
    def draw_anchor(self, frame, t):
        """Draws a simple animated news anchor avatar."""
        # Body (torso) - maroon suit
        cv2.ellipse(frame, (self.width // 2, self.height - 30), (70, 90), 0, 0, 360, (50, 20, 120), -1)
        # Shirt - white collar
        pts = np.array([[self.width // 2 - 20, self.height - 80], 
                        [self.width // 2 + 20, self.height - 80], 
                        [self.width // 2, self.height - 50]], np.int32)
        cv2.fillPoly(frame, [pts], (255, 255, 255))
        # Tie - red
        tie_pts = np.array([[self.width // 2 - 5, self.height - 50], 
                            [self.width // 2 + 5, self.height - 50], 
                            [self.width // 2, self.height - 10]], np.int32)
        cv2.fillPoly(frame, [tie_pts], (40, 40, 200))
        
        # Head (oval) - skin tone
        head_y = self.height - 120 + int(math.sin(t * 4) * 2)  # subtle breathing movement
        cv2.ellipse(frame, (self.width // 2, head_y), (40, 50), 0, 0, 360, (110, 160, 210), -1)
        
        # Hair (black)
        cv2.ellipse(frame, (self.width // 2, head_y - 25), (42, 28), 0, 0, 360, (20, 20, 20), -1)
        
        # Eyes - animated blinking
        eye_y = head_y - 10
        blink = math.sin(t * 2) > 0.95
        if blink:
            # Closed eyes (lines)
            cv2.line(frame, (self.width // 2 - 15, eye_y), (self.width // 2 - 5, eye_y), (20, 20, 20), 2)
            cv2.line(frame, (self.width // 2 + 5, eye_y), (self.width // 2 + 15, eye_y), (20, 20, 20), 2)
        else:
            # Open eyes
            cv2.circle(frame, (self.width // 2 - 10, eye_y), 4, (255, 255, 255), -1)
            cv2.circle(frame, (self.width // 2 + 10, eye_y), 4, (255, 255, 255), -1)
            cv2.circle(frame, (self.width // 2 - 10, eye_y), 2, (20, 20, 20), -1)
            cv2.circle(frame, (self.width // 2 + 10, eye_y), 2, (20, 20, 20), -1)
            
        # Mouth - animated speaking
        mouth_y = head_y + 15
        mouth_open = int(abs(math.sin(t * 12)) * 6)  # rapid movement to simulate speaking
        cv2.ellipse(frame, (self.width // 2, mouth_y), (10, mouth_open), 0, 0, 360, (20, 20, 80), -1)
        
    def generate_frame(self, noise_level=25, blur_strength=3, compression_artifacts=True):
        """Generates a low-quality news broadcast frame."""
        t = time.time() - self.start_time
        
        # 1. Base frame - studio background (dark blue/purple gradient)
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        for y in range(self.height):
            # Gradient color
            c = int(20 + 30 * (y / self.height))
            frame[y, :] = (c + 15, c, 10) # BGR
            
        # Add studio grid/lines
        for x in range(0, self.width, 40):
            cv2.line(frame, (x, 0), (x + 20, self.height), (40, 25, 15), 1)
        
        # 2. Draw news anchor
        self.draw_anchor(frame, t)
        
        # 3. TV Channel Overlay (e.g. CRTV / Cameroon News)
        # News Banner at bottom
        cv2.rectangle(frame, (0, self.height - 45), (self.width, self.height), (150, 40, 30), -1)  # Red banner
        cv2.rectangle(frame, (0, self.height - 45), (100, self.height), (0, 180, 220), -1)       # Gold tag "LIVE"
        cv2.putText(frame, "DIRECT", (12, self.height - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 2)
        
        # Scrolling news ticker
        ticker_slice = self.ticker_text[int(self.ticker_pos):] + self.ticker_text[:int(self.ticker_pos)]
        cv2.putText(frame, ticker_slice[:45], (110, self.height - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        # Update ticker position
        self.ticker_pos = (self.ticker_pos + 0.15) % len(self.ticker_text)
        
        # Top Logo (e.g., "CRTV Live" or "L3 INFO TV")
        # Cameroon flag badge in logo
        cv2.rectangle(frame, (self.width - 150, 20), (self.width - 20, 50), (30, 30, 30), -1)
        # Flag stripes: Green, Red, Yellow
        cv2.rectangle(frame, (self.width - 145, 25), (self.width - 130, 45), (30, 100, 30), -1)
        cv2.rectangle(frame, (self.width - 130, 25), (self.width - 115, 45), (30, 30, 180), -1)
        cv2.rectangle(frame, (self.width - 115, 25), (self.width - 100, 45), (30, 180, 180), -1)
        # Little gold star in red stripe
        cv2.circle(frame, (self.width - 123, 35), 2, (30, 180, 180), -1)
        
        cv2.putText(frame, "L3 INFO TV", (self.width - 92, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
        
        # Clock / Time
        local_time = time.strftime("%H:%M:%S", time.localtime())
        cv2.rectangle(frame, (20, 20), (120, 45), (30, 30, 30), -1)
        cv2.putText(frame, local_time, (28, 37), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1, cv2.LINE_AA)
        
        # Signal Indicator (Low Signal simulation)
        cv2.putText(frame, "SIGNAL: FAIBLE", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (50, 50, 220), 1, cv2.LINE_AA)
        cv2.rectangle(frame, (120, 62), (123, 70), (50, 50, 220), -1)
        cv2.rectangle(frame, (125, 65), (128, 70), (100, 100, 100), -1)
        cv2.rectangle(frame, (130, 68), (133, 70), (100, 100, 100), -1)
        
        # 4. DEGRADATION PIPELINE (Simulate local network/camera defects)
        # A. Apply Motion Blur / Camera Defocus
        if blur_strength > 0:
            if blur_strength % 2 == 0:
                blur_strength += 1
            frame = cv2.GaussianBlur(frame, (blur_strength, blur_strength), 0)
            
        # B. Apply Heavy Image Noise (Analog Static / Gaussian Noise)
        if noise_level > 0:
            noise = np.random.normal(0, noise_level, frame.shape).astype(np.float32)
            noisy_frame = frame.astype(np.float32) + noise
            frame = np.clip(noisy_frame, 0, 255).astype(np.uint8)
            
        # C. Apply JPEG Compression Artifacts (blockiness)
        if compression_artifacts:
            # Encode frame with low JPEG quality, then decode it
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 18] # 18% quality for blocky look
            result, encimg = cv2.imencode('.jpg', frame, encode_param)
            if result:
                frame = cv2.imdecode(encimg, 1)
                
        return frame

if __name__ == "__main__":
    # Test generator output
    generator = CameroonianTVGenerator()
    print("Test du générateur de flux...")
    for i in range(10):
        frame = generator.generate_frame()
        print(f"Frame {i} générée avec succès (Taille: {frame.shape[1]}x{frame.shape[0]})")
        time.sleep(0.04)
    print("Générateur OK.")
