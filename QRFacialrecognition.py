#pip3 install face_recognition
import cv2
from pyzbar.pyzbar import decode
import datetime as dt
import hashlib
import face_recognition
import numpy as np


cap = cv2.VideoCapture(0)
pause = False
eye_cascade = cv2.CascadeClassifier('haarcascade_righteye_2splits.xml')
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

password = "Brady"
scalefactor = 1.3
tolerance = .54
minNeighbors = 8

usedcodes = []
users = {'name':[], 'auth':[], 'face_encoding':[]} # [Name, auth, face_encoding]


# Takes image and puts boxes on faces using data on users
# If pause, laser is disabled
# reutrns facial encoding

def facialrec(img, pause):
    returnEncode = 0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    faces = face_cascade.detectMultiScale(gray, scalefactor, minNeighbors, minSize=(30, 30))
    boxes = [(y, x + w, y + h, x) for (x, y, w, h) in faces]  # bottom right to top left. List of tuples
    encodings = face_recognition.face_encodings(rgb, boxes)
    names = []

    for encoding in encodings:
        returnEncode = encoding
        matches = face_recognition.compare_faces(users['face_encoding'],
                                                 encoding, tolerance=tolerance)
        name = "Unknown"

        if True in matches:
            matchedIdxs = [i for (i, b) in enumerate(matches) if b]
            counts = {}

            for i in matchedIdxs:
                name = users['name'][i]
                counts[name] = counts.get(name, 0) + 1

            name = max(counts, key=counts.get)
        names.append(name)

    for ((top, right, bottom, left), name) in zip(boxes, names):
        y = top - 15 if top - 15 > 15 else top + 15
        if (name == 'Unknown') or (users['auth'][users['name'].index(name)] == "Not Authorized"):
            cv2.rectangle(img, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.putText(img, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
            if pause:
                img = cv2.putText(img, "Laser Disabled", (5, 30), cv2.FONT_HERSHEY_COMPLEX,
                                  1, (0, 255, 0), 2, cv2.LINE_AA)
            else:
                laserMode(img, faces, gray)
        else:
            cv2.rectangle(img, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(img, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
    return returnEncode

#adds entry to user dictionary
def newUser(name, auth, face_encoding):
    users['name'].append(name)
    users['auth'].append(auth)
    users['face_encoding'].append(face_encoding)


# Detects right eye from img and face bounding box
# If laser mode is on, draws red line, else displays the coordinates of the eye

def laserMode(img, faces, gray):
    if len(faces) != 0:
        x, y, w, h = faces[0]
        roi_gray = gray[y:y + h, x:x + w]
        roi_color = img[y:y + h, x:x + w]
        eyes = eye_cascade.detectMultiScale(roi_gray, 1.05, 10)

        if len(eyes) != 0:
            ex, ey, ew, eh = eyes[0]
            x = faces[0][0] + ex + int(round(ew / 2))
            y = faces[0][1] + ey + int(round(eh / 2)) + 5
            img = cv2.line(img, (320, 240), (x, y), (0, 0, 255), 2)
            img = cv2.putText(img, f'X:{x}  Y:{y}', (5, 30), cv2.FONT_HERSHEY_COMPLEX,
                              1, (0, 255, 0), 2, cv2.LINE_AA)


# init users to avoid error
rand = np.random.random(128)
newUser('Nobody', 'Not Authorized', rand)

def decodeQR(img, pause):
    for code in decode(img):
        rawcode = code.data.decode('utf-8')
        data = rawcode.split(',')
        if len(data) == 4:
            key, cmnd, name, auth = data

            # verify Hash
            valid_codes = []
            datet = dt.datetime.now()
            # Create valid hash for the next 15 seconds
            for i in range(15):
                code = password + (datet - dt.timedelta(seconds=i)).strftime('%m/%d/%y-%H:%M:%S')
                valid_codes.append(hashlib.md5(code.encode()).hexdigest())

            if not ((key not in valid_codes) or (key in usedcodes)):
                if (key in valid_codes) and (key not in usedcodes):
                    usedcodes.append(key)
                    if cmnd == 'nu':
                        print(f'{name} entered as {auth}')
                        newUser(name, auth, returnEncode)  # need closest face encoding (or just one for start)
                    if cmnd == 'ca':
                        changeAuth(name, auth)
                        print(f'{name} changed to {auth}')
                    if cmnd == 'cn':
                        changeName(name, auth)
                        print(f'{name} changed to {auth}')
                    if cmnd == 'pr':
                        if name == 'Pause':
                            pause = True
                            print('Laser Disabled')
                        else:
                            pause = False
                            print('Laser Activated')
    return pause

def changeAuth(name, newAuth):
    users['auth'][users['name'].index(name)] = newAuth

def changeName(oldname, newname):
    users['name'][users['name'].index(oldname)] = newname


pause = False
while True:
    _, img = cap.read()
    #     img = cv2.flip(img, 0)
    returnEncode = facialrec(img, pause)
    pause = decodeQR(img, pause)

    cv2.namedWindow('Source', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Source', 1100, 800)
    cv2.imshow('Source', img)
    k = cv2.waitKey(5) & 0xff
    if k == 27:
        break
cap.release()
cv2.destroyAllWindows()