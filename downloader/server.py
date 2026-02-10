import os
import pathlib
import sys
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp

# Detecta se está rodando empacotado pelo PyInstaller
if getattr(sys, "frozen", False):
    # Quando empacotado, usamos a pasta onde o .exe está
    BASE_DIR = pathlib.Path(sys.executable).resolve().parent
else:
    # Em modo desenvolvimento, usamos a raiz do projeto
    BASE_DIR = pathlib.Path(__file__).resolve().parent.parent

FRONT_DIR = BASE_DIR / "front"

app = Flask(__name__)
CORS(app)  # Libera chamadas do front (http://localhost, file:// etc.)

# Estado simples de progresso (um "job" por vez, suficiente para uso local)
progress_state = {
    "status": "idle",          # idle | downloading | done | error
    "percent": 0,              # 0–100 (geral)
    "current_video": None,     # URL atual
    "current_video_percent": 0,
    "index": 0,                # índice do vídeo atual (1-based)
    "total": 0,                # total de vídeos
    "message": "",
}


@app.get("/")
def serve_front():
    """Serve o index.html do front como página principal."""
    return send_from_directory(FRONT_DIR, "index.html")


@app.get("/api/progress")
def get_progress():
    """Retorna o estado atual de progresso do download."""
    return jsonify(progress_state)


@app.post("/api/download")
def download_videos():
    """
    Endpoint que recebe uma lista de URLs do YouTube e faz o download
    usando yt_dlp, salvando na pasta ./downloads.
    Também atualiza um estado de progresso que o front pode consultar.
    """
    data = request.get_json(silent=True) or {}
    urls = data.get("urls") or []
    audio_only = bool(data.get("audioOnly"))

    if not isinstance(urls, list) or not urls:
        return jsonify({"error": "Envie um JSON com o campo 'urls' como lista e pelo menos 1 URL."}), 400

    # Garante que a pasta de downloads exista
    # Usa a pasta padrão "Downloads" do usuário no Windows
    user_home = os.path.expanduser("~")
    downloads_dir = os.path.join(user_home, "Downloads")
    os.makedirs(downloads_dir, exist_ok=True)

    total_videos = len(urls)

    # Reset e inicia progresso
    progress_state.update(
        {
            "status": "downloading",
            "percent": 0,
            "current_video": None,
            "current_video_percent": 0,
            "index": 0,
            "total": total_videos,
            "message": f"Iniciando download de {total_videos} vídeo(s)...",
        }
    )

    def make_hook(video_index: int, total: int, url: str):
        """Cria um hook de progresso para um vídeo específico."""

        def hook(d):
            if d.get("status") == "downloading":
                downloaded = d.get("downloaded_bytes") or 0
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

                if total_bytes > 0:
                    file_percent = int(downloaded * 100 / total_bytes)
                else:
                    file_percent = 0

                # Progresso geral: vídeos anteriores completos + parte do atual
                overall = ((video_index - 1) + file_percent / 100.0) / total
                overall_percent = int(overall * 100)

                progress_state.update(
                    {
                        "status": "downloading",
                        "percent": overall_percent,
                        "current_video": url,
                        "current_video_percent": file_percent,
                        "index": video_index,
                        "total": total,
                        "message": f"Baixando vídeo {video_index}/{total}",
                    }
                )

        return hook

    try:
        # Usamos uma instância de YoutubeDL por vídeo para poder trocar o hook
        for idx, url in enumerate(urls, start=1):
            mode_label = "áudio" if audio_only else "vídeo"
            app.logger.info(f"Baixando {mode_label} ({idx}/{total_videos}): {url}")

            # Configurações de download
            # Se audio_only=True, baixa apenas o áudio e converte para MP3.
            if audio_only:
                ydl_opts = {
                    "outtmpl": os.path.join(downloads_dir, "%(title)s.%(ext)s"),
                    "noplaylist": True,
                    "format": "bestaudio/best",
                    "skip_download": False,
                    "progress_hooks": [make_hook(idx, total_videos, url)],
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }
                    ],
                }
            else:
                ydl_opts = {
                    # Salva fora da pasta do projeto, para evitar reload do Live Server
                    "outtmpl": os.path.join(downloads_dir, "%(title)s.%(ext)s"),
                    "noplaylist": True,
                    "format": "bestvideo+bestaudio/best",
                    "merge_output_format": "mp4",
                    "skip_download": False,
                    "progress_hooks": [make_hook(idx, total_videos, url)],
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        progress_state.update(
            {
                "status": "done",
                "percent": 100,
                "current_video_percent": 100,
                "message": f"Downloads concluídos para {total_videos} item(ns).",
            }
        )

        return jsonify(
            {
                "status": "ok",
                "message": f"Downloads concluídos para {total_videos} item(ns).",
                "count": total_videos,
            }
        )
    except Exception as e:
        app.logger.exception("Erro ao baixar vídeos.")
        progress_state.update(
            {
                "status": "error",
                "message": f"Erro ao baixar vídeos: {e}",
            }
        )
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Rode com: python server.py
    app.run(host="0.0.0.0", port=5000, debug=True)
