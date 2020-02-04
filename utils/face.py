# sources for the face image encodings
# https://www.pyimagesearch.com/2018/06/25/raspberry-pi-face-recognition/

import re
import cv2
import os
import face_recognition
import pickle
from math import fabs
from utils import graphics
from glob import glob
from time import time

roi = [(0, 0), (0, 0)]  # global variable for interested hand area
old_fc_area = [(0, 0), (0, 0)]

dt_path = 'datasets/'
fc_path = 'user_images/'


def name2folder(name):
    tmp = re.sub(r'[^a-zA-Z]', "_", name)  # turn every non-chars to '_'
    tmp = re.sub(r'(_)\1+', "_", tmp)  # replace sequental '___' with a single '_'
    return tmp.upper()


def folder2name(name):
    return re.sub(r'(_)\1+', " ", name)  # abc__def to abc def


def delete_files(path):
    if os.path.isdir(path):
        for i in os.listdir(path):
            delete_files(os.path.join(path, i))
        os.rmdir(path)
    else:
        os.remove(path)


def create_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)


def print_users(user_list):
    for idx, name in enumerate(user_list):
        print(f'{idx+1}-) {folder2name(name)}')


def encode_faces(random_faces_pickle, face_path, pickle_path, detection_method, name, cap):
    """# load random_faces pretrained data and append new user data on it
    infile = open(random_faces_pickle, 'rb')
    tmp_dict = pickle.load(infile)
    infile.close()
    known_encodings, known_names = tmp_dict["encodings"], tmp_dict["names"]
    del tmp_dict """
    known_encodings, known_names = [], []
    processed = 0
    width, height = cap.get(3), cap.get(4)
    total_img_count = len(glob(face_path + '/*.jpg'))
    pt1 = (int((width/20)*2), int((height/30)*24))  # rectangle point for proggress bar
    pt2 = (int((width/20)*18), int((height/30)*25))
    pr_bar_slice = (int((width/20)*18) - int((width/20)*2)) / total_img_count
    for n, img in enumerate(glob(face_path + '/*.jpg')):
        ##################################################
        # for blurred progress window
        cap_img = cap.read()[1]
        cap_img = cv2.GaussianBlur(cap_img, (15, 15), 0)
        cv2.rectangle(cap_img, pt1, pt2, (255, 255, 255), thickness=1, lineType=8, shift=0)  # progressbar border
        cv2.rectangle(cap_img, pt1, (int(pt1[0] + (pr_bar_slice * n)), pt2[1]), (255, 255, 0), -1, 1)  # bar
        cv2.putText(cap_img, '%'+str(int(100*n/total_img_count)), (int(pt1[0] + (pr_bar_slice * n)) + 8, pt2[1]-3),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, [0, 255, 0], 2)  # progresbar % value
        cv2.imshow('Veri Isleniyor', cap_img)
        cv2.waitKey(1)
        ##################################################

        img = img.replace("\\", "/")
        rgb = cv2.cvtColor(cv2.imread(img), cv2.COLOR_BGR2RGB)
        rgb = cv2.convertScaleAbs(rgb, alpha=1.4, beta=30)
        # detect the (x, y)-coordinates of the bounding boxes
        # corresponding to each face in the input image
        boxes = face_recognition.face_locations(rgb, model=detection_method)
        # process if the image contains only one face
        if 0 < len(boxes) < 2:
            # compute the facial embedding for the face
            # higer jitter = more variety of face augmentation
            encodings = face_recognition.face_encodings(rgb, known_face_locations=boxes, num_jitters=50)[0]
            known_encodings.append(encodings)
            known_names.append(name)
            processed += 1
        else:
            print(img + " contains none or more than one faces and can't be used for training.")
            os.remove(img)
            # todo refactor this
            # exit(1)

        # print(f'Total:{total_img_count}  | Current: {n+1}')
    if processed == 0:
        print("[HATA]: Islenen resimlerde yuz tespit edilemedi!!")
        cv2.destroyAllWindows()
        return False
    data = {"encodings": known_encodings, "names": known_names}
    f = open(f'{pickle_path + name}.pickle', "wb")
    f.write(pickle.dumps(data))
    f.close()
    cv2.destroyAllWindows()
    return True


def new_user(face_path, cap):
    while True:
        name = str(input("Yeni kullanici adini giriniz -> "))
        if name2folder(name) != "" and name2folder(name) != "_":
            name = name2folder(name)
            create_folder(face_path + fc_path + name)
            while not take_pictures(face_path + fc_path + name, cap):
                print("En az 1 fotograf kaydetmelisiniz!!!")
            # encode face images with pickle and use cnn method for face detection
            if encode_faces(face_path + "random_faces.pickle", face_path + fc_path + name, face_path + dt_path, "cnn", name, cap):
                break
        else:
            print("Hatali kullanici adi!!!")


def update_user(face_path, users_list, cap):
    pass


def delete_user(face_path, users_list):
    print_users(users_list)
    while True:
        choice = int(input("Silmek istediginiz kullaniciyi seciniz -> "))
        if 0 < choice < len(users_list)+1:
            # TODO: rename datasets
            # delete_files(face_path + 'datasets/' +    name2folder(users_list[choice-1]))
            delete_files(face_path + fc_path + name2folder(users_list[choice-1]))
            break
        else:
            print("Hatali secim yaptiniz!!!")


def take_pictures(face_path, cap):
    img_count = 0
    height = cap.get(4)  # float
    for entry in os.scandir(face_path):  # get current image count
        img_count += 1
    while True:
        img = cap.read()[1]
        keypress = cv2.waitKey(1)
        # if the `q` key was pressed, break from the loop
        if keypress == ord("q"):
            break
        elif keypress == ord('c'):
            cv2.imwrite(face_path + "/%.3f.jpg" % time(), img)  # folder name with epoc time
            img_count += 1
        cv2.putText(img, f'Mevcut Resim Sayisi: {img_count}', (15, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.putText(img, f'Resim kaydetmek icin "C" Sonlandirmak icin "Q" tusuna basiniz.', (15, int(height-25)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.imshow('Face', img)
    cv2.destroyAllWindows()
    if img_count > 0:
        return True
    return False


def get_users_list(path):
    users_list = []
    for pickle_path in glob(path + '/*.pickle'):
        users_list.append(pickle_path.split(os.path.sep)[-1].replace('.pickle', ''))
    return users_list


def print_menu_list(show_additional):
    print("\n\n1-) Yeni kullanici olustur.")
    if show_additional:
        print("2-) Var olan kullanicilardan sec.\n"
              "3-) Var olan kullaniciyi guncelle.\n"
              "4-) Kullanici sil.\n"
              "5-) Cikis.")


def choose_user(path, users_list):
    print_users(users_list)
    while True:
        choice = int(input("Kullanici numarasini giriniz -> "))
        if 0 < choice < len(users_list)+1:
            return path + name2folder(users_list[choice-1]) + '.pickle', name2folder(users_list[choice-1])
        else:
            print("Hatali secim yaptiniz!!!")


def select_user(face_path, cap):
    create_folder(face_path + fc_path)
    create_folder(face_path + dt_path)

    while True:
        users_list = get_users_list(face_path + dt_path)
        show_additional = len(users_list) > 0
        print_menu_list(show_additional)
        choice = int(input(" => "))
        if 0 < choice < 6:
            if choice == 1:
                new_user(face_path, cap)
            elif choice == 5:
                exit(0)
            else:
                if show_additional:
                    if choice == 2:
                        return choose_user(face_path + dt_path, users_list)
                    if choice == 3:
                        update_user(face_path, users_list, cap)
                    if choice == 4:
                        delete_user(face_path, users_list)
                else:
                    print("Hatali secim yaptiniz!!!")
        else:
            print("Hatali secim yaptiniz!!!")


##############################################################################
#___________________________ FACE RECOGNITIONS ______________________________#
##############################################################################


def is_face_moved(p1, p2):
    (left, top) = p1
    (right, bottom) = p2
    h_center = p1[0] + int((p2[0]-p1[0]) / 2)
    v_center = p1[1] + int((p2[1]-p1[1]) / 2)
    if old_fc_area[0][0] <= h_center <= old_fc_area[1][0] and old_fc_area[0][1] <= v_center <= old_fc_area[1][1]:
        # for both vertical and horizontal border lenght change check with 0.25 sensitivity
        if fabs((p2[0]-p1[0]) - (old_fc_area[1][0] - old_fc_area[0][0])) / (p2[0]-p1[0]) < 0.25 or\
                fabs((p2[1]-p1[1]) - (old_fc_area[1][1] - old_fc_area[0][1])) / (p2[1] - p1[1]) < 0.25:
            return False
        return True
    return True


def calculate_roi(width, height, p1, p2):
    # use newly calculated face area for roi if it's center out of the old face area borders
    if is_face_moved(p1, p2):
        old_fc_area[0] = p1
        old_fc_area[1] = p2
    (left, top) = old_fc_area[0]
    (right, bottom) = old_fc_area[1]
    horizontal = int((right-left) * 4)
    vertical_top = int((bottom-top) * 2.5)
    vertical_bottom = int((bottom-top) * 2)  # for smaller roi at the bottom of the face
    right = right + horizontal if right + horizontal <= width else width
    left = left - horizontal if left - horizontal >= 0 else 0
    bottom = bottom + vertical_bottom if bottom + vertical_bottom <= height else height
    top = top - vertical_top if top - vertical_top >= 0 else 0
    return (left, top), (right, bottom)


def detect_faces(cascade, enCodings, frame_queue, user_name, w, h):
    global roi
    data = pickle.loads(open(enCodings, "rb").read())
    detector = cv2.CascadeClassifier(cascade)
    fps = graphics.ShowFps(3)
    fps.start()
    undetected = 0

    while True:
        frame = frame_queue.get()
        fps_val = fps.next()
        # frame = imutils.resize(frame, width=500)
        frame = cv2.convertScaleAbs(frame, alpha=1.4, beta=30)
        # convert the input frame from (1) BGR to grayscale (for face
        # detection) and (2) from BGR to RGB (for face recognition)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # cv2.equalizeHist(gray, gray)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # detect faces in the grayscale frame
        rects = detector.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=6, minSize=(15, 15), maxSize=(300, 300),
                                          flags=cv2.CASCADE_SCALE_IMAGE)

        # OpenCV returns bounding box coordinates in (x, y, w, h) order
        # but we need them in (top, right, bottom, left) order, so we
        # need to do a bit of reordering
        boxes = [(y, x + w, y + h, x) for (x, y, w, h) in rects]

        # compute the facial embeddings for each face bounding box
        encodings = face_recognition.face_encodings(rgb, boxes)
        names = []

        # loop over the facial embeddings
        for encoding in encodings:
            # attempt to match each face in the input image to our known encodings
            # lower tolerance = better recognition, 0.6 recommended
            matches = face_recognition.compare_faces(data["encodings"], encoding, tolerance=0.5)
            name = "Unknown"

            # check to see if we have found a match
            if True in matches:
                # find the indexes of all matched faces then initialize a
                # dictionary to count the total number of times each face
                # was matched
                matched_idxs = [i for (i, b) in enumerate(matches) if b]
                counts = {}

                # loop over the matched indexes and maintain a count for
                # each recognized face
                for i in matched_idxs:
                    name = data["names"][i]
                    counts[name] = counts.get(name, 0) + 1

                # determine the recognized face with the largest number of votes
                name = max(counts, key=counts.get)

            # update the list of names
            names.append(name)
        if names.count(user_name) == 1:
            # for ((top, right, bottom, left), name) in zip(boxes, names):
            (top, right, bottom, left) = boxes[names.index(user_name)]
            # draw roi
            p1, p2 = calculate_roi(w, h, (left, top), (right, bottom))
            cv2.rectangle(frame, p1, p2, (0, 255, 0), 2)
            # update global roi
            roi = [p1, p2]
            # draw the predicted face name on the image
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            y = top - 15 if top - 15 > 15 else top + 15
            cv2.putText(frame, user_name, (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            # reset undetected count
            undetected = 0
        else:
            undetected += 1
            if undetected == round(fps_val):
                # set roi to max frame size
                roi = [(0, 0), (w, h)]
        # display the image to our screen
        cv2.imshow("Face Detection", frame)
        cv2.waitKey(1)
