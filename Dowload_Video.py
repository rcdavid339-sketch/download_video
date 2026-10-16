import ctypes
import logging
import os
import queue
import shutil
import sys
import threading
from pathlib import Path
from urllib.parse import urlparse

import customtkinter as ctk
from tkinter import messagebox
import yt_dlp



def resource_path(relative_path):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative_path


TOOLS_DIR = resource_path("tools")
DOWNLOAD_DIR = Path.home() / "Downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = DOWNLOAD_DIR / "DownloadVideo.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    encoding="utf-8"
)


os.environ["PATH"] = (
    str(TOOLS_DIR)
    + os.pathsep
    + os.environ.get("PATH", "")
)


ffmpeg_inclus = TOOLS_DIR / "ffmpeg.exe"

ffmpeg_local = (
    Path.home()
    / "AppData"
    / "Local"
    / "Programs"
    / "FFmpeg"
    / "bin"
    / "ffmpeg.exe"
)

if ffmpeg_inclus.is_file():
    ffmpeg_path = str(TOOLS_DIR)

elif ffmpeg_local.is_file():
    ffmpeg_path = str(ffmpeg_local.parent)

else:
    ffmpeg_path = shutil.which("ffmpeg")



ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


evenements = queue.Queue()


def format_size(bytes_size):
    for unit in ("o", "Ko", "Mo", "Go"):
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024

    return f"{bytes_size:.1f} To"


def url_youtube_valide(value):
    try:
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()

        return (
            parsed.scheme in ("http", "https")
            and (
                host == "youtube.com"
                or host.endswith(".youtube.com")
                or host == "youtu.be"
            )
        )

    except ValueError:
        return False


def telecharger_video(url, qualite):


    try:
        if not ffmpeg_path:
            raise RuntimeError(
                "FFmpeg introuvable. "
                "Ajoutez ffmpeg.exe et ffprobe.exe dans tools."
            )

        if not shutil.which("deno"):
            raise RuntimeError(
                "Deno introuvable. Ajoutez deno.exe dans tools."
            )

        evenements.put((
            "status",
            "Analyse de la vidéo...",
            "#facc15"
        ))

        def progress_hook(info):
            etat = info.get("status")

            if etat == "downloading":
                total = (
                    info.get("total_bytes")
                    or info.get("total_bytes_estimate")
                    or 0
                )

                downloaded = info.get("downloaded_bytes") or 0

                if total > 0:
                    value = min(1.0, downloaded / total)

                    texte = (
                        f"{format_size(downloaded)} / "
                        f"{format_size(total)} "
                        f"({value * 100:.0f} %) "
                        "- téléchargement du flux"
                    )

                    evenements.put((
                        "progress",
                        value,
                        texte
                    ))

            elif etat == "finished":
                evenements.put((
                    "status",
                    "Flux reçu, traitement en cours...",
                    "#facc15"
                ))


        options = {
            "format": (
                f"bv[vcodec^=avc1][height<={qualite}]+ba[ext=m4a]/"
                f"bv[height<={qualite}]+ba/b"
            ),

            "outtmpl": str(
                DOWNLOAD_DIR / "%(title)s [%(id)s].%(ext)s"
            ),

            "merge_output_format": "mp4",
            "ffmpeg_location": ffmpeg_path,
            "progress_hooks": [progress_hook],

            "quiet": True,
            "no_warnings": False,

            "socket_timeout": 60,
            "retries": 10,
            "fragment_retries": 10,

            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            result = ydl.download([url])

        if result != 0:
            raise RuntimeError(
                f"yt-dlp a terminé avec le code {result}."
            )

        evenements.put((
            "success",
            "Téléchargement terminé. "
            "Vérifiez votre dossier Downloads."
        ))

        logging.info(
            "Téléchargement terminé : %s", url
        )

    except Exception as exc:
        logging.exception("Échec du téléchargement")

        evenements.put((
            "error",
            f"Téléchargement impossible : {exc}"
        ))

    finally:
        evenements.put(("ready",))


def lancer_telechargement():
    url = entree_url.get().strip()
    qualite = combo_qualite.get()

    if not url_youtube_valide(url):
        messagebox.showwarning(
            "Lien invalide",
            "Veuillez entrer une URL YouTube valide."
        )
        return

    bouton_download.configure(
        state="disabled",
        text="En cours..."
    )

    progress_bar.set(0)
    progress_bar.pack(
        pady=(0, 5),
        padx=25,
        fill="x"
    )

    label_status.configure(
        text="Préparation...",
        text_color="#facc15"
    )

    threading.Thread(
        target=telecharger_video,
        args=(url, qualite),
        daemon=True
    ).start()


def traiter_evenements():
    """Traite les événements dans le thread principal Tkinter."""

    try:
        while True:
            evenement = evenements.get_nowait()
            action = evenement[0]

            if action == "progress":
                _, progression, texte = evenement

                progress_bar.set(progression)

                label_status.configure(
                    text=texte,
                    text_color="#60a5fa"
                )

            elif action == "status":
                _, texte, couleur = evenement

                label_status.configure(
                    text=texte,
                    text_color=couleur
                )

            elif action == "success":
                progress_bar.set(1.0)

                label_status.configure(
                    text=evenement[1],
                    text_color="#4ade80"
                )

            elif action == "error":
                label_status.configure(
                    text="Erreur : consultez DownloadVideo.log",
                    text_color="#f87171"
                )

                messagebox.showerror(
                    "Échec du téléchargement",
                    evenement[1]
                )

            elif action == "ready":
                bouton_download.configure(
                    state="normal",
                    text="Download"
                )

                progress_bar.pack_forget()

    except queue.Empty:
        pass

    fenetre.after(100, traiter_evenements)



if sys.platform == "win32":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "mon_application.video_downloader.beta"
        )
    except OSError:
        pass



