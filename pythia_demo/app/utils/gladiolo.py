import random

class VideoRecorder:
    def __init__(self, *a, **kw):
        self.ctr = 0

    def record(self):
        if random.randint(0,1):
            self.ctr += random.randint(0,100)
        return f"/tmp/videos/{self.ctr}.avi"

