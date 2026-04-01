import customtkinter as ctk
import cv2
from PIL import Image
import pygame
import os
import tkinter as tk
from ffpyplayer.player import MediaPlayer

class MediaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("プロ仕様！マルチメディアプレイヤー")
        self.geometry("1000x800")

        pygame.mixer.init()

        # --- 1. 制御変数の初期化 ---
        self.cap = None
        self.audio_player = None
        self.video_running = False
        self.is_paused = False
        self.current_volume = 0.5
        self.total_frames = 0
        self.fps = 30
        self.music_start_time = 0
        self.playlist_paths = []

        # --- 2. UIレイアウトの作成 ---
        # メインコンテナ（左右分割用）
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(expand=True, fill="both", padx=10, pady=10)

        # 左側：表示エリア
        self.display_container = ctk.CTkFrame(self.main_container, fg_color="black")
        self.display_container.pack(side="left", expand=True, fill="both")

        self.video_label = ctk.CTkLabel(self.display_container, text="", fg_color="black")
        self.video_label.place(relx=0.5, rely=0.5, anchor="center")

        # 右側：プレイリストエリア
        self.playlist_frame = ctk.CTkFrame(self.main_container, width=250)
        self.playlist_frame.pack(side="right", fill="y", padx=(10, 0))
        
        ctk.CTkLabel(self.playlist_frame, text="プレイリスト", font=("Arial", 16, "bold")).pack(pady=5)

        self.listbox = tk.Listbox(self.playlist_frame, bg="#2b2b2b", fg="white", 
                                  selectbackground="#1f538d", borderwidth=0, 
                                  highlightthickness=0, font=("Arial", 10))
        self.listbox.pack(expand=True, fill="both", padx=5, pady=5)
        self.listbox.bind("<Double-Button-1>", lambda e: self.play_selected_from_list())

        # プレイリスト操作ボタン
        self.playlist_btn_frame = ctk.CTkFrame(self.playlist_frame, fg_color="transparent")
        self.playlist_btn_frame.pack(fill="x", padx=5)

        ctk.CTkButton(self.playlist_btn_frame, text="選択削除", fg_color="#a11d1d", 
                      hover_color="#7a1616", command=self.delete_selected, width=100).pack(side="left", expand=True, padx=2, pady=5)
        ctk.CTkButton(self.playlist_btn_frame, text="全削除", command=self.clear_playlist, width=100).pack(side="right", expand=True, padx=2, pady=5)

        # --- 下部コントロールエリア ---
        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.pack(fill="x", padx=20, pady=10)

        # シークバー
        self.seek_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.seek_frame.pack(fill="x", padx=10, pady=5)

        self.seek_slider = ctk.CTkSlider(self.seek_frame, from_=0, to=100, command=self.seek_media)
        self.seek_slider.set(0)
        self.seek_slider.pack(side="left", expand=True, fill="x", padx=(0, 10))

        self.time_label = ctk.CTkLabel(self.seek_frame, text="00:00 / 00:00")
        self.time_label.pack(side="right")

        # 操作ボタン
        self.btn_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.btn_frame.pack(pady=5)
        
        ctk.CTkButton(self.btn_frame, text="ファイル追加", command=self.load_files).grid(row=0, column=0, padx=10)
        self.btn_play_pause = ctk.CTkButton(self.btn_frame, text="再生", command=self.toggle_play_pause)
        self.btn_play_pause.grid(row=0, column=1, padx=10)
        ctk.CTkButton(self.btn_frame, text="停止", command=self.stop_media).grid(row=0, column=2, padx=10)

        # 音量
        self.volume_slider = ctk.CTkSlider(self.bottom_frame, from_=0, to=1, command=self.change_volume, width=200)
        self.volume_slider.set(self.current_volume)
        self.volume_slider.pack(pady=5)

        self.status_label = ctk.CTkLabel(self, text="プレイリストにファイルを追加してください")
        self.status_label.pack(pady=5)

        # ウィンドウ監視
        self.display_container.bind("<Configure>", lambda e: self.on_resize())

    # --- ヘルパー関数 ---
    def format_time(self, seconds):
        mins, secs = divmod(int(max(0, seconds)), 60)
        return f"{mins:02d}:{secs:02d}"

    def on_resize(self):
        pass

    # --- メディア制御 ---
    def load_files(self):
        file_paths = ctk.filedialog.askopenfilenames(filetypes=[("Media", "*.mp4 *.mp3 *.wav")])
        if file_paths:
            for path in file_paths:
                if path not in self.playlist_paths:
                    self.playlist_paths.append(path)
                    self.listbox.insert("end", os.path.basename(path))
            if not hasattr(self, 'current_file'):
                self.listbox.selection_set(0)
                self.play_selected_from_list()

    def play_selected_from_list(self):
        selection = self.listbox.curselection()
        if not selection: return
        
        index = selection[0]
        file_path = self.playlist_paths[index]
        self.stop_media()
        self.current_file = file_path
        self.status_label.configure(text=f"再生中: {os.path.basename(file_path)}")

        if file_path.endswith(".mp4"):
            self.cap = cv2.VideoCapture(file_path)
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
            self.seek_slider.configure(to=self.total_frames)
            self.audio_player = MediaPlayer(file_path)
            self.audio_player.set_volume(self.current_volume)
        else:
            sound = pygame.mixer.Sound(file_path)
            self.total_music_sec = sound.get_length()
            self.seek_slider.configure(to=self.total_music_sec)
        
        self.start_playback()

    def toggle_play_pause(self):
        if not hasattr(self, 'current_file'): return
        if not self.video_running and not self.is_paused: self.start_playback()
        elif self.is_paused: self.resume_playback()
        else: self.pause_playback()

    def start_playback(self):
        if not hasattr(self, 'current_file'): return
        self.video_running, self.is_paused = True, False
        self.btn_play_pause.configure(text="一時停止")

        if self.current_file.endswith(".mp4"):
            if self.audio_player: self.audio_player.set_pause(False)
            self.update_video()
        else:
            self.video_label.configure(image="", text="音楽再生中")
            pygame.mixer.music.load(self.current_file)
            pygame.mixer.music.play(start=self.music_start_time)
            self.update_music_time()

    def pause_playback(self):
        self.is_paused = True
        self.btn_play_pause.configure(text="再生")
        if self.current_file.endswith(".mp4"):
            if self.audio_player: self.audio_player.set_pause(True)
        else:
            pygame.mixer.music.pause()

    def resume_playback(self):
        self.is_paused = False
        self.btn_play_pause.configure(text="一時停止")
        if self.current_file.endswith(".mp4"):
            if self.audio_player: self.audio_player.set_pause(False)
            self.update_video()
        else:
            pygame.mixer.music.unpause()
            self.update_music_time()

    def stop_media(self):
        self.video_running, self.is_paused = False, False
        self.music_start_time = 0
        self.btn_play_pause.configure(text="再生")
        pygame.mixer.music.stop()
        if self.audio_player:
            try: self.audio_player.close_player()
            except: pass
            self.audio_player = None
        if self.cap:
            self.cap.release()
            self.cap = None
        try:
            self.video_label.configure(image="", text="停止中")
            self.video_label.image = None
        except: pass
        self.time_label.configure(text="00:00 / 00:00")
        self.seek_slider.set(0)

    # --- 更新ループ ---
    def update_video(self):
        if self.video_running and not self.is_paused and self.cap:
            _, val = self.audio_player.get_frame() if self.audio_player else (None, 0)
            if val < -0.01:
                self.cap.grab()
                self.after(1, self.update_video)
                return

            ret, frame = self.cap.read()
            if ret:
                cw, ch = self.display_container.winfo_width(), self.display_container.winfo_height()
                vh, vw = frame.shape[:2]
                ratio = min(cw/vw, ch/vh)
                nw, nh = max(1, int(vw*ratio)), max(1, int(vh*ratio))

                frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_NEAREST)
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                ctk_img = ctk.CTkImage(img, img, size=(nw, nh))
                self.video_label.configure(image=ctk_img, text="")
                self.video_label.image = ctk_img

                cur_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                if cur_frame % 10 == 0:
                    self.time_label.configure(text=f"{self.format_time(cur_frame/self.fps)} / {self.format_time(self.total_frames/self.fps)}")
                    self.seek_slider.set(cur_frame)

                delay = max(1, int(val * 1000)) if val > 0 else 1
                self.after(delay, self.update_video)
            else: self.stop_media()

    def update_music_time(self):
        if self.video_running and not self.is_paused and not self.current_file.endswith(".mp4"):
            raw_pos = pygame.mixer.music.get_pos()
            if raw_pos == -1: return
            cur_sec = self.music_start_time + (raw_pos / 1000.0)
            self.time_label.configure(text=f"{self.format_time(cur_sec)} / {self.format_time(self.total_music_sec)}")
            self.seek_slider.set(cur_sec)
            self.after(500, self.update_music_time)

    # --- プレイリスト操作 ---
    def delete_selected(self):
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            if hasattr(self, 'current_file') and self.current_file == self.playlist_paths[idx]:
                self.stop_media()
            self.playlist_paths.pop(idx)
            self.listbox.delete(idx)

    def clear_playlist(self):
        self.stop_media()
        self.playlist_paths.clear()
        self.listbox.delete(0, "end")

    def seek_media(self, value):
        if not hasattr(self, 'current_file'): return
        v = float(value)
        if self.current_file.endswith(".mp4"):
            if self.cap:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, int(v))
                if self.audio_player: self.audio_player.seek(v/self.fps, relative=False)
        else:
            self.music_start_time = v
            pygame.mixer.music.play(start=v)
            if self.is_paused: pygame.mixer.music.pause()

    def change_volume(self, value):
        self.current_volume = float(value)
        pygame.mixer.music.set_volume(self.current_volume)
        if self.audio_player: self.audio_player.set_volume(self.current_volume)

if __name__ == "__main__":
    app = MediaApp()
    app.mainloop()
