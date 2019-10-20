import time


class MouseTrackWindow:
    def __init__(self):
        pass


class KeyboardTrackWindow:
    def __init__(self):
        pass


class ShowFps:
    # fps_after_frames = calculate fps once at every each 3 frame
    fps_after_frames = 3
    total_frame_count = 0
    calculated_fps = 0
    check_time = None

    def __init__(self, desired_frame_count):
        self.fps_after_frames = desired_frame_count

    def start(self):
        self.check_time = time.time()

    def next(self):
        self.total_frame_count += 1
        if self.total_frame_count % self.fps_after_frames == 0:
            self.calculated_fps = (1 / (time.time() - self.check_time)) * self.fps_after_frames
            self.check_time = time.time()
        return self.calculated_fps



