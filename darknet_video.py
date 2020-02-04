import os
import darknet_dll
import cv2
from threading import Thread
from queue import Queue
from utils import graphics
from utils import logicals
from utils import face

configPath = "./data/yolov3-obj.cfg"
weightPath = "./data/yolov3-obj_13000.weights"
metaPath = "./data/obj.data"
facePath = "./data/face_dataset/"
faceCascade = facePath + "frontalface_default.xml"

netMain = None
metaMain = None
altNames = None
# frame_width, frame_height = 1280, 720
frame_width, frame_height = 640, 480
old_width, old_height = 0, 0
dshow_active = False
thresh_val = 0.7
movement_speed = 1
default_activator_deactivator_val = 4


darknet_image = darknet_dll.make_image(frame_width, frame_height, 3)

def cvDrawBoxes(detections, img):
    for detection in detections:
        pt1, pt2 = logicals.pt_extractor(detection)
        cv2.rectangle(img, pt1, pt2, (0, 255, 0), 1)
        cv2.putText(img,
                    detection[0].decode() +
                    " [" + str(round(detection[1] * 100, 2)) + "]",
                    (pt1[0], pt1[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    [0, 255, 0], 2)
    return img


def reCreateDarknetImage(width, height):
    global darknet_image
    darknet_image = darknet_dll.make_image(width, height, 3)


def YOLO():
    full_frame_queue = Queue()
    processed_frame_queue = Queue()
    global metaMain, netMain, altNames, frame_width, frame_height, thresh_val, old_width, old_height, darknet_image

    if not os.path.exists(configPath):
        raise ValueError("Invalid config path `" + os.path.abspath(configPath)+"`")
    if not os.path.exists(weightPath):
        raise ValueError("Invalid weight path `" + os.path.abspath(weightPath)+"`")
    if not os.path.exists(metaPath):
        raise ValueError("Invalid data file path `" + os.path.abspath(metaPath)+"`")
    if netMain is None:
        netMain = darknet_dll.load_net_custom(configPath.encode(
            "ascii"), weightPath.encode("ascii"), 0, 1)  # batch size = 1
    if metaMain is None:
        metaMain = darknet_dll.load_meta(metaPath.encode("ascii"))
    if altNames is None:
        try:
            with open(metaPath) as metaFH:
                metaContents = metaFH.read()
                import re
                match = re.search("names *= *(.*)$", metaContents, re.IGNORECASE | re.MULTILINE)
                if match:
                    result = match.group(1)
                else:
                    result = None
                try:
                    if os.path.exists(result):
                        with open(result) as namesFH:
                            namesList = namesFH.read().strip().split("\n")
                            altNames = [x.strip() for x in namesList]
                except TypeError:
                    pass
        except Exception:
            pass


    if dshow_active:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(0)

    cap.set(3, frame_width)
    cap.set(4, frame_height)
    # y1:y2, x1:x2
    face.roi[1] = (frame_width, frame_height)

    user_pickle, user_name = face.select_user(facePath, cap)

    th = Thread(target=face.detect_faces, args=(faceCascade, user_pickle, full_frame_queue, user_name,
                                                frame_width, frame_height))
    th.daemon = False
    th.start()


    print("Starting the YOLO loop...")

    sign_detector = logicals.SignDetector(altNames, frame_width, frame_height, movement_speed)

    fps = graphics.ShowFps(3)
    fps.start()

    while True:
        frame_read = cv2.flip(cap.read()[1], 1)
        # empty the queue for prevent queue from overfeeding
        while not full_frame_queue.empty():
            try:
                full_frame_queue.get_nowait()
            except Empty:
                continue
            full_frame_queue.task_done()
        full_frame_queue.put(frame_read)
        # y1:y2, x1:x2 for cropping
        # 4 equals cv2.COLOR_BGR2RGB = 4
        frame_rgb = cv2.cvtColor(frame_read[face.roi[0][1]:face.roi[1][1], face.roi[0][0]:face.roi[1][0]], 4)
        # recreate new darknet image only if new frame shape different that old one
        tmp_w, tmp_h = frame_rgb.shape[1], frame_rgb.shape[0]
        if old_width != tmp_w or old_height != tmp_h:
            reCreateDarknetImage(tmp_w, tmp_h)
            old_width, old_height = tmp_w, tmp_h

        darknet_dll.copy_image_from_bytes(darknet_image, frame_rgb.tobytes())

        detections = darknet_dll.detect_image(netMain, metaMain, darknet_image, thresh=thresh_val)

        image = cvDrawBoxes(detections, cv2.cvtColor(frame_rgb, cv2.COLOR_BGR2RGB))

        fps_val = fps.next()

        # update minimum detect activator count (1 for each 4 frames)
        sign_detector.update_min_activator(round(fps_val/default_activator_deactivator_val))
        # hand sign detection
        sign_detector.detect_sign(detections)
        # for drawing cursor control center circle
        if sign_detector.controls.first_dtc_location != [0, 0]:
            image = cv2.circle(image, (int(sign_detector.controls.first_dtc_location[0]), int(sign_detector.controls.first_dtc_location[1])),
                               int(sign_detector.controls.cursor_center_radius), (255, 0, 0), 3)
            image = cv2.circle(image, (int(sign_detector.controls.last_dtc_location[0]), int(sign_detector.controls.last_dtc_location[1])),
                               5, (255, 255, 255), 3)
        cv2.putText(image, f'{fps_val:3.2f} fps', (15, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

        cv2.imshow('Demo', image)
        k = cv2.waitKey(1) & 0xFF
        # baska tus icin ord c gibi elif koyabilirsin
        if k == ord('q') or k == ord('Q'):
            exit(0)


if __name__ == "__main__":
    YOLO()
