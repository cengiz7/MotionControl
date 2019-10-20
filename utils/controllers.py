from collections import deque
import threading
from pynput.mouse import Button, Controller
import time
from math import fabs, sqrt
from PIL import ImageGrab

mouse = Controller()


def calculate_relative(frame_area, screen_area, detection, last_dtc_location, last_bottom_location):
    relative_size = sqrt(sqrt(frame_area / (detection[2][2] * detection[2][3])) * (screen_area/frame_area))/1.5
    print(relative_size)
    # when we switch duz sign to another sign, mouse cursor moves downwar if the new sign size taking less area then duz
    # sign, so if y max and center x cordinate changing less then we want, dont move the cursor
    if fabs((detection[2][1] + (detection[2][3] / 2)) - last_bottom_location) > relative_size and fabs(detection[2][0] - last_dtc_location[0]) > relative_size:

        abs_x = round((detection[2][0] - last_dtc_location[0])) * relative_size
        abs_y = round((detection[2][1] - last_dtc_location[1])) * relative_size
        if fabs(abs_x) < relative_size and fabs(abs_y) < relative_size:
            return 0, 0  # for ignoring small movement detections
        return abs_x, abs_y
    else:
        return 0, 0

class Controls:
    def __init__(self, frame_width, frame_height, movement_speed):
        img = ImageGrab.grab()
        self.screen_size = img.size
        self.screen_area = img.size[0] * img.size[1]
        self.frame_width, self.frame_height = frame_width, frame_height
        self.frame_area = frame_width * frame_height
        self.movement_speed = movement_speed
        self.DEQUE_MAX_LEN = 32
        self.pts = deque(maxlen=self.DEQUE_MAX_LEN)
        self.ounter = 0
        self.dX, self.dY = 0, 0
        self.SPEED = 20
        self.last_dtc_location = [0, 0]
        self.last_bottom_location = 0.0
        self.left_button_pressed = False
        self.left_button_clicked = False
        del img

    def release_left_press(self):
        mouse.release(Button.left)

    def move_smooth(self, x, y, speed):
        speed = 30 / (1 / speed)
        x = x / speed
        y = y / speed
        for _ in range(round(speed)):
            mouse.move(round(x), round(y))
            time.sleep((1 / speed) / 4)

    def move_cursor(self, detection):
        # calculate relative will return 0, 0 for unnecessary movements
        (x, y) = calculate_relative(self.frame_area, self.screen_area, detection, self.last_dtc_location,
                                    self.last_bottom_location)
        if fabs(x) + fabs(y) > 0 and x < self.screen_size[0] / 3 and y < self.screen_size[1] / 3:
            self.last_bottom_location = int(round(detection[2][1] + (detection[2][3] / 2)))
            threading.Thread(target=self.move_smooth, args=(x, y, self.movement_speed)).start()
            self.last_dtc_location = [detection[2][0], detection[2][1]]

    def action(self, sign, detection):
        # TODO: check rectangle size for validation

        # Mouse Cursor movements
        if sign == 'duz':
            self.move_cursor(detection)
        # Left Mouse Press
        if sign == 'basisaret':
            if not self.left_button_pressed:
                mouse.press(Button.left)
                self.left_button_pressed = True
                self.move_cursor(detection)

        # Letf Mouse Click
        if sign == 'basisaretserce':
            if not self.left_button_clicked:
                mouse.click(Button.left, 1)
                self.left_button_clicked = True

