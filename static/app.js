// VISIO-CMR Dashboard Javascript Logic

// Dynamic API Base URL (Relative path works everywhere: Render, Ngrok, Localhost, XAMPP)
const API_BASE = "";

// State management
let currentSettings = {
    enable_denoise: true,
    denoise_strength: 5,
    enable_contrast: true,
    contrast_limit: 2.0,
    enable_sharpness: true,
    sharpness_strength: 0.8,
    enable_upscale: true,
    upscale_method: "traditional",
    selected_model: "fsrcnn",
    video_source: "simulation",
    codec_opt: true
};

let serverIp = "127.0.0.1";
let hasModels = false;
let sliderVal = 0.5; // Split position (0.0 to 1.0)
let isDragging = false;
let ws = null;
let streamInterval = null;

// DOM Elements
const canvas = document.getElementById("comparison-canvas");
const ctx = canvas.getContext("2d");
const hiddenStreamImg = document.getElementById("hidden-stream");
const sliderBar = document.getElementById("slider-bar");
const sliderContainer = document.getElementById("slider-container");
const serverIpText = document.getElementById("server-ip-text");
const hudMethodText = document.getElementById("hud-method-text");
const labelActiveSource = document.getElementById("label-active-source");
const labelActiveMethod = document.getElementById("label-active-method");
const mobileUrlSpan = document.getElementById("mobile-url-span");
const mobileGuide = document.getElementById("mobile-guide");
const recEngineText = document.getElementById("rec-engine-text");

// Tab Elements
const tabBtnDemo = document.getElementById("tab-btn-demo");
const tabBtnMetrics = document.getElementById("tab-btn-metrics");
const tabBtnMobile = document.getElementById("tab-btn-mobile");
const tabBtnDoc = document.getElementById("tab-btn-doc");

const tabContentDemo = document.getElementById("tab-content-demo");
const tabContentMetrics = document.getElementById("tab-content-metrics");
const tabContentMobile = document.getElementById("tab-content-mobile");
const tabContentDoc = document.getElementById("tab-content-doc");

// Form Inputs
const chkDenoise = document.getElementById("chk-denoise");
const sliderDenoise = document.getElementById("slider-denoise");
const denoiseVal = document.getElementById("denoise-val");

const chkContrast = document.getElementById("chk-contrast");
const sliderContrast = document.getElementById("slider-contrast");
const contrastVal = document.getElementById("contrast-val");

const chkSharpness = document.getElementById("chk-sharpness");
const sliderSharpness = document.getElementById("slider-sharpness");
const sharpnessVal = document.getElementById("sharpness-val");

const chkUpscale = document.getElementById("chk-upscale");
const selectUpscaleMethod = document.getElementById("select-upscale-method");
const aiModelBox = document.getElementById("ai-model-box");
const selectAiModel = document.getElementById("select-ai-model");
const modelStatusBadge = document.getElementById("model-status-badge");

const selectVideoSource = document.getElementById("select-video-source");
const chkCodecOpt = document.getElementById("chk-codec-opt");

// Metric fields
const metricFps = document.getElementById("metric-fps");
const metricLatency = document.getElementById("metric-latency");
const metricLoss = document.getElementById("metric-loss");
const progressLoss = document.getElementById("progress-loss");
const lossWarning = document.getElementById("loss-warning");
const bandwidthSavingText = document.getElementById("bandwidth-saving-text");

// Mobile elements
const mobileStartSection = document.getElementById("mobile-start-section");
const btnStartMobile = document.getElementById("btn-start-mobile");
const btnStopMobile = document.getElementById("btn-stop-mobile");
const btnSwitchCamera = document.getElementById("btn-switch-camera");
const mobileVideo = document.getElementById("mobile-video");
const mobileFpsBadge = document.getElementById("mobile-fps-badge");
const cameraOverlayPlaceholder = document.getElementById("camera-overlay-placeholder");

let currentFacingMode = "environment"; // Default back camera

// Initialize Charts
let latencyChart = null;
let bandwidthChart = null;

// Check if mobile user agent
const isMobileDevice = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth < 768;

// MAIN INITIALIZATION
document.addEventListener("DOMContentLoaded", () => {
    // 1. Setup Icons
    lucide.createIcons();
    
    // 2. Mobile adaptation
    if (isMobileDevice) {
        // Hide desktop tab navigation and dashboard tabs on mobile phone
        const tabNavBar = document.getElementById("tab-nav-bar");
        if (tabNavBar) tabNavBar.classList.add("hidden");
        const tabContents = document.querySelectorAll(".tab-content");
        tabContents.forEach(c => c.classList.add("hidden"));
        if (mobileStartSection) mobileStartSection.classList.remove("hidden");
        currentSettings.video_source = "mobile";
    }
    
    // 3. Setup Charts
    initCharts();
    
    // 4. Set the MJPEG stream source dynamically
    hiddenStreamImg.src = `${API_BASE}/api/stream`;
    
    // Mobile button listeners
    if (btnStartMobile) btnStartMobile.addEventListener("click", startMobileCameraStream);
    if (btnStopMobile) btnStopMobile.addEventListener("click", stopMobileCameraStream);
    if (btnSwitchCamera) {
        btnSwitchCamera.addEventListener("click", async () => {
            currentFacingMode = currentFacingMode === "environment" ? "user" : "environment";
            if (isStreamingActive && mobileVideo && mobileVideo.srcObject) {
                // Stop current video tracks only without dropping WebSocket
                const stream = mobileVideo.srcObject;
                stream.getTracks().forEach(track => track.stop());
                try {
                    const constraints = {
                        video: { facingMode: currentFacingMode, width: { ideal: 640 }, height: { ideal: 360 } },
                        audio: false
                    };
                    const newStream = await navigator.mediaDevices.getUserMedia(constraints);
                    mobileVideo.srcObject = newStream;
                    await mobileVideo.play();
                } catch (e) {
                    console.error("Erreur lors du changement de caméra :", e);
                }
            }
        });
    }
    
    // 5. Start Canvas Draw Loop
    requestAnimationFrame(drawCanvasLoop);
    
    // 6. Bind Events
    setupEventListeners();
});

// EVENT BINDINGS
function setupEventListeners() {
    // Slider Drag Logic
    const handleMove = (clientX) => {
        const rect = sliderContainer.getBoundingClientRect();
        const x = clientX - rect.left;
        sliderVal = Math.max(0.01, Math.min(0.99, x / rect.width));
        sliderBar.style.left = `${sliderVal * 100}%`;
    };
    
    sliderContainer.addEventListener("mousedown", (e) => {
        isDragging = true;
        handleMove(e.clientX);
    });
    
    window.addEventListener("mousemove", (e) => {
        if (isDragging) handleMove(e.clientX);
    });
    
    window.addEventListener("mouseup", () => {
        isDragging = false;
    });
    
    // Touch support for slider
    sliderContainer.addEventListener("touchstart", (e) => {
        isDragging = true;
        handleMove(e.touches[0].clientX);
    });
    
    window.addEventListener("touchmove", (e) => {
        if (isDragging) handleMove(e.touches[0].clientX);
    });
    
    window.addEventListener("touchend", () => {
        isDragging = false;
    });
    
    // Control changes triggers API sync
    const inputs = [
        chkDenoise, sliderDenoise, chkContrast, sliderContrast,
        chkSharpness, sliderSharpness, chkUpscale, selectUpscaleMethod,
        selectAiModel, selectVideoSource, chkCodecOpt
    ];
    
    inputs.forEach(input => {
        input.addEventListener("change", syncSettingsToBackend);
        input.addEventListener("input", updateUIBadges); // Real-time badge text update
    });
    
    // Mobile Start Streaming Button
    btnStartMobile.addEventListener("click", startMobileCameraStream);
    btnStopMobile.addEventListener("click", stopMobileCameraStream);

    // Tab buttons event listeners
    tabBtnDemo.addEventListener("click", () => switchTab(tabBtnDemo, tabContentDemo));
    tabBtnMetrics.addEventListener("click", () => switchTab(tabBtnMetrics, tabContentMetrics));
    tabBtnMobile.addEventListener("click", () => switchTab(tabBtnMobile, tabContentMobile));
    tabBtnDoc.addEventListener("click", () => switchTab(tabBtnDoc, tabContentDoc));
}

