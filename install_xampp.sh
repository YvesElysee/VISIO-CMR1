#!/bin/bash
# ============================================================
# VISIO-CMR : Script d'installation pour XAMPP
# Exécutez avec : sudo bash install_xampp.sh
# ============================================================

set -e

LAMPP_DIR="/opt/lampp"
HTDOCS_DIR="$LAMPP_DIR/htdocs/visio-cmr"
HTTPD_CONF="$LAMPP_DIR/etc/httpd.conf"
SSL_CONF="$LAMPP_DIR/etc/extra/httpd-ssl.conf"
VHOSTS_CONF="$LAMPP_DIR/etc/extra/httpd-vhosts.conf"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================================"
echo "  VISIO-CMR - Installation XAMPP Automatique"
echo "============================================================"

# ---- 1. Vérifier que XAMPP est installé ----
if [ ! -d "$LAMPP_DIR" ]; then
    echo "[ERREUR] XAMPP n'est pas installé dans $LAMPP_DIR !"
    exit 1
fi
echo "[OK] XAMPP trouvé dans $LAMPP_DIR"

# ---- 2. Copier les fichiers statiques vers htdocs ----
echo "[...] Copie des fichiers frontend vers $HTDOCS_DIR"
mkdir -p "$HTDOCS_DIR"
cp -f "$SCRIPT_DIR/static/index.html" "$HTDOCS_DIR/"
cp -f "$SCRIPT_DIR/static/app.js" "$HTDOCS_DIR/"
cp -f "$SCRIPT_DIR/static/styles.css" "$HTDOCS_DIR/"
chown -R $(logname):$(logname) "$HTDOCS_DIR" 2>/dev/null || true
echo "[OK] Fichiers frontend copiés."

# ---- 3. Activer mod_proxy_wstunnel dans httpd.conf ----
echo "[...] Activation de mod_proxy_wstunnel..."
if ! grep -q "mod_proxy_wstunnel" "$HTTPD_CONF"; then
    # Insert after mod_proxy_http line
    sed -i '/LoadModule proxy_http_module/a LoadModule proxy_wstunnel_module modules/mod_proxy_wstunnel.so' "$HTTPD_CONF"
    echo "[OK] mod_proxy_wstunnel activé."
else
    echo "[OK] mod_proxy_wstunnel déjà présent."
fi

# ---- 4. Activer httpd-vhosts.conf ----
echo "[...] Activation des VirtualHosts..."
sed -i 's|#Include etc/extra/httpd-vhosts.conf|Include etc/extra/httpd-vhosts.conf|' "$HTTPD_CONF"
echo "[OK] VirtualHosts activés."

# ---- 5. Créer la configuration VirtualHost avec Reverse Proxy ----
echo "[...] Configuration du VirtualHost Apache pour VISIO-CMR..."

# Check if our config block already exists
if grep -q "VISIO-CMR" "$VHOSTS_CONF" 2>/dev/null; then
    echo "[INFO] Configuration VISIO-CMR déjà présente, mise à jour..."
    # Remove old block
    sed -i '/# === VISIO-CMR START ===/,/# === VISIO-CMR END ===/d' "$VHOSTS_CONF"
fi

cat >> "$VHOSTS_CONF" << 'VHOST_EOF'

# === VISIO-CMR START ===
# Reverse Proxy pour le backend FastAPI de VISIO-CMR
# Les requetes /visio-cmr/api/* sont redirigees vers FastAPI (port 8000)

<IfModule mod_proxy.c>
    ProxyPreserveHost On

    # API REST endpoints
    ProxyPass /visio-cmr/api/ http://127.0.0.1:8000/api/
    ProxyPassReverse /visio-cmr/api/ http://127.0.0.1:8000/api/

    # WebSocket pour la camera mobile
    <IfModule mod_proxy_wstunnel.c>
        ProxyPass /visio-cmr/ws/ ws://127.0.0.1:8000/api/ws/
        ProxyPassReverse /visio-cmr/ws/ ws://127.0.0.1:8000/api/ws/
    </IfModule>
