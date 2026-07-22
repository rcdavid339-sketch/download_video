import ctypes
import customtkinter as ctk
from tkinter import messagebox
import threading
import os
import requests
import re
import yt_dlp
import sys
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(__file__)


chemin_ressource = os.path.join(base_path, '')
ffmpeg_path = os.path.join(
    os.path.expanduser("~"),
    "AppData",
    "Local",
    "Programs",
    "FFmpeg",
    "bin"
)
os.environ["PATH"] += ";" + ffmpeg_path
ctk.set_appearance_mode("blue")
ctk.set_default_color_theme("blue")



def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def download_file(url, filename, progress_callback=None):

    filename = re.sub(r'[<>:"/\\|?*]', '', filename)

    if not filename:
        filename = "video.mp4"

    filepath = os.path.join(os.getcwd(), filename)

    try:
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(filepath, 'wb') as f:

            for chunk in response.iter_content(chunk_size=8192):

                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if progress_callback and total_size > 0:
                        progress = downloaded / total_size
                        progress_callback(progress, downloaded, total_size)

        return filepath

    except Exception as e:
        print("Error 259+0 :", e)
        if os.path.exists(filepath):
            os.remove(filepath)

        raise e


def format_size(bytes_size):

    for unit in ['o', 'Ko', 'Mo', 'Go']:

        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"

        bytes_size /= 1024

    return f"{bytes_size:.1f} To"


def lancer_telechargement():

    url = entree_url.get().strip()
    qualite = combo_qualite.get()

    if not url:
        messagebox.showwarning(
            "Erreur",
            "Veuillez entrer une URL valide."
        )
        return

    if "youtube.com" not in url and "youtu.be" not in url:
        messagebox.showwarning(
            "Erreur",
            "Veuillez entrer un lien YouTube valide s'il-vous-plait."
        )
        return

    threading.Thread(
        target=telecharger_video,
        args=(url, qualite),
        daemon=True
    ).start()


def telecharger_video(url, qualite):

    bouton_download.configure(
        state="disabled",
        text=" En cours..."
    )

    progress_bar.set(0)

    progress_bar.pack(
        pady=(0, 5),
        padx=25,
        fill="x"
    )

    label_status.configure(
        text="Analyse de la vidéo...",
        text_color="#facc15"
    )

    def progress_hook(d):

        if d['status'] == 'downloading':

            total = d.get('total_bytes', 0) or d.get(
                'total_bytes_estimate',
                0
            )

            downloaded = d.get('downloaded_bytes', 0)

            if total > 0:

                progress = downloaded / total

                progress_bar.set(progress)

                label_status.configure(
                    text=f"{format_size(downloaded)} / "
                         f"{format_size(total)} "
                         f"({int(progress * 100)}%)",
                    text_color="#60a5fa"
                )

        elif d['status'] == 'finished':

            progress_bar.set(1.0)

            label_status.configure(
                text="Téléchargement terminé",
                text_color="#FFFFFF"
            )

    dossier_telechargement = os.path.join(
        os.path.expanduser("~"),
        "Downloads"
    )

    print("Téléchargement vers :", dossier_telechargement)

    print("FFmpeg path:", ffmpeg_path)

    print("Existe :", os.path.exists(ffmpeg_path))

    ydl_opts = {
        'format': f'bv*[height<={qualite}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best',
        'outtmpl': os.path.join(
            dossier_telechargement,
            '%(title)s.%(ext)s'
        ),
        'merge_output_format': 'mp4',
        'progress_hooks': [progress_hook],
        'quiet': False,
        'ffmpeg_location': ffmpeg_path,
        'socket_timeout': 60,
        'retries': 10,
        'fragment_retries': 10,
        'concurrent_fragment_downloads': 10,
        'throttledratelimit': 0,
    }

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    except Exception as e:
        print("Error 259 :", e)
        ydl_opts['format'] = (
            f'bestvideo[height<={qualite}]'
            f'+bestaudio/best'
        )

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    finally:
        bouton_download.configure(
            state="normal",
            text="Download"
        )
        progress_bar.pack_forget()
        label_status.configure(text="Prêt pour un nouveau téléchargement", text_color="#94a3b8")

        progress_bar.pack_forget()

myappid = 'mon_application.video_downloader.beta'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

fenetre = ctk.CTk()

fenetre.iconbitmap(resource_path("assets/icon.ico"))

fenetre.title("Download video")

fenetre.geometry("645x450")

fenetre.resizable(False, False)

titre_label = ctk.CTkLabel(
    fenetre,
    text="Download video",
    font=ctk.CTkFont(size=24, weight="bold")
)

titre_label.pack(pady=(20, 5))

sous_titre = ctk.CTkLabel(
    fenetre,
    text="100% Local mais en beta pour le moment..., CTRL+C pour copie et CTRL+V pour coller URL",
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
    text=" Lien de la vidéo",
    font=ctk.CTkFont(size=13, weight="bold")
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
    text=" Quality :",
    font=ctk.CTkFont(size=13, weight="bold")
)

label_qualite.pack(side="left")

combo_qualite = ctk.CTkComboBox(
    frame_qualite,
    values=["720", "1080", "1440"],
    state="readonly",
    width=100
)

combo_qualite.pack(
    side="left",
    padx=10
)

label_qualite_info = ctk.CTkLabel(
    frame_qualite,
    text="pixels",
    font=ctk.CTkFont(size=12),
    text_color="#64748b"
)

label_qualite_info.pack(side="left")

label_status = ctk.CTkLabel(
    fenetre,
    text="Pour instant, c'est en beta!",
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
    text=" Download",
    command=lancer_telechargement,
    height=45,
    font=ctk.CTkFont(size=15, weight="bold"),
    corner_radius=10
)

bouton_download.pack(
    pady=(8, 20),
    padx=25,
    fill="x"
)

fenetre.mainloop()
