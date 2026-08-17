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

active_mobile_streams = {}  # client_id -> {"frame": np_array, "last_update": float, "id": int}
client_counter = 0

# Video Source Handler
class VideoSourceManager:
    def __init__(self):
        self.cap = None
        self.active_source = "simulation"
        
    def get_frame(self):
        global active_mobile_streams
        self.active_source = settings["video_source"]
        
        if self.active_source == "simulation":
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            n_level = 28 if settings["enable_denoise"] else 12
            return generator.generate_frame(noise_level=n_level, blur_strength=3, compression_artifacts=True)
            
        elif self.active_source == "webcam":
            if self.cap is None:
                self.cap = cv2.VideoCapture(0)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
            ret, frame = self.cap.read()
            if not ret or frame is None:
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
            
            # Clean up stale connections (> 5 seconds inactive)
            now = time.time()
            stale_keys = [k for k, v in active_mobile_streams.items() if (now - v["last_update"]) > 5.0]
            for k in stale_keys:
                del active_mobile_streams[k]
                
            active_frames = [v["frame"] for v in active_mobile_streams.values() if v["frame"] is not None]
            
            if len(active_frames) == 0:
                err_frame = np.zeros((360, 640, 3), dtype=np.uint8)
                cv2.rectangle(err_frame, (0, 0), (640, 360), (30, 45, 30), -1)
                cv2.putText(err_frame, "En attente du flux mobile (Android / iOS)", (100, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(err_frame, "1. Connectez le mobile sur l'adresse web", (60, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1)
                cv2.putText(err_frame, "2. Cliquez sur 'Demarrer la Camera Mobile'", (60, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1)
                return err_frame
                
            elif len(active_frames) == 1:
                return active_frames[0]
                
            else:
                # MULTI-CAMERA SPLIT SCREEN (Multiple phones streaming simultaneously)
                if len(active_frames) == 2:
                    f1 = cv2.resize(active_frames[0], (320, 360))
                    f2 = cv2.resize(active_frames[1], (320, 360))
                    cv2.putText(f1, "CAM 1 (MOBILE)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    cv2.putText(f2, "CAM 2 (MOBILE)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    combined = np.hstack([f1, f2])
                    cv2.line(combined, (320, 0), (320, 360), (0, 255, 255), 2)
                    return combined
                else:
                    resized = [cv2.resize(f, (320, 180)) for f in active_frames[:4]]
                    while len(resized) < 4:
                        blank = np.zeros((180, 320, 3), dtype=np.uint8)
                        resized.append(blank)
                    for idx, img in enumerate(resized):
                        cv2.putText(img, f"CAM {idx+1}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    top_row = np.hstack([resized[0], resized[1]])
                    bot_row = np.hstack([resized[2], resized[3]])
                    return np.vstack([top_row, bot_row])
                    
        return np.zeros((360, 640, 3), dtype=np.uint8)

manager = VideoSourceManager()

def get_local_ip():
    """Gets local IP address of the server to display on the placeholder."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
    global metrics_state
    if settings["codec_opt"]:
        metrics_state["network_loss"] = 0.02
    else:
        metrics_state["network_loss"] = 3.84
        
    return {
        "settings": settings,
        "metrics": metrics_state,
        "server_ip": get_local_ip(),
        "has_models": enhancer.has_models,
        "active_cameras": len(active_mobile_streams)
    }

@app.post("/api/settings")
def update_settings(new_settings: SettingsModel):
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
    global active_mobile_streams, client_counter
    client_counter += 1
    client_id = f"client_{client_counter}"
    active_mobile_streams[client_id] = {"frame": None, "last_update": time.time(), "id": client_counter}
    
    settings["video_source"] = "mobile"
    print(f"📱 Smartphone #{client_counter} connecté via WebSocket ! Total caméras : {len(active_mobile_streams)}")
    
    try:
        while True:
            data = await websocket.receive_bytes()
            np_arr = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                resized_frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
                active_mobile_streams[client_id]["frame"] = resized_frame
                active_mobile_streams[client_id]["last_update"] = time.time()
                
            await websocket.send_text("ACK")
    except WebSocketDisconnect:
        print(f"Smartphone #{client_id} déconnecté.")
    except Exception as e:
        print(f"Erreur WebSocket mobile : {e}")
    finally:
        if client_id in active_mobile_streams:
            del active_mobile_streams[client_id]

# HTTP POST fallback endpoint for mobile camera ingestion
@app.post("/api/upload_frame")
async def upload_frame(request: Request):
    global active_mobile_streams, client_counter
    try:
        data = await request.body()
        if not data:
            return JSONResponse(content={"status": "empty"}, status_code=400)
            
        np_arr = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if frame is not None:
            client_ip = request.client.host if request.client else "http_client"
            client_id = f"http_{client_ip}"
            
            resized_frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
            active_mobile_streams[client_id] = {
                "frame": resized_frame,
                "last_update": time.time(),
                "id": client_ip
            }
            settings["video_source"] = "mobile"
            
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

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
