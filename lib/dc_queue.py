from collections import deque

class MusicQueue:
    def __init__(self):
        self.queue = deque()
        self.is_playing = False

    def add(self, item):
        self.queue.append(item)

    def get_next(self):
        if self.queue:
            return self.queue.popleft()
        return None