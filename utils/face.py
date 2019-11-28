# sources for the face image encodings
# https://www.pyimagesearch.com/2018/06/25/raspberry-pi-face-recognition/

import re
import cv2
import os
import face_recognition
import pickle
from glob import glob
from time import time


def name2folder(name):
    tmp = re.sub(r'[^a-zA-Z]', "_", name)  # turn every non-chars to '_'
    tmp = re.sub(r'(_)\1+', "_", tmp)  # replace sequental '___' with a single '_'
    return tmp.upper()


def folder2name(name):
    return re.sub(r'(.)\1+', " ", name)  # replace '_' with white space


def encode_face(face_path, detection_method, name):
    pass


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


def encode_faces(face_path, pickle_path, detection_method, name, cap):
    known_encodings = []
    known_names = []
    width, height = cap.get(3), cap.get(4)
    total_img_count = len(glob(face_path + '/*.jpg'))
    pt1 = (int((width/20)*2), int((height/30)*24))  # rectangle point for proggress bar
    pt2 = (int((width/20)*18), int((height/30)*25))
    pr_bar_slice = (int((width/20)*18) - int((width/20)*2)) / total_img_count
    for n, img in enumerate(glob(face_path + '/*.jpg')):
        cap_img = cap.read()[1]
        cap_img = cv2.GaussianBlur(cap_img, (15, 15), 0)
        cv2.rectangle(cap_img, pt1, pt2, (255, 255, 255), thickness=1, lineType=8, shift=0)  # progressbar border
        cv2.rectangle(cap_img, pt1, (int(pt1[0] + (pr_bar_slice * n)), pt2[1]), (255, 255, 0), -1, 1)  # bar
        cv2.putText(cap_img, '%'+str(int(100*n/total_img_count)), (int(pt1[0] + (pr_bar_slice * n)) + 8, pt2[1]-3),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, [0, 255, 0], 2)  # progresbar % value
        cv2.imshow('Veri Isleniyor', cap_img)
        cv2.waitKey(1)

        img = img.replace("\\", "/")
        rgb = cv2.cvtColor(cv2.imread(img), cv2.COLOR_BGR2RGB)

        # detect the (x, y)-coordinates of the bounding boxes
        # corresponding to each face in the input image
        boxes = face_recognition.face_locations(rgb, model=detection_method)

        # compute the facial embedding for the face
        encodings = face_recognition.face_encodings(rgb, boxes)

        for encoding in encodings:
            known_encodings.append(encoding)
            known_names.append(name)
        print(f'Total:{total_img_count}  | Current: {n+1}')
    data = {"encodings": known_encodings, "names": known_names}
    f = open(f'{pickle_path + name}.pickle', "wb")
    f.write(pickle.dumps(data))
    f.close()
    cv2.destroyAllWindows()


def new_user(face_path, cap):
    while True:
        name = str(input("Yeni kullanici adini giriniz -> "))
        if name2folder(name) != "" and name2folder(name) != "_":
            name = name2folder(name)
            create_folder(face_path + 'user_images/' + name)
            while not take_pictures(face_path + "user_images/" + name, cap):
                print("En az 1 fotograf kaydetmelisiniz!!!")
            # encode face images with pickle
            # use cnn method for face detection
            encode_faces(face_path + 'user_images/' + name, face_path + 'datasets/', "cnn", name, cap)

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
            delete_files(face_path + 'user_images/' + name2folder(users_list[choice-1]))
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
    for entry in os.scandir(path):
        if entry.is_dir():
            users_list.append(entry.name)
    return users_list


def print_menu_list(show_additional):
    print("\n\n1-) Yeni kullanici olustur.")
    if show_additional:
        print("2-) Var olan kullanicilardan sec.\n"
              "3-) Var olan kullaniciyi guncelle.\n"
              "4-) Kullanici sil.\n"
              "5-) Cikis.")


def select_user(face_path, cap):
    create_folder(face_path + "user_images")
    create_folder(face_path + "datasets")

    while True:
        users_list = get_users_list(face_path + "user_images")
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
                        print_users(users_list)
                        break
                    if choice == 3:
                        update_user(face_path, users_list, cap)
                    if choice == 4:
                        delete_user(face_path, users_list)
                else:
                    print("Hatali secim yaptiniz!!!")
        else:
            print("Hatali secim yaptiniz!!!")
    return users_list[0]