</IfModule>

# Alias pour que /visio-cmr/ serve les fichiers statiques directement depuis htdocs
<Directory "/opt/lampp/htdocs/visio-cmr">
    Options Indexes FollowSymLinks
    AllowOverride All
    Require all granted
</Directory>
# === VISIO-CMR END ===
VHOST_EOF

echo "[OK] VirtualHost configuré."

# ---- 6. Ajouter la même config dans le VirtualHost SSL (port 443) ----
echo "[...] Ajout du reverse proxy dans la config SSL (port 443)..."

if grep -q "VISIO-CMR" "$SSL_CONF" 2>/dev/null; then
    echo "[INFO] Config SSL VISIO-CMR déjà présente, mise à jour..."
    sed -i '/# === VISIO-CMR SSL START ===/,/# === VISIO-CMR SSL END ===/d' "$SSL_CONF"
fi

# Insert before </VirtualHost> closing tag in SSL config
sed -i '/<\/VirtualHost>/i \
# === VISIO-CMR SSL START ===\
ProxyPreserveHost On\
SSLProxyEngine On\
ProxyPass /visio-cmr/api/ http://127.0.0.1:8000/api/\
ProxyPassReverse /visio-cmr/api/ http://127.0.0.1:8000/api/\
ProxyPass /visio-cmr/ws/ ws://127.0.0.1:8000/api/ws/\
ProxyPassReverse /visio-cmr/ws/ ws://127.0.0.1:8000/api/ws/\
# === VISIO-CMR SSL END ===' "$SSL_CONF"

echo "[OK] Configuration SSL ajoutée."

# ---- 7. Ouvrir le port 8000 dans le pare-feu (si UFW est actif) ----
echo "[...] Configuration du pare-feu..."
if command -v ufw &>/dev/null; then
    ufw allow 80/tcp 2>/dev/null || true
    ufw allow 443/tcp 2>/dev/null || true
    ufw allow 8000/tcp 2>/dev/null || true
    echo "[OK] Ports 80, 443 et 8000 autorisés dans UFW."
else
    echo "[INFO] UFW non trouvé, pas de modification du pare-feu."
fi

# ---- 8. Tester la config Apache ----
echo "[...] Vérification de la configuration Apache..."
"$LAMPP_DIR/bin/apachectl" configtest 2>&1
if [ $? -eq 0 ]; then
    echo "[OK] Configuration Apache valide."
else
    echo "[ATTENTION] Des avertissements ont été détectés, mais le serveur devrait fonctionner."
fi

# ---- 9. Redémarrer Apache XAMPP ----
echo "[...] Redémarrage de Apache XAMPP..."
"$LAMPP_DIR/xampp" reloadapache 2>/dev/null || "$LAMPP_DIR/xampp" restartapache 2>/dev/null || true
echo "[OK] Apache XAMPP redémarré."

# ---- 10. Résumé final ----
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "============================================================"
echo "  ✅ INSTALLATION TERMINÉE AVEC SUCCÈS !"
echo "============================================================"
echo ""
echo "  📋 Étapes pour utiliser VISIO-CMR :"
echo ""
echo "  1. Lancez le backend Python :"
echo "     cd $SCRIPT_DIR && python3 app.py"
echo ""
echo "  2. Sur votre ORDINATEUR, ouvrez :"
echo "     http://localhost/visio-cmr/"
echo "     ou https://localhost/visio-cmr/"
echo ""
echo "  3. Sur votre iPHONE / ANDROID (même Wi-Fi), ouvrez :"
echo "     https://$LOCAL_IP/visio-cmr/"
echo ""
echo "  💡 Si Safari affiche un avertissement SSL :"
echo "     → Cliquez sur 'Afficher les détails'"
echo "     → Puis 'Visiter ce site web'"
echo "     → Confirmez avec 'Visiter'"
echo ""
echo "============================================================"
