import pickle
from collections import deque

class MusicQueue:
    def __init__(self):
        self.song = None
        self.queue = deque()
        self.pre_queue = deque()
        self.fav_queue = deque()
        self.save_queue = deque()
        self.is_playing = False
        # self.get_save()

    def add(self, item):
        self.queue.append(item)

    def get_next(self):
        if self.queue:
            self.song = self.queue.popleft()
            self.pre_queue.append(self.song)
            return self.song
        return None

    def get_previous(self):
        if self.pre_queue:
            self.song = self.pre_queue.pop()
            self.queue.appendleft(self.song)
            return self.song
        return None

    def set_favorite(self):
        self.fav_queue.append(self.song)
        with open(r"utils\fav.txt", "a") as file:
            pickle.dump(self.song, file)

    def get_favorite(self):
        self.save_queue.append(self.song)
        with open(r"utils\fav.txt", "r") as file:
            self.queue = pickle.load(file)

    def set_save(self):
        self.fav_queue.append(self.song)
        with open(r"utils\sav.pkl", "ab") as file:
            pickle.dump(self.song, file)

    def get_save(self):
        self.save_queue.append(self.song)
        with open(r"utils\sav.pkl", "rb") as file:
            self.queue = pickle.load(file)