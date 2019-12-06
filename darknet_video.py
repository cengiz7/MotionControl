import os
import darknet_dll
import cv2
from threading import Thread
from queue import Queue
from utils import graphics
from utils import logicals
from utils import face


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


def yolo_loop(cropped_frame_queue, detections_queue, net_main, meta_main, thresh_val):
    while True:
        (frame, frame_count) = cropped_frame_queue.get()
        # 4 equals cv2.COLOR_BGR2RGB = 4
        frame_rgb = cv2.cvtColor(frame, 4)
        darknet_image = darknet_dll.make_image(frame_rgb.shape[1], frame_rgb.shape[0], 3)
        darknet_dll.copy_image_from_bytes(darknet_image, frame_rgb.tobytes())
        detections = darknet_dll.detect_image(net_main, meta_main, darknet_image, thresh=thresh_val)
        detections_queue.put((detections, frame, frame_count))


def YOLO():
    cropped_frame_queue = Queue()
    detections_queue = Queue()
    configPath = "./data/yolov3-obj.cfg"
    weightPath = "./data/yolov3-obj_13000.weights"
    metaPath = "./data/obj.data"
    facePath = "./data/face_dataset/"
    faceCascade = facePath + "frontalface_default.xml"

    net_main = None
    meta_main = None
    alt_names = None
    # frame_width, frame_height = 1280, 720
    frame_width, frame_height = 640, 480
    dshow_active = False
    thresh_val = 0.7
    movement_speed = 1
    default_activator_deactivator_val = 4
    if not os.path.exists(configPath):
        raise ValueError("Invalid config path `" + os.path.abspath(configPath)+"`")
    if not os.path.exists(weightPath):
        raise ValueError("Invalid weight path `" + os.path.abspath(weightPath)+"`")
    if not os.path.exists(metaPath):
        raise ValueError("Invalid data file path `" + os.path.abspath(metaPath)+"`")
    if net_main is None:
        net_main = darknet_dll.load_net_custom(configPath.encode(
            "ascii"), weightPath.encode("ascii"), 0, 1)  # batch size = 1
    if meta_main is None:
        meta_main = darknet_dll.load_meta(metaPath.encode("ascii"))
    if alt_names is None:
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
                            alt_names = [x.strip() for x in namesList]
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

    # get selected user
    user_pickle, user_name = face.select_user(facePath, cap)

    Thread(target=face.detect_faces, args=(faceCascade, user_pickle, user_name, frame_width, frame_height,
                                           cropped_frame_queue, cap)).start()

    print("Starting the YOLO loop...")
    Thread(target=yolo_loop, args=(cropped_frame_queue, detections_queue, net_main, meta_main, thresh_val)).start()
    Thread(target=yolo_loop, args=(cropped_frame_queue, detections_queue, net_main, meta_main, thresh_val)).start()

    yolo_frame_count = 1
    tmp_frame_list = []
    tmp_count_list = []
    tmp_detections = []
    sign_detector = logicals.SignDetector(alt_names, frame_width, frame_height, movement_speed)
    fps = graphics.ShowFps(3)
    fps.start()

    def magic(detections, frame_rgb):
        image = cvDrawBoxes(detections, cv2.cvtColor(frame_rgb, cv2.COLOR_BGR2RGB))
        fps_val = fps.next()
        # update minimum detect activator count (1 for each 4 frames)
        sign_detector.update_min_activator(round(fps_val / default_activator_deactivator_val))
        # hand sign detection
        sign_detector.detect_sign(detections)
        cv2.putText(image, f'{fps_val:3.2f} fps', (15, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

        cv2.imshow('Demo Double Threaded', image)
        k = cv2.waitKey(1) & 0xFF
        if k == ord('q') or k == ord('Q'):
            # baska tus icin ord c gibi elif koyabilirsin
            exit(0)

    while True:
        (detections, frame_rgb, frame_count) = detections_queue.get()
        magic(detections, frame_rgb)

if __name__ == "__main__":
    YOLO()