// TAB NAVIGATION SWITCHER
function switchTab(activeBtn, activeContent) {
    const contents = [tabContentDemo, tabContentMetrics, tabContentMobile, tabContentDoc];
    contents.forEach(c => {
        if (c) c.classList.add("hidden");
    });
    
    if (activeContent) activeContent.classList.remove("hidden");
    
    const buttons = [tabBtnDemo, tabBtnMetrics, tabBtnMobile, tabBtnDoc];
    buttons.forEach(btn => {
        if (btn) {
            btn.className = "tab-btn px-5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all duration-200 flex items-center gap-2 bg-slate-800/80 text-gray-300 hover:bg-slate-700";
        }
    });
    
    if (activeBtn) {
        activeBtn.className = "tab-btn px-5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all duration-200 flex items-center gap-2 bg-yellow-500 text-slate-900 shadow-[0_0_10px_rgba(250,204,21,0.2)]";
    }
}

// REALTIME TEXT BADGES ON SLIDERS
function updateUIBadges() {
    denoiseVal.textContent = sliderDenoise.value;
    contrastVal.textContent = (sliderContrast.value / 10).toFixed(1);
    sharpnessVal.textContent = (sliderSharpness.value / 10).toFixed(1);
    
    // Toggle sub-boxes
    if (chkUpscale.checked && selectUpscaleMethod.value === "ai") {
        aiModelBox.classList.remove("hidden");
    } else {
        aiModelBox.classList.add("hidden");
    }
    
    if (selectVideoSource.value === "mobile") {
        mobileGuide.classList.remove("hidden");
    } else {
        mobileGuide.classList.add("hidden");
    }
}

// SYNC CONTROLS TO API
async function syncSettingsToBackend() {
    currentSettings = {
        enable_denoise: chkDenoise.checked,
        denoise_strength: parseInt(sliderDenoise.value),
        enable_contrast: chkContrast.checked,
        contrast_limit: parseFloat(sliderContrast.value) / 10.0,
        enable_sharpness: chkSharpness.checked,
        sharpness_strength: parseFloat(sliderSharpness.value) / 10.0,
        enable_upscale: chkUpscale.checked,
        upscale_method: selectUpscaleMethod.value,
        selected_model: selectAiModel.value,
        video_source: selectVideoSource.value,
        codec_opt: chkCodecOpt.checked
    };
    
    updateUIBadges();
    
    try {
        await fetch(`${API_BASE}/api/settings`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(currentSettings)
        });
    } catch (e) {
        console.error("Impossible de sauvegarder les réglages :", e);
    }
}