fenetre = ctk.CTk()

icon_path = resource_path("assets/icon.ico")

if icon_path.is_file():
    fenetre.iconbitmap(str(icon_path))

fenetre.title("Download video")
fenetre.geometry("645x450")
fenetre.resizable(False, False)



titre_label = ctk.CTkLabel(
    fenetre,
    text="Download video",
    font=ctk.CTkFont(
        size=24,
        weight="bold"
    )
)

titre_label.pack(pady=(20, 5))



sous_titre = ctk.CTkLabel(
    fenetre,
    text="100% local version bêta",
    font=ctk.CTkFont(size=13),
    text_color="#FFFFFF"
)

sous_titre.pack(pady=(0, 10))



cadre = ctk.CTkFrame(
    fenetre,
    corner_radius=12
)

cadre.pack(
    pady=10,
    padx=25,
    fill="both",
    expand=True
)



label_url = ctk.CTkLabel(
    cadre,
    text="Lien de la vidéo",
    font=ctk.CTkFont(
        size=13,
        weight="bold"
    )
)

label_url.pack(
    pady=(15, 3),
    anchor="w",
    padx=20
)



entree_url = ctk.CTkEntry(
    cadre,
    width=420,
    height=38,
    placeholder_text="https://www.youtube.com/watch?v=..."
)

entree_url.pack(
    pady=(0, 10),
    padx=20
)



frame_qualite = ctk.CTkFrame(
    cadre,
    fg_color="transparent"
)

frame_qualite.pack(
    pady=(0, 15),
    padx=20,
    fill="x"
)



label_qualite = ctk.CTkLabel(
    frame_qualite,
    text="Quality :",
    font=ctk.CTkFont(
        size=13,
        weight="bold"
    )
)

label_qualite.pack(side="left")



combo_qualite = ctk.CTkComboBox(
    frame_qualite,
    values=["720", "1080", "1440"],
    state="readonly",
    width=100
)

combo_qualite.set("1080")

combo_qualite.pack(
    side="left",
    padx=10
)


label_qualite_info = ctk.CTkLabel(
    frame_qualite,
    text="pixels",
    font=ctk.CTkFont(size=12),
    text_color="#94a3b8"
)

label_qualite_info.pack(side="left")



label_status = ctk.CTkLabel(
    fenetre,
    text="Prêt pour un téléchargement",
    font=ctk.CTkFont(size=12),
    text_color="#FFFFFF"
)

label_status.pack(pady=(5, 0))



progress_bar = ctk.CTkProgressBar(
    fenetre,
    mode="determinate"
)

progress_bar.set(0)



bouton_download = ctk.CTkButton(
    fenetre,
    text="Download",
    command=lancer_telechargement,
    height=45,
    font=ctk.CTkFont(
        size=15,
        weight="bold"
    ),
    corner_radius=10
)

bouton_download.pack(
    pady=(8, 20),
    padx=25,
    fill="x"
)



fenetre.after(100, traiter_evenements)


fenetre.mainloop()
