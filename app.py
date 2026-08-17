from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import cv2
import numpy as np
import time
import os
import socket
from pydantic import BaseModel

from generator import CameroonianTVGenerator
from enhancer import VideoEnhancer

app = FastAPI(title="VISIO-CMR: Video Enhancer and Optimizer")

# CORS - Permet les requêtes depuis Apache XAMPP (port 80/443) vers FastAPI (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
generator = CameroonianTVGenerator(640, 360)
enhancer = VideoEnhancer()

# Configuration state
settings = {
    "enable_denoise": True,
    "denoise_strength": 5,
    "enable_contrast": True,
    "contrast_limit": 2.0,
    "enable_sharpness": True,
    "sharpness_strength": 0.8,
    "enable_upscale": True,
    "upscale_method": "traditional",  # "ai" or "traditional"
    "selected_model": "fsrcnn",       # "fsrcnn" or "espcn"
    "video_source": "simulation",      # "simulation", "webcam", "mobile"
    "codec_opt": True,                 # True = H.265/AV1 active, False = H.264
}

# Live metrics
metrics_state = {
    "fps": 0.0,
    "denoise_time": 0.0,
    "contrast_time": 0.0,
    "sharpness_time": 0.0,
    "upscale_time": 0.0,
    "total_time": 0.0,
    "used_method": "Lanczos4 (Traditionnel)",
    "h264_bitrate": 4.5,   # Mbps (1080p reference)
    "h265_bitrate": 2.0,   # Mbps (approx 55% saving)
    "av1_bitrate": 1.4,    # Mbps (approx 68% saving)
    "network_loss": 0.5,   # % loss
}

latest_mobile_frame = None
mobile_last_update = 0