// FETCH LIVE STATUS & METRICS
async function fetchStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/status`);
        if (!res.ok) return;
        const data = await res.json();
        
        serverIp = data.server_ip;
        hasModels = data.has_models;
        
        serverIpText.textContent = serverIp;
        
        // Update mobile URL display dynamically using current site origin
        const currentOrigin = window.location.origin;
        const mobileUrlFull = document.getElementById("mobile-url-span-full");
        if (mobileUrlFull) {
            mobileUrlFull.textContent = currentOrigin;
        }
        if (mobileUrlSpan) {
            mobileUrlSpan.textContent = currentOrigin;
        }
        
        // Update models availability badge
        if (hasModels) {
            modelStatusBadge.textContent = "🧠 Modèles IA chargés et prêts.";
            modelStatusBadge.className = "text-[10px] mt-1 block text-green-400 font-medium";
        } else {
            modelStatusBadge.textContent = "⚠️ Modèles IA non trouvés, upscaling traditionnel activé.";
            modelStatusBadge.className = "text-[10px] mt-1 block text-yellow-500 font-medium";
        }
        
        // Sync control inputs with backend (only if user is not actively dragging/interacting)
        if (!document.activeElement || document.activeElement.tagName !== "INPUT") {
            chkDenoise.checked = data.settings.enable_denoise;
            sliderDenoise.value = data.settings.denoise_strength;
            chkContrast.checked = data.settings.enable_contrast;
            sliderContrast.value = Math.round(data.settings.contrast_limit * 10);
            chkSharpness.checked = data.settings.enable_sharpness;
            sliderSharpness.value = Math.round(data.settings.sharpness_strength * 10);
            chkUpscale.checked = data.settings.enable_upscale;
            selectUpscaleMethod.value = data.settings.upscale_method;
            selectAiModel.value = data.settings.selected_model;
            selectVideoSource.value = data.settings.video_source;
            chkCodecOpt.checked = data.settings.codec_opt;
            updateUIBadges();
        }
        
        // Update live metrics on dashboard
        metricFps.textContent = data.metrics.fps.toFixed(1);
        metricLatency.textContent = data.metrics.total_time.toFixed(1);
        metricLoss.textContent = `${data.metrics.network_loss.toFixed(2)}%`;
        progressLoss.style.width = `${Math.min(100, data.metrics.network_loss * 15)}%`;
        
        if (data.metrics.network_loss > 1.5) {
            lossWarning.classList.remove("hidden");
            progressLoss.className = "bg-red-500 h-1.5 transition-all duration-300";
        } else {
            lossWarning.classList.add("hidden");
            progressLoss.className = "bg-emerald-500 h-1.5 transition-all duration-300";
        }
        
        // Update rendering method label
        labelActiveMethod.textContent = data.metrics.used_method;
        hudMethodText.textContent = data.metrics.used_method;
        
        // Update source label
        const sourcesNames = {
            simulation: "SIMULATION TV (CRTV)",
            webcam: "WEBCAM LOCALE",
            mobile: "CAMÉRA SMARTPHONE (WI-FI)"
        };
        labelActiveSource.textContent = sourcesNames[data.settings.video_source] || "INCONNU";
        
        // Dynamic Recommendation Engine Text
        updateRecommendationEngine(data);
        
        // Update Charts
        updateChartsData(data.metrics, data.settings.codec_opt);
        
    } catch (e) {
        console.warn("Erreur de récupération du statut :", e);
    }
}

// RECOMMENDATION ENGINE TEXT
function updateRecommendationEngine(data) {
    let text = "";
    if (data.settings.video_source === "mobile") {
        text += "[CAPTEUR SMARTPHONE ACTIVE]\n";
    }
    
    if (data.settings.codec_opt) {
        text += "✓ CODEC DYNAMIQUE: H.265/AV1 actif.\n";
        text += "✓ ÉCONOMIE: ~55% de bande passante.\n";
        text += "✓ SIGNAL: Très stable (Perte: " + data.metrics.network_loss.toFixed(2) + "%).\n";
        text += "✓ Statut: Recommandé pour MTN/Orange Cameroun.";
        bandwidthSavingText.textContent = "-55%";
        bandwidthSavingText.className = "text-[9px] text-green-400 font-bold font-mono";
    } else {
        text += "⚠ CODEC NON OPTIMISE: Flux H.264 actif.\n";
        text += "⚠ DEBIT REQUIS: Élevé (4.5 Mbps).\n";
        text += "⚠ CONGESTION: Perte de paquets critique (" + data.metrics.network_loss.toFixed(2) + "%).\n";
        text += "⚠ Action: Activez 'Optimisation de Flux' (H.265).";
        bandwidthSavingText.textContent = "0% (Saturé)";
        bandwidthSavingText.className = "text-[9px] text-red-500 font-bold font-mono";
    }
    recEngineText.innerHTML = text.replace(/\n/g, "<br>");
}

// DRAW LOOP FOR COMPARISON CANVAS
function drawCanvasLoop() {
    if (hiddenStreamImg.complete && hiddenStreamImg.naturalWidth > 0) {
        const w = hiddenStreamImg.naturalWidth / 2; // Split width (e.g. 960)
        const h = hiddenStreamImg.naturalHeight;    // Height (e.g. 540)
        
        if (canvas.width !== w || canvas.height !== h) {
            canvas.width = w;
            canvas.height = h;
        }
        
        ctx.clearRect(0, 0, w, h);
        
        const splitX = sliderVal * w;
        
        // Draw Left: Original (Read from left half of double-wide source)
        ctx.drawImage(hiddenStreamImg, 0, 0, splitX, h, 0, 0, splitX, h);
        
        // Draw Right: Enhanced (Read from right half of double-wide source)
        ctx.drawImage(hiddenStreamImg, w + splitX, 0, w - splitX, h, splitX, 0, w - splitX, h);
        
        // Draw separation text label tags
        ctx.fillStyle = "rgba(11, 15, 25, 0.7)";
        
        // Original text label
        ctx.fillRect(15, 15, 95, 26);
        ctx.fillStyle = "#f87171"; // Light red
        ctx.font = "bold 11px system-ui, sans-serif";
        ctx.fillText("ORIGINAL", 25, 32);
        
        // Enhanced text label
        ctx.fillStyle = "rgba(11, 15, 25, 0.7)";
        ctx.fillRect(w - 145, 15, 130, 26);
        ctx.fillStyle = "#34d399"; // Light green
        ctx.fillText("SIGNAL AMÉLIORÉ", w - 135, 32);
    }
    
    requestAnimationFrame(drawCanvasLoop);
}

// CHARTS SETUP
function initCharts() {
    // Latency Chart
    const ctxL = document.getElementById("latencyChart").getContext("2d");
    latencyChart = new Chart(ctxL, {
        type: "bar",
        data: {
            labels: ["Bruit", "Contraste", "Netteté", "Upscale"],
            datasets: [{
                label: "Latence (ms)",
                data: [0, 0, 0, 0],
                backgroundColor: [
                    "rgba(52, 211, 153, 0.6)", // Green
                    "rgba(96, 165, 250, 0.6)", // Blue
                    "rgba(251, 191, 36, 0.6)", // Yellow
                    "rgba(167, 139, 250, 0.6)" // Purple
                ],
                borderColor: [
                    "#10b981", "#3b82f6", "#f59e0b", "#8b5cf6"
                ],
                borderWidth: 1.5,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#9ca3af", font: { size: 9 } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: "#9ca3af", font: { size: 9 } }
                }
            }
        }
    });
    
    // Bandwidth Chart
    const ctxB = document.getElementById("bandwidthChart").getContext("2d");
    bandwidthChart = new Chart(ctxB, {
        type: "bar",
        data: {
            labels: ["H.264 (Std)", "H.265 (Opt)", "AV1 (Opt)"],
            datasets: [{
                label: "Débit (Mbps)",
                data: [4.5, 2.0, 1.4],
                backgroundColor: [
                    "rgba(239, 68, 68, 0.5)",   // Red (H.264)
                    "rgba(5, 107, 56, 0.6)",   // Cameroon Green (H.265)
                    "rgba(252, 209, 22, 0.6)"   // Cameroon Gold (AV1)
                ],
                borderColor: [
                    "#ef4444", "#056b38", "#fcd116"
                ],
                borderWidth: 1.5,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: "Mbps", color: "#9ca3af", font: { size: 9 } },
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#9ca3af", font: { size: 9 } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: "#9ca3af", font: { size: 9 } }
                }
            }
        }
    });
}

function updateChartsData(metrics, isCodecOptActive) {
    if (latencyChart) {
        latencyChart.data.datasets[0].data = [
            metrics.denoise_time,
            metrics.contrast_time,
            metrics.sharpness_time,
            metrics.upscale_time
        ];
        latencyChart.update("none"); // Update without animation for performance
    }
    
    if (bandwidthChart) {
        // Highlight active codec selection
        if (isCodecOptActive) {
            bandwidthChart.data.datasets[0].backgroundColor = [
                "rgba(239, 68, 68, 0.2)", // dim H.264
                "rgba(16, 185, 129, 0.8)", // highlight H.265
                "rgba(252, 209, 22, 0.4)"
            ];
        } else {
            bandwidthChart.data.datasets[0].backgroundColor = [
                "rgba(239, 68, 68, 0.8)", // highlight H.264
                "rgba(16, 185, 129, 0.2)",
                "rgba(252, 209, 22, 0.2)"
            ];
        }
        bandwidthChart.update("none");
    }
}

// PHONE CAMERA CAPTURE LOGIC (CLIENT SIDE)
let isStreamingActive = false;
let isSendingFrame = false;

async function startMobileCameraStream() {
    if (isStreamingActive) return;
    try {
        const constraints = {
            video: {
                facingMode: currentFacingMode,
                width: { ideal: 640 },
                height: { ideal: 360 },
                frameRate: { ideal: 15 }
            },
            audio: false
        };
        
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        mobileVideo.srcObject = stream;
        await mobileVideo.play();
        
        isStreamingActive = true;
        
        // Hide placeholder overlay and toggle action buttons
        if (cameraOverlayPlaceholder) cameraOverlayPlaceholder.classList.add("hidden");
        if (btnStartMobile) btnStartMobile.classList.add("hidden");
        if (btnStopMobile) btnStopMobile.classList.remove("hidden");
        
        // Connect WebSocket and start sending loop
        connectWebSocket();
        startSendingFrames();
        
    } catch (e) {
        alert("Impossible d'accéder à la caméra du téléphone : " + e.message);
        console.error(e);
    }
}

function connectWebSocket() {
    if (!isStreamingActive) return;
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
    
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsHost = window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/api/ws/mobile`;
    
    if (mobileFpsBadge) {
        mobileFpsBadge.textContent = "🟡 Connexion...";
        mobileFpsBadge.className = "px-2.5 py-1 bg-yellow-950/80 border border-yellow-700 text-xs font-mono text-yellow-400 rounded-lg animate-pulse";
    }
    
    console.log(`Connexion WebSocket mobile vers : ${wsUrl}`);
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log("WebSocket mobile connecté avec succès.");
        isSendingFrame = false;
        if (mobileFpsBadge) {
            mobileFpsBadge.textContent = "🟢 EN DIRECT";
            mobileFpsBadge.className = "px-2.5 py-1 bg-green-900/80 border border-green-500 text-xs font-mono text-green-300 font-bold rounded-lg";
        }
    };
    
    ws.onmessage = (event) => {
        // Backend sent ACK: ready for next frame
        isSendingFrame = false;
    };
    
    ws.onclose = () => {
        console.log("WebSocket mobile déconnecté. Tentative de reconnexion...");
        isSendingFrame = false;
        if (mobileFpsBadge && isStreamingActive) {
            mobileFpsBadge.textContent = "🟡 Reconnexion...";
            mobileFpsBadge.className = "px-2.5 py-1 bg-yellow-950/80 border border-yellow-700 text-xs font-mono text-yellow-400 rounded-lg animate-pulse";
        }
        // Auto-reconnect WebSocket if streaming is still active
        if (isStreamingActive) {
            setTimeout(connectWebSocket, 1500);
        }
    };
    
    ws.onerror = (err) => {
        console.error("Erreur WebSocket :", err);
        try { ws.close(); } catch(e) {}
    };
}

