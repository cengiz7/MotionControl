from MotionControl.utils import controllers


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


class SignDetector:
    signs_dict = {}
    controls = None
    reset_check = False  # boolean for sign_dict reset jobs

    def __init__(self, names, frame_width, frane_height, movement_speed):
        self.frame_width = frame_width
        self.controls = controllers.Controls(frame_width, frane_height, movement_speed)
        # minimun frame count for activating sign controlled action
        self.min_dtct_actv_count = 4  # initial value for avarage 15-20 fps
        for name in names:
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
                self.controls.action(name, detection)
            else:
                # correct some values just before calling action function at the other detection
                if self.signs_dict[name] == self.min_dtct_actv_count:
                    if name != 'duz' and name != 'basisaret':
                        self.controls.first_dtc_location = [0, 0]
                    if name == 'duz' or name == 'basisaret':
                        # set last detection point center for initial movement calculation and others
                        self.controls.first_dtc_location = [detection[2][0], detection[2][1]]
                        self.controls.cursor_center_radius = calculate_radius(detection[2][2], self.frame_width)
                        self.controls.last_dtc_location = self.controls.first_dtc_location  # for initial display
                        # self.controls.last_bottom_location = int(round(detection[2][1] +(detection[2][3]/2)))  # y max
                    # if its not mouse hold move, release the button
                    if name != 'basisaret':
                        self.controls.release_left_press()
                    # if not mouse left click, reset it
                    if name != 'basisaretserce':
                        self.controls.left_button_clicked = False
                    # reset other sign detections counts
                    for key in self.signs_dict:
                        if key != name:
                            # reset count values
                            self.signs_dict[key] = 0