# Video Source Handler
class VideoSourceManager:
    def __init__(self):
        self.cap = None
        self.active_source = "simulation"
        
    def get_frame(self):
        global latest_mobile_frame, mobile_last_update
        self.active_source = settings["video_source"]
        
        if self.active_source == "simulation":
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            # Generate simulation frame
            # If Denoising is off, generate standard noise. If on, generate high noise so we see the difference
            n_level = 28 if settings["enable_denoise"] else 12
            return generator.generate_frame(noise_level=n_level, blur_strength=3, compression_artifacts=True)
            
        elif self.active_source == "webcam":
            if self.cap is None:
                self.cap = cv2.VideoCapture(0)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
            ret, frame = self.cap.read()
            if not ret or frame is None:
                # Show red webcam error frame
                err_frame = np.zeros((360, 640, 3), dtype=np.uint8)
                cv2.rectangle(err_frame, (0, 0), (640, 360), (20, 20, 40), -1)
                cv2.putText(err_frame, "Webcam indisponible ou non connectee", (80, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                cv2.putText(err_frame, "Basculez sur 'Simulation' pour tester", (120, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                return err_frame
            return frame
            
        elif self.active_source == "mobile":
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            # Check timeout for mobile camera (5 seconds without updates)
            if latest_mobile_frame is None or (time.time() - mobile_last_update > 5.0):
                err_frame = np.zeros((360, 640, 3), dtype=np.uint8)
                # Green glassmorphism style card
                cv2.rectangle(err_frame, (0, 0), (640, 360), (30, 45, 30), -1)
                cv2.putText(err_frame, "En attente du flux mobile (Android / iOS)", (100, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(err_frame, "1. Connectez le mobile au MEME reseau Wi-Fi", (60, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1)
                
                # Try to get server IP address
                s_ip = get_local_ip()
                cv2.putText(err_frame, f"2. Ouvrez : http://{s_ip}:8000", (60, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1)
                cv2.putText(err_frame, "3. Cliquez sur 'Demarrer Camera Mobile'", (60, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1)
                return err_frame
            return latest_mobile_frame
            
        # Default fallback
        return np.zeros((360, 640, 3), dtype=np.uint8)

manager = VideoSourceManager()

def get_local_ip():
    """Gets local IP address of the server to display on the placeholder."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't need to connect, just resolves local routing interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# Request schema
class SettingsModel(BaseModel):
    enable_denoise: bool
    denoise_strength: int
    enable_contrast: bool
    contrast_limit: float
    enable_sharpness: bool
    sharpness_strength: float
    enable_upscale: bool
    upscale_method: str
    selected_model: str
    video_source: str
    codec_opt: bool

@app.get("/api/status")
def get_status():
    """Returns current settings and performance metrics."""
    global metrics_state
    
    # Simulate network packet loss rate depending on codec optimization
    # In H.265/AV1 mode, bandwidth is reduced, meaning packet loss rate drops under local network constraints.
    if settings["codec_opt"]:
        metrics_state["network_loss"] = 0.02  # Very stable (0.02% loss)
    else:
        # Without optimization, high bitrate of raw upscaled 1080p H.264 stream causes congestion
        metrics_state["network_loss"] = 3.84  # 3.84% loss (causes video freeze/glitches)
        
    return {
        "settings": settings,
        "metrics": metrics_state,
        "server_ip": get_local_ip(),
        "has_models": enhancer.has_models
    }

@app.post("/api/settings")
def update_settings(new_settings: SettingsModel):
    """Updates settings in real-time."""
    global settings
    settings["enable_denoise"] = new_settings.enable_denoise
    settings["denoise_strength"] = new_settings.denoise_strength
    settings["enable_contrast"] = new_settings.enable_contrast
    settings["contrast_limit"] = new_settings.contrast_limit
    settings["enable_sharpness"] = new_settings.enable_sharpness
    settings["sharpness_strength"] = new_settings.sharpness_strength
    settings["enable_upscale"] = new_settings.enable_upscale
    settings["upscale_method"] = new_settings.upscale_method
    settings["selected_model"] = new_settings.selected_model
    settings["video_source"] = new_settings.video_source
    settings["codec_opt"] = new_settings.codec_opt
    
    return JSONResponse(content={"status": "updated"})

# WebSocket for receiving camera frames from Android/iOS devices
@app.websocket("/api/ws/mobile")
async def websocket_mobile_camera(websocket: WebSocket):
    await websocket.accept()
    global latest_mobile_frame, mobile_last_update
    settings["video_source"] = "mobile" # Auto-switch backend source to mobile camera
    print("📱 Smartphone connecté via WebSocket ! Basculement automatique sur la caméra mobile.")
    try:
        while True:
            # Receive binary frame (JPEG) from phone browser
            data = await websocket.receive_bytes()
            # Decode JPEG to opencv image
            np_arr = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # Resize mobile frame to standard input width (640x360) for consistency
                latest_mobile_frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
                mobile_last_update = time.time()
                
            # Send brief heartbeat acknowledgment back to mobile to regulate speed
            await websocket.send_text("ACK")
    except WebSocketDisconnect:
        print("Téléphone déconnecté.")
    except Exception as e:
        print(f"Erreur WebSocket mobile : {e}")

# Video streaming loop
def generate_mjpeg_stream():
    global metrics_state
    last_fps_time = time.time()
    frame_count = 0
    
    while True:
        t0 = time.time()
        
        # 1. Fetch frame from selected source
        frame = manager.get_frame()
        
        # 2. Process and enhance frame
        comparison, metrics = enhancer.enhance_frame(frame, settings)
        
        # Update metrics
        metrics_state["denoise_time"] = round(metrics["denoise_time"], 1)
        metrics_state["contrast_time"] = round(metrics["contrast_time"], 1)
        metrics_state["sharpness_time"] = round(metrics["sharpness_time"], 1)
        metrics_state["upscale_time"] = round(metrics["upscale_time"], 1)
        metrics_state["total_time"] = round(metrics["total_time"], 1)
        metrics_state["used_method"] = metrics["used_method"]
        
        # FPS Calculation
        frame_count += 1
        elapsed = time.time() - last_fps_time
        if elapsed >= 1.0:
            metrics_state["fps"] = round(frame_count / elapsed, 1)
            frame_count = 0
            last_fps_time = time.time()
            
        # 3. Encode comparison frame as JPEG (quality 75% for network streaming)
        ret, jpeg = cv2.imencode(".jpg", comparison, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if not ret:
            continue
            
        # Yield frame in MJPEG boundary format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
               
        # Cap streaming rate to ~25fps to save CPU
        processing_elapsed = time.time() - t0
        delay = max(0.01, 0.04 - processing_elapsed)
        time.sleep(delay)

@app.get("/api/stream")
def video_stream():
    """Endpoint serving the MJPEG video stream."""
    return StreamingResponse(generate_mjpeg_stream(), media_type="multipart/x-mixed-replace; boundary=frame")

# Serve frontend files
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
else:
    print("[ATTENTION] Le dossier 'static' n'existe pas encore. Le frontend ne pourra pas être servi.")

if __name__ == "__main__":
    ip = "0.0.0.0" # Listen on all interfaces
    local_ip = get_local_ip()
    
    print(f"="*60)
    print(f"  VISIO-CMR - Backend API (FastAPI + OpenCV)")
    print(f"="*60)
    print(f"  API locale    : http://localhost:8000")
    print(f"  API réseau    : http://{local_ip}:8000")
    print(f"")
    print(f"  ACCÈS DEPUIS VOTRE iPHONE / ANDROID :")
    print(f"  → Ouvrez https://{local_ip}/visio-cmr/ dans Safari/Chrome")
    print(f"  (Le frontend est servi par Apache XAMPP sur le port 443)")
    print(f"="*60)
    
    uvicorn.run(app, host=ip, port=8000)
