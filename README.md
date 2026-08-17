# 🇨🇲 VISIO-CMR : Amplificateur de Signal & Optimiseur de Flux Vidéo par IA

> **Projet de Fin de Cycle (Licence 3 Informatique - Cameroun)**  
> *Système intelligent de restauration de signal vidéo en temps réel et d'optimisation de bande passante pour les chaînes de télévision locales.*

---

## 📌 Présentation du Projet

Au Cameroun, la majorité des chaînes de télévision locales (CRTV, Canal 2, STV, etc.) sont confrontées à des défis majeurs lors des retansmissions en direct :
1. **Flou et bruit numérique** causés par des caméras ou des encodeurs d'ancienne génération.
2. **Congestion et coupures de signal** sur les liaisons 4G/Wi-Fi instables lors des événements en extérieur.

**VISIO-CMR** résout ce problème grâce à un pipeline hybride de traitement d'images et d'IA (débruitage bilatéral, égalisation CLAHE, masque flou, super-résolution) combiné à un encodage dynamique de nouvelle génération (**H.265 / AV1**) qui divise par deux la bande passante nécessaire sans dégrader la qualité HD.

---

## ✨ Fonctionnalités Clés

- 📱 **Détection Automatique d'Appareil (Dual-Screen)** :
  - **Sur Smartphone (iPhone / Android)** : L'application s'ouvre en **Mode Émetteur Caméra** (interface dédiée plein écran pour capturer et transmettre le flux vidéo en direct).
  - **Sur Ordinateur / Régie** : L'application s'ouvre en **Mode Tableau de Bord & Visualiseur HD** (comparateur avant/après avec slider interactif, filtres et métriques réseau).
- 🧠 **Traitement d'Image et Super-Résolution** :
  - **Filtre Bilatéral** : Élimine le grain et le bruit sans flouter les contours.
  - **CLAHE** : Égalisation adaptative de la luminosité pour déboucher les ombres.
  - **Masque Flou (Unsharp Masking)** : Accentuation chirurgicale de la netteté.
  - **Super-Résolution IA / Hybride** : Upscaling 480p → 1080p avec modèles Deep Learning (FSRCNN/ESPCN) et repli dynamique (Lanczos4).
- ⚡ **Optimisation de Flux Réseau** :
  - Simulation de réencodage H.265/AV1 économisant jusqu'à **55% de bande passante**.
  - Réduction de la perte de paquets de `3.8%` à `0.02%`.

---

## 🛠️ Architecture Technique

- **Backend** : Python (FastAPI, OpenCV, NumPy, Uvicorn, WebSockets).
- **Frontend** : HTML5, Vanilla JS, Tailwind CSS, Lucide Icons, Chart.js, Canvas API.
- **Protocoles** : WebSocket (Ingestion vidéo binaire mobile), MJPEG (Streaming direct).

---

## 🚀 Installation & Lancement

### 1. Cloner le dépôt et installer les dépendances
```bash
git clone https://github.com/VOTRE_NOM_UTILISATEUR/VISIO-CMR.git
cd VISIO-CMR
pip install -r requirements.txt
```

### 2. Démarrer le backend Python
```bash
python3 app.py
```

### 3. Utilisation Dual-Screen (Téléphone + PC)
- **Sur l'ordinateur** : Ouvrez `http://localhost:8000`
- **Sur le téléphone** : Ouvrez `http://[IP_PC]:8000` (ou via tunnel HTTPS `ssh -R 80:localhost:8000 localhost.run`)

---

## 📜 Licence
© 2026 - Développé dans le cadre de la soutenance de Licence 3 Informatique (Cameroun).
