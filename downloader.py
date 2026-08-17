import os
import urllib.request
import sys

def progress_hook(count, block_size, total_size):
    """Callback to print download progress."""
    if total_size <= 0:
        return
    percent = int(count * block_size * 100 / total_size)
    percent = min(100, percent)
    sys.stdout.write(f"\rTéléchargement... {percent}%")
    sys.stdout.flush()

def download_model(url, filename, output_dir="models"):
    """Downloads a file from a URL to the specified directory."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Dossier '{output_dir}' créé.")
        
    dest_path = os.path.join(output_dir, filename)
    
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 100000:
        print(f"[OK] Le modèle '{filename}' existe déjà à l'emplacement : {dest_path}")
        return dest_path
        
    print(f"\nTéléchargement de {filename} depuis {url}...")
    try:
        urllib.request.urlretrieve(url, dest_path, reporthook=progress_hook)
        print(f"\n[OK] Téléchargé avec succès : {dest_path}")
    except Exception as e:
        print(f"\n[ERREUR] Impossible de télécharger {filename} : {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
            
    return dest_path

if __name__ == "__main__":
    print("=== VISIO-CMR : Initialisation des modèles d'amélioration IA ===")
    
    # Models to download
    models = [
        {
            "url": "https://github.com/fannymonori/TF-ESPCN/raw/master/export/ESPCN_x4.pb",
            "filename": "ESPCN_x4.pb"
        },
        {
            "url": "https://github.com/Saafke/FSRCNN_Tensorflow/raw/master/models/FSRCNN_x2.pb",
            "filename": "FSRCNN_x2.pb"
        }
    ]
    
    for m in models:
        download_model(m["url"], m["filename"])
        
    print("\nInitialisation terminée. Vous pouvez lancer le serveur avec 'python3 app.py'.")
