import tkinter as tk
from tkinter import messagebox, ttk
import os
import yt_dlp
import pygame
import random
import threading
import time

pygame.mixer.init()

def download_song(url, output_path, download_progress):
    def progress_hook(d):
        if d['status'] == 'finished':
            download_progress.set("Download complete")
        elif d['status'] == 'downloading':
            progress = d['_percent_str']
            download_progress.set(f"Downloading: {progress}")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'progress_hooks': [progress_hook],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def search_song(query):
    ydl_opts = {
        'quiet': True,
        'default_search': 'ytsearch10',
        'skip_download': True,
        'noplaylist': True,
        'extract_flat': 'in_playlist',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(query, download=False)
        return result['entries']

class SpotifyCloneApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Music Player 🎵")
        self.root.geometry("800x800")

        self.apply_tokyo_night_theme()

        self.downloading = False
        self.download_progress = tk.StringVar()
        self.playlist = []
        self.current_song_index = None
        self.paused = False
        self.updating_timeline = False
        self.scrubbing = False
        self.results = [] 

        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=1)
        for i in range(11):
            self.root.rowconfigure(i, weight=1)


        self.search_label = ttk.Label(root, text="Search for a song:")
        self.search_label.grid(row=0, column=0, padx=10, pady=10, sticky="W")

        self.search_entry = ttk.Entry(root, width=50)
        self.search_entry.grid(row=0, column=1, padx=10, pady=10, sticky="W")

        self.search_button = ttk.Button(root, text="Search", command=self.search_song)
        self.search_button.grid(row=0, column=2, padx=10, pady=10, sticky="W")

        self.result_listbox = tk.Listbox(root, width=80, height=10, bg="#1a1b26", fg="#c0caf5",
                                         selectbackground="#414868", font=('Helvetica', 12))
        self.result_listbox.grid(row=1, column=0, columnspan=3, padx=10, pady=10)

        self.download_button = ttk.Button(root, text="Download", command=self.download_selected_song)
        self.download_button.grid(row=2, column=0, columnspan=3, padx=10, pady=10)

        self.download_progress_label = ttk.Label(root, textvariable=self.download_progress)
        self.download_progress_label.grid(row=3, column=0, columnspan=3, padx=10, pady=10)

        self.playlist_label = ttk.Label(root, text="Playlist")
        self.playlist_label.grid(row=4, column=0, padx=10, pady=10, sticky="W")

        self.playlist_listbox = tk.Listbox(root, width=80, height=10, bg="#1a1b26", fg="#c0caf5",
                                         selectbackground="#414868", font=('Helvetica', 12))
        self.playlist_listbox.grid(row=5, column=0, columnspan=3, padx=10, pady=10)

        self.current_song_label = ttk.Label(root, text="No song playing", font=('Helvetica', 14, 'bold'))
        self.current_song_label.grid(row=6, column=0, columnspan=3, padx=10, pady=10)

        self.timeline = ttk.Scale(root, from_=0, to=100, orient=tk.HORIZONTAL, length=400)
        self.timeline.grid(row=7, column=0, columnspan=3, padx=10, pady=10)
        self.timeline.bind("<ButtonRelease-1>", self.seek_song)
        self.timeline.bind("<B1-Motion>", self.start_scrubbing)
        self.timeline.bind("<ButtonRelease-1>", self.stop_scrubbing)

        self.controls_frame = ttk.Frame(root)
        self.controls_frame.grid(row=8, column=0, columnspan=3, pady=10)

        self.prev_button = ttk.Button(self.controls_frame, text="⏮️", command=self.prev_song, style="Emoji.TButton")
        self.prev_button.grid(row=0, column=0, padx=5)

        self.play_button = ttk.Button(self.controls_frame, text="▶️", command=self.play_selected_song, style="Emoji.TButton")
        self.play_button.grid(row=0, column=1, padx=5)

        self.pause_button = ttk.Button(self.controls_frame, text="⏸️", command=self.pause_song, style="Emoji.TButton")
        self.pause_button.grid(row=0, column=2, padx=5)

        self.next_button = ttk.Button(self.controls_frame, text="⏭️", command=self.next_song, style="Emoji.TButton")
        self.next_button.grid(row=0, column=3, padx=5)

        self.volume_scale = ttk.Scale(root, from_=0, to=1, length=150, command=self.set_volume)
        self.volume_scale.grid(row=9, column=0, columnspan=3, padx=10, pady=10)

        self.remove_button = ttk.Button(root, text="Remove", command=self.remove_selected_song)
        self.remove_button.grid(row=10, column=0, padx=10, pady=10)

        self.shuffle_button = ttk.Button(root, text="Shuffle", command=self.shuffle_playlist)
        self.shuffle_button.grid(row=10, column=1, padx=10, pady=10)

        self.sort_button = ttk.Button(root, text="Sort", command=self.sort_playlist)
        self.sort_button.grid(row=10, column=2, padx=10, pady=10)

        self.load_existing_downloads()

        self.root.bind('<<NextSong>>', self.handle_next_song)

        threading.Thread(target=self.check_song_end, daemon=True).start()

    def apply_tokyo_night_theme(self):
        self.root.configure(bg="#1a1b26")
        self.root.option_add("*TButton", {"background": "#414868", "foreground": "#c0caf5", "font": ('Helvetica', 12)})
        self.root.option_add("*TLabel", {"background": "#1a1b26", "foreground": "#c0caf5", "font": ('Helvetica', 12)})
        self.root.option_add("*TScale", {"background": "#1a1b26", "foreground": "#c0caf5"})
        self.root.option_add("*TFrame", {"background": "#1a1b26"})
        style = ttk.Style()
        style.configure("Emoji.TButton", font=('Segoe UI Emoji', 12))

    def search_song(self):
        query = self.search_entry.get()
        if not query:
            messagebox.showwarning("Warning", "Please enter a search query!")
            return
        self.results = search_song(query)
        self.result_listbox.delete(0, tk.END)
        for result in self.results:
            self.result_listbox.insert(tk.END, result['title'])

    def download_selected_song(self):
        selected_index = self.result_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("Warning", "Select a song to download!")
            return

        selected_result = self.results[selected_index[0]]
        url = selected_result['url']
        title = selected_result['title']

        download_path = os.path.join(os.getcwd(), 'downloads')
        os.makedirs(download_path, exist_ok=True)

        threading.Thread(target=self.download_song_thread, args=(url, download_path, title)).start()

    def download_song_thread(self, url, download_path, title):
        if self.downloading:
            messagebox.showwarning("Warning", "Another download is already in progress!")
            return
        self.downloading = True
        self.download_progress.set("Starting download...")
        download_song(url, download_path, self.download_progress)
        self.downloading = False
        self.download_progress.set("")

        self.playlist.append(os.path.join(download_path, f"{title}.mp3"))
        self.update_playlist_display()
        messagebox.showinfo("Info", f"Downloaded: {title}")

    def update_playlist_display(self):
        self.playlist_listbox.delete(0, tk.END)
        for song in self.playlist:
            self.playlist_listbox.insert(tk.END, os.path.basename(song))

    def play_selected_song(self):
        selected_index = self.playlist_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("Warning", "Select a song to play!")
            return

        self.current_song_index = selected_index[0]
        self.play_song_at_index(self.current_song_index)

    def shuffle_playlist(self):
        random.shuffle(self.playlist)
        self.update_playlist_display()

    def prev_song(self):
        if self.current_song_index is None:
            return
        self.current_song_index = (self.current_song_index - 1) % len(self.playlist)
        self.play_song_at_index(self.current_song_index)

    def sort_playlist(self):
        self.playlist.sort(key=lambda s: os.path.basename(s).lower())
        self.update_playlist_display()

    def load_existing_downloads(self):
        download_path = os.path.join(os.getcwd(), 'downloads')
        if os.path.exists(download_path):
            for filename in os.listdir(download_path):
                if filename.endswith('.mp3'):
                    self.playlist.append(os.path.join(download_path, filename))
            self.update_playlist_display()

    def pause_song(self):
        if self.paused:
            pygame.mixer.music.unpause()
        else:
            pygame.mixer.music.pause()
        self.paused = not self.paused

    def next_song(self):
        if self.current_song_index is None:
            return
        self.current_song_index = (self.current_song_index + 1) % len(self.playlist)
        self.play_song_at_index(self.current_song_index)

    def play_song_at_index(self, index):
        if index is None:
            return

        selected_song = self.playlist[index]
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        pygame.mixer.music.load(selected_song)
        pygame.mixer.music.play()
        self.current_song_label.config(text=f"Playing: {os.path.basename(selected_song)}")
        self.paused = False

        self.timeline.config(to=self.get_song_length(selected_song))
        self.start_updating_timeline()

    def set_volume(self, volume):
        pygame.mixer.music.set_volume(float(volume))

    def get_song_length(self, song):
        try:
            audio = pygame.mixer.Sound(song)
            return audio.get_length()
        except Exception as e:
            return 100  

    def update_timeline(self):
        while self.updating_timeline:
            if pygame.mixer.music.get_busy() and not self.paused and not self.scrubbing:
                current_pos = pygame.mixer.music.get_pos() / 1000  # get_pos returns milliseconds
                self.timeline.set(current_pos)
            time.sleep(0.5)

    def start_updating_timeline(self):
        self.updating_timeline = True
        threading.Thread(target=self.update_timeline, daemon=True).start()

    def stop_updating_timeline(self):
        self.updating_timeline = False

    def seek_song(self, event):
        seek_pos = self.timeline.get()
        pygame.mixer.music.set_pos(seek_pos)
        self.scrubbing = False

    def start_scrubbing(self, event):
        self.scrubbing = True

    def stop_scrubbing(self, event):
        self.scrubbing = False
        self.seek_song(event)

    def remove_selected_song(self):
        selected_index = self.playlist_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("Warning", "Select a song to remove!")
            return
        song_index = selected_index[0]
        song_filename = self.playlist[song_index]
        del self.playlist[song_index]
        self.update_playlist_display()
        try:
            os.remove(os.path.join(os.getcwd(), 'downloads', song_filename))
            messagebox.showinfo("Info", f"Song '{song_filename}' removed from playlist and deleted from downloads folder.")
        except FileNotFoundError:
            messagebox.showerror("Error", f"File '{song_filename}' not found in downloads folder.")

    def check_song_end(self):
        while True:
            if pygame.mixer.music.get_busy():
                time.sleep(1)
            else:
                self.root.event_generate('<<NextSong>>', when='tail')
                time.sleep(1)

    def handle_next_song(self, event):
        self.next_song()

if __name__ == "__main__":
    root = tk.Tk()
    app = SpotifyCloneApp(root)
    root.mainloop()
