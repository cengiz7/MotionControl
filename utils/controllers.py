from collections import deque
import threading
from pynput.mouse import Button, Controller
from pynput.keyboard import Key
from pynput.keyboard import Controller as KeyboardController
from math import fabs, sqrt, pow, pi
from PIL import ImageGrab
from queue import Queue

mouse = Controller()
keyboard = KeyboardController()

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
    if fabs((detection[2][1] + (detection[2][3] / 2)) -
            last_bottom_location) > relative_size and fabs(detection[2][0] - last_dtc_location[0]) > relative_size:

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
        mouse.move(round(x), round(y))


def calculate_cursor_movement(x, y, speed, radius):
    x = (radius * (x/radius) * speed) / 4
    y = (radius * (y/radius) * speed) / 4
    return x, y


# mouse controls
class Controls:
    def __init__(self, frame_width, frame_height, movement_speed, names):
        self.n = names  # for action matching
        self.mouse_movement_queue = Queue()
        th = threading.Thread(target=move_smooth, args=(self.mouse_movement_queue,))
        th.daemon = True
        th.start()
        img = ImageGrab.grab()
        self.screen_size = img.size
        self.screen_area = img.size[0] * img.size[1]
        self.frame_width, self.frame_height = frame_width, frame_height
        self.frame_area = frame_width * frame_height
        self.cursor_center_radius = 1
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

    # currently this fucntıon is useless you can delete it
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
        # print( distance )
        if distance > self.cursor_center_radius:
            x, y = calculate_cursor_movement(abs_x, abs_y, self.movement_speed, self.cursor_center_radius)
            self.mouse_movement_queue.put((x, y))

    def action(self, sign, detection):
        # TODO: check rectangle size for validation
        # Mouse Cursor movements
        if sign == self.n['move']:
            self.move_cursor(detection)
        # Left Mouse Press
        if sign == self.n['press_move']:
            if not self.left_button_pressed:
                mouse.press(Button.left)
                self.left_button_pressed = True
            self.move_cursor(detection)
        # Letf Mouse Click
        if sign == self.n['left_click']:
            if not self.left_button_clicked:
                mouse.click(Button.left, 1)
                self.left_button_clicked = True
        if sign == self.n['8pen']:
            # just update the last detection cordinates then we weill use
            # it in the 8pen keyboard window for indicator circle
            self.last_dtc_location = [detection[2][0], detection[2][1]]


class KeyboardControls:
    qpi = 0.25*pi
    active = False
    first_region = 0   # initial value
    second_region = 0  # initial value
    last_region = 0    # initial value
    # Todo: ctrl alt kontrolleri için tutucu bir değişken lazım
    alt_active = False
    ctrl_active = False

    def __check_region(self, radian):  # divide 8pen window to 4 pieces for controll shortcuts
        # clockwise numerating the regions
        if self.qpi < radian < self.qpi*3:      return 1
        elif self.qpi > radian > -self.qpi:     return 2
        elif -self.qpi > radian > -self.qpi*3:  return 3
        elif self.qpi*3 < radian or radian < -self.qpi*3: return 4

    def key_in(self, ch):
        keyboard.press(ch)  # ch ~ 'A'
        self.__finalize_ctrlalt_press()
        keyboard.release(ch)

    def press_ctrl(self):
        keyboard.press(Key.ctrl)
        if self.ctrl_active:
            keyboard.release(Key.ctrl)
            self.ctrl_active = False
        else:
            self.ctrl_active = True

    def press_alt(self):
        keyboard.press(Key.alt)
        if self.alt_active:
            keyboard.release(Key.alt)
            self.alt_active = False
        else:
            self.alt_active = True

    def press_esc(self):
        keyboard.press(Key.esc)
        keyboard.release(Key.esc)

    def press_backspace(self):
        keyboard.press(Key.backspace)
        keyboard.release(Key.backspace)

    def press_enter(self):
        keyboard.press(Key.enter)
        keyboard.release(Key.enter)

    def press_space(self):
        keyboard.press(Key.space)
        keyboard.release(Key.space)

    def __finalize_ctrlalt_press(self):
        if self.ctrl_active: keyboard.release(Key.ctrl)
        if self.alt_active: keyboard.release(Key.alt)
        self.alt_active = False
        self.ctrl_active = False

    # detect which arm and char selected within the 2 sides of an arm
    def __odd_even_and_arm(self):
        if self.first_region == 4 and self.second_region == 1:
            return 1, 4
        elif self.first_region == 1 and self.second_region == 4:
            return 2, 4
        elif self.first_region < self.second_region:
            return 1, self.first_region
        else:
            return 2, self.second_region

    def __calculate_steps(self):
        odd_even, arm = self.__odd_even_and_arm()
        step = 0
        if self.first_region == self.last_region:
            step = 4
        else:
            if odd_even == 1:
                if self.first_region < self.last_region:
                    step = self.last_region - self.first_region
                else:
                    step = 4 - (self.first_region - self.last_region)
            elif odd_even == 2:
                if self.first_region < self.last_region:
                    step = 4 - (self.last_region - self.first_region)
                else:
                    step = self.first_region - self.last_region
        step = (step-1) * 8 # each level has 8 characters
        step = step + ((arm-1)*2) + odd_even
        return int(step-1)  # -1 for array indexing

    def check_control(self, inout_check, radian):
        if inout_check and not self.active:
            self.active = True
            self.first_region = self.__check_region(radian)

        if inout_check and self.active:
            current_region = self.__check_region(radian)
            if self.first_region != current_region and self.second_region == 0:
                self.second_region = current_region
                self.last_region = current_region
            else:
                self.last_region = current_region
            return self.__calculate_steps(), 0, False  # only for displaying current char at the center

        if not inout_check and not self.active:
            if self.first_region != 0:
                self.first_region, self.second_region, self.last_region = 0, 0, 0  # reset vals

        if not inout_check and self.active:
            self.active = False
            if self.second_region == 0:
                print("fonksiyon tuşu aktif")
                return -1, self.first_region, True  # -1 for array indexing
            else:
                return self.__calculate_steps(), 0, True
        return -1, 0, False


