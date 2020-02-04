from collections import deque
import threading
from pynput.mouse import Button, Controller
import time
from math import fabs, sqrt, pow
from PIL import ImageGrab
from queue import Queue


mouse = Controller()


def calculate_relative(frame_area, screen_area, detection, last_dtc_location, last_bottom_location):
    """
    abs_frame = sqrt(screen_area/frame_area)
    abs_hand = sqrt(frame_area/(detection[2][2]*detection[2][3]))
    abs_x = fabs(detection[2][0] - last_dtc_location[0])  # x center
    abs_y = fabs(detection[2][1] - last_dtc_location[1])  # y center
    print(f'abs_x: {abs_x}\nabs_y: {abs_y}\nabs_frame: {abs_frame}\nabs_hand: {abs_hand}')
    abs_x *= (abs_hand * abs_frame)
    abs_y *= (abs_hand * abs_frame)
    print(abs_x, abs_y, '\n\n')
    """
    relative_size = sqrt(sqrt(frame_area / (detection[2][2] * detection[2][3])) * (screen_area/frame_area))/1.5
    # when we switch duz sign to another sign, mouse cursor moves downward if new sign size taking less area then duz
    # new sign area could be shorter from top x
    # sign, so if y max and center x cordinate changing less then we want, dont move the cursor
    if fabs((detection[2][1] + (detection[2][3] / 2)) - last_bottom_location) > relative_size and fabs(detection[2][0] - last_dtc_location[0]) > relative_size:

        abs_x = round((detection[2][0] - last_dtc_location[0])) * relative_size
        abs_y = round((detection[2][1] - last_dtc_location[1])) * relative_size
        if fabs(abs_x) < relative_size and fabs(abs_y) < relative_size:
            return 0, 0  # for ignoring small movement detections
        return abs_x, abs_y
    else:
        return 0, 0


def move_smooth(mouse_movement_queue):
    while True:
        (x, y) = mouse_movement_queue.get()
        # complete movement in 4 step for smooth movement
        for _ in range(4):
            mouse.move(round(x/4), round(y/4))


def calculate_cursor_movement(x, y, speed, radius):
    x = (radius * (x/radius) * speed) / 2
    y = (radius * (y/radius) * speed) / 2
    return x, y


class Controls:
    def __init__(self, frame_width, frame_height, movement_speed):
        self.mouse_movement_queue = Queue()
        th = threading.Thread(target=move_smooth, args=(self.mouse_movement_queue,))
        th.daemon = False
        th.start()
        img = ImageGrab.grab()
        self.screen_size = img.size
        self.screen_area = img.size[0] * img.size[1]
        self.frame_width, self.frame_height = frame_width, frame_height
        self.frame_area = frame_width * frame_height
        self.cursor_center_radius = 0
        self.movement_speed = movement_speed
        self.DEQUE_MAX_LEN = 32
        self.pts = deque(maxlen=self.DEQUE_MAX_LEN)
        self.ounter = 0
        self.dX, self.dY = 0, 0
        self.SPEED = 20
        self.first_dtc_location = [0, 0]
        self.last_dtc_location = [0, 0]
        self.last_bottom_location = 0.0
        self.left_button_pressed = False
        self.left_button_clicked = False
        del img

    def release_left_press(self):
        mouse.release(Button.left)
        self.left_button_pressed = False

    def old_move_cursor(self, detection):
        # calculate relative will return 0, 0 for unnecessary movements
        (x, y) = calculate_relative(self.frame_area, self.screen_area, detection, self.last_dtc_location,
                                    self.last_bottom_location)
        if abs(x) > 4 and fabs(y) > 4:
            self.last_bottom_location = int(round(detection[2][1] + (detection[2][3] / 2)))
            # threading.Thread(target=move_smooth, args=(x, y, self.movement_speed)).start()
            self.mouse_movement_queue.put((x, y, self.movement_speed))
            self.last_dtc_location = [detection[2][0], detection[2][1]]

    def move_cursor(self, detection):
        self.last_dtc_location = [detection[2][0], detection[2][1]]
        abs_x = detection[2][0] - self.first_dtc_location[0]
        abs_y = detection[2][1] - self.first_dtc_location[1]
        distance = sqrt(pow(fabs(abs_x), 2) + pow(fabs(abs_y), 2))  # hipotenus to detection center
        print(distance)
        if distance > self.cursor_center_radius:
            x, y = calculate_cursor_movement(abs_x, abs_y, self.movement_speed, self.cursor_center_radius)
            self.mouse_movement_queue.put((x, y))

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
        if sign == 'peace':
            if not self.left_button_clicked:
                mouse.click(Button.left, 1)
                self.left_button_clicked = True

