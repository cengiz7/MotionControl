from MotionControl.utils import controllers
from MotionControl.utils import graphics as gr
from math import fabs, sqrt, pow, atan2

keyboard = controllers.KeyboardControls()


def convertBack(x, y, w, h):
    xmin = int(round(x - (w / 2)))
    xmax = int(round(x + (w / 2)))
    ymin = int(round(y - (h / 2)))
    ymax = int(round(y + (h / 2)))
    return xmin, ymin, xmax, ymax


def pt_extractor(detection):
    x, y, w, h = detection[2][0], \
                 detection[2][1], \
                 detection[2][2], \
                 detection[2][3]
    xmin, ymin, xmax, ymax = convertBack(float(x), float(y), float(w), float(h))
    # return pt1 , pt2
    return (xmin, ymin), (xmax, ymax)


def calculate_radius(detection_width, frame_width):
    radius = (detection_width / 30) * frame_width / detection_width
    if radius*2 > detection_width:
        radius = detection_width
    return radius


# for mouse cursor indications and movements
def regulate_cursor_window(show, firstx=0, firsty=0, radius=0, lastx=0, lasty=0):
    if show:
        # set necessary cordinates for cursor movement indications
        gr.firstx, gr.firsty, gr.radius, gr.lastx, gr.lasty = firstx, firsty, radius, lastx, lasty
        gr.arrow_movement()  # to calculate angle for cursor indication arrow before display
        gr.cursor_wnd.Show()
        gr.cursor_wnd.Refresh()
    else:
        gr.cursor_wnd.Hide()


def calcutale_distance_angle(firstx, firsty, lastx, lasty):
    abs_x = lastx - firstx
    abs_y = firsty - lasty
    distance = sqrt(pow(fabs(abs_x), 2) + pow(fabs(abs_y), 2))  # hipotenus to detection center
    return distance, atan2(abs_y, abs_x)  # angle in radian


def apply_function(func):
    icon_names = [["next-page", "enter", "space", "backspace"], ["next-page", "capslock", "ctrl", "alt"]]
    name = gr.icon_names[gr.eightpen_wnd.current_page][func]
    print(name)
    if name == "next-page":
        gr.post_wx_event(gr.eightpen_wnd, gr.swtch_pg_evnt)
    elif name == "enter":
        keyboard.press_enter()
    elif name == "space":
        keyboard.press_space()
    elif name == "backspace":
        keyboard.press_backspace()
    elif name == "capslock":
        gr.post_wx_event(gr.eightpen_wnd, gr.swtch_case_evnt)
    elif name == "ctrl":
        keyboard.press_ctrl()
    elif name == "alt":
        keyboard.press_alt()


def regulate_eightpen_window(show, firstx=0, firsty=0, radius=0, lastx=0, lasty=0):
    if show:
        distance, radian = calcutale_distance_angle(firstx, firsty, lastx, lasty)
        # update indicator circle possition
        chck = distance >= gr.circle_radius
        char_pos, function, ok = keyboard.check_control(chck, radian)
        # only one char input
        if ok and function == 0:
            try:
                if gr.eightpen_wnd.current_page == 0:
                    ch = gr.alphabet_chars[char_pos]
                else:
                    ch = gr.special_chars[char_pos]
                # print(ch)
                gr.eightpen_wnd.center_text.SetText('')  # reset center text
                keyboard.key_in(ch)
            except Exception:
                pass
        # function or function combined with char
        elif ok and function:
            apply_function(function-1)  # -1 for array indexing
        elif not ok and char_pos != -1:
            gr.eightpen_wnd.center_text.SetText(gr.alphabet_chars[char_pos])

        gr.eightpen_wnd.indicator_circle.XY = (lastx - firstx, firsty - lasty)
        gr.eightpen_wnd.cs.Draw(True)
        gr.eightpen_wnd.custom_show()
    else:
        if not gr.eightpen_wnd.is_custom_hide:
            gr.eightpen_wnd.custom_hide()


class SignDetector:
    controls = None
    reset_check = False  # bool for sign_dict reset jobs
    cursor_wnd_dsply = False  # bool for cursor window display or hide checks
    eightpen_wnd_dsply = False  # for 8pen window

    def __init__(self, alt_names, frame_width, frane_height, movement_speed, names):
        self.n = names  # for action matching
        self.frame_width = frame_width
        self.controls = controllers.Controls(frame_width, frane_height, movement_speed, names)
        # minimun frame count for activating sign controlled action
        self.min_dtct_actv_count = 4  # initial value for avarage 15-20 fps
        self.signs_dict = {}
        for name in alt_names:
            self.signs_dict[name] = 0

    def reset_detection_counts(self):
        for name in self.signs_dict:
            self.signs_dict[name] = 0

    def update_min_activator(self, count):
        self.min_dtct_actv_count = count

    def detect_sign(self, detections):
        for detection in detections:
            name = detection[0].decode()
            self.signs_dict[name] += 1
            # run control command only if sign detection count bigger than min activation count
            if self.signs_dict[name] > self.min_dtct_actv_count:
                # take action here !
                self.controls.action(name, detection)

                if name == self.n['8pen']:
                    self.eightpen_wnd_dsply = True
                    regulate_eightpen_window(True, self.controls.first_dtc_location[0],
                                             self.controls.first_dtc_location[1], self.controls.cursor_center_radius,
                                             self.controls.last_dtc_location[0], self.controls.last_dtc_location[1])
                else:
                    regulate_eightpen_window(False)
                    self.cursor_wnd_dsply = False

                # set display true or false for cursor indications
                if name == self.n['move'] or name == self.n['press_move']:
                    self.cursor_wnd_dsply = True
                    regulate_cursor_window(True, self.controls.first_dtc_location[0],
                                           self.controls.first_dtc_location[1], self.controls.cursor_center_radius,
                                           self.controls.last_dtc_location[0], self.controls.last_dtc_location[1])
                else:
                    self.cursor_wnd_dsply = False
                    regulate_cursor_window(False)

            else:
                # correct some values just before calling action function at the other detection
                if self.signs_dict[name] == self.min_dtct_actv_count:
                    if name == self.n['move'] or name == self.n['press_move'] or name == self.n['8pen']:
                        # set last detection point center for initial movement calculation and others
                        self.controls.first_dtc_location = [detection[2][0], detection[2][1]]
                        # comment out right below when detection display = false
                        self.controls.cursor_center_radius = calculate_radius(detection[2][2], self.frame_width)
                        self.controls.last_dtc_location = self.controls.first_dtc_location  # for initial display
                        # self.controls.last_bottom_location = int(round(detection[2][1] +(detection[2][3]/2)))  # y max
                    # if its not mouse hold move, release the button
                    if self.controls.left_button_pressed and name != self.n['press_move']:
                        self.controls.release_left_press()
                    # if not mouse left click, reset it
                    if self.controls.left_button_clicked and name != self.n['left_click']:
                        self.controls.left_button_clicked = False
                    # reset other sign detections counts
                    for key in self.signs_dict:
                        if key != name:
                            # reset count values
                            self.signs_dict[key] = 0