function startSendingFrames() {
    if (streamInterval) clearInterval(streamInterval);
    
    const hiddenCanvas = document.createElement("canvas");
    hiddenCanvas.width = 640;
    hiddenCanvas.height = 360;
    const hCtx = hiddenCanvas.getContext("2d");
    
    let framesSent = 0;
    let lastTime = timeSeconds();
    
    streamInterval = setInterval(() => {
        if (!isStreamingActive) return;
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        if (isSendingFrame) return; // Flow control: wait for previous frame ACK
        if (!mobileVideo || mobileVideo.readyState < 2) return;
        
        try {
            hCtx.drawImage(mobileVideo, 0, 0, 640, 360);
            isSendingFrame = true;
            
            hiddenCanvas.toBlob((blob) => {
                if (blob && ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(blob);
                    framesSent++;
                    
                    const now = timeSeconds();
                    if (now - lastTime >= 1.0) {
                        const mobileFps = framesSent / (now - lastTime);
                        if (mobileFpsBadge) {
                            mobileFpsBadge.textContent = `🟢 EN DIRECT (${mobileFps.toFixed(0)} FPS)`;
                        }
                        framesSent = 0;
                        lastTime = now;
                    }
                } else {
                    isSendingFrame = false;
                }
            }, "image/jpeg", 0.5); // 50% JPEG quality for smooth, low latency transmission
        } catch (e) {
            isSendingFrame = false;
        }
        
    }, 80); // ~12 FPS: optimal stability and zero congestion
}

function stopMobileCameraStream() {
    isStreamingActive = false;
    isSendingFrame = false;
    
    if (streamInterval) {
        clearInterval(streamInterval);
        streamInterval = null;
    }
    
    if (ws) {
        const tempWs = ws;
        ws = null;
        tempWs.onclose = null; // Prevent triggering auto-reconnect on manual stop
        try { tempWs.close(); } catch(e) {}
    }
    
    if (mobileVideo && mobileVideo.srcObject) {
        const stream = mobileVideo.srcObject;
        const tracks = stream.getTracks();
        tracks.forEach(track => track.stop());
        mobileVideo.srcObject = null;
    }
    
    if (cameraOverlayPlaceholder) cameraOverlayPlaceholder.classList.remove("hidden");
    if (btnStartMobile) btnStartMobile.classList.remove("hidden");
    if (btnStopMobile) btnStopMobile.classList.add("hidden");
    if (mobileFpsBadge) {
        mobileFpsBadge.textContent = "⚪ Hors-Ligne";
        mobileFpsBadge.className = "px-2.5 py-1 bg-slate-900 border border-slate-800 text-xs font-mono text-gray-400 rounded-lg";
    }
}

// Utility helper
function timeSeconds() {
    return timeSecondsRaw() / 1000;
}
function timeSecondsRaw() {
    return new Date().getTime();
}
