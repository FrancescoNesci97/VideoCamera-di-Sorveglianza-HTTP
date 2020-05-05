import cv2
import sqlite3
import base64
import logging
import threading
import time
import face_recognition
from flask import Flask
from flask_restful import Resource, Api
from sqlalchemy import create_engine
from json import dumps
from flask import jsonify
from imageio import imread
import matplotlib.pyplot as plt
import io
import numpy as np
from PIL import Image
from flask import request
import sys

movement=[False]*100
app = Flask(__name__)
api = Api(app)
mode = 0

class face(Resource):
    def get(self):
        global mode
        try:
            if mode==2:
                return "error"
            connec = sqlite3.connect('images.db')
            cursor = connec.cursor()
            cursor.execute("""SELECT * FROM faces""")
            connec.commit()
            faces12=cursor.fetchall()
            
        except sqlite3.Error as error:
            print("errore nell'accesso al database", error)
        finally:
            if(connec):
                connec.close()
                print("la connessione è stata chiusa")
        i=0
        text_to_send=""
        for face in faces12:
            text_to_send=text_to_send+face[1]+"*"
        return {'data':text_to_send[:-1]}
    
class move(Resource):
    def get(self):
        global mode
        if(mode==1):
            return "error"
        text_to_send = control_movement()
        return {'data':text_to_send}
 

api.add_resource(face, '/face_recognition') 
api.add_resource(move, '/movement_detection') 

def control_movement():
    global movement
    for i in movement:
        if(i==True):
            return "movement detected"
    return "not movement"

def Http_Server(str_to_print):
    print(str_to_print)
    app.run(port='5002')
   
def encode_image(img):
    retval, buffe = cv2.imencode('.jpg', img) 
    btext = base64.b64encode(buffe)
    text= btext.decode()
    return text

def decode_image(img):
    jpg_original = base64.b64decode(img)
    return cv2.cvtColor(np.array(Image.open(io.BytesIO(jpg_original))), cv2.COLOR_BGR2RGB)

def array_to_string(arr):
    text = ""
    for a in arr:
        text = text+str(a)+"/"
    return text[:-1]

def string_to_array(tex):
    tf=tex.split('/')
    arg= list()
    for t in tf:
        arg.append(float(t))
    return np.array(arg)
        



def movement_detection(str_to_print):
    sdThresh = 10
    font = cv2.FONT_HERSHEY_SIMPLEX
    trigger = 5
    cap=cv2.VideoCapture(0)
    _, frame1 = cap.read()
    _, frame2 = cap.read()
    increment=0
    global movement
    while True:
        #ogni tot cicli si azzera increment in modo da avere una lista movement FIFO e avere un'informazione sui movimenti avvenuti negli ultimi 100 cicli
        if(increment==100):
            increment=0
        diff = cv2.absdiff(frame1,frame2)
        gray = cv2.cvtColor(diff,cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray,(5,5),0)
        _,thresh = cv2.threshold(blur,25,255,cv2.THRESH_BINARY)
        mean = cv2.mean(thresh)#se la media e' maggiore del trigger vuol dire che una parte significativa dell'immagine e' cambiata e viene inviato un segnale 
        contours,_= cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
        #tutti i tipi di movimenti sono mostrati nella finestra,ma quelli più piccoli non vengono immagazzinati dal server e non saranno ricevuti dal client
        cv2.drawContours(frame1,contours,-1,(0,255,0),2)
        cv2.imshow("feed",frame1)
        if mean[0]>trigger:
        #il segnale di avvertimento viene inviato se  piu' dell'1% dell'immagine ha una variazione di 25(valore di threshold) in modo da ignorare movimenti non significativi,se questo avviene vuol dire che in più dell'1% dei pixel abbiamo avuto una variazione significativa 
            print("movement detected")
            movement[increment]=True
        else:
            print("NO movement")
            movement[increment]=False
        frame1= frame2
        ret,frame2 = cap.read()
        increment=increment+1
        if cv2.waitKey(40) == 27:
            break
    

    cv2.destroyAllWindows()
    cap.release()


    
    

def dbManagment(face,cursor,connection):
    resized2 = cv2.resize(face, (0, 0), fx=0.25, fy=0.25)
    rgb2 = cv2.cvtColor(resized2, cv2.COLOR_BGR2RGB)
    face_locations2 = face_recognition.face_locations(rgb2,2)
    face_encodings2 = face_recognition.face_encodings(rgb2,face_locations2)
    cursor.execute("""SELECT * FROM faces""")
    faces=cursor.fetchall()
    count = len(faces)
    for recog in face_encodings2:
        ctrl=0
        for entry in faces:
            results = face_recognition.compare_faces([recog],string_to_array(entry[2]))
            if(results[0]):
                ctrl=1
                break
        if(ctrl==0):
            to_send = encode_image(face)
            cursor.execute('''INSERT INTO faces VALUES(?,?,?)''',(count,to_send,array_to_string(recog)))
            connection.commit()
  



def camera(str_to_print):
    face_cascade=cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

    i=0
    try:
        connection = sqlite3.connect('images.db')
        query = '''CREATE TABLE IF NOT EXISTS faces (id INTEGER,img TEXT,feature TEXT)'''
        cursor=connection.cursor()
        print("Successfully Connected to SQLite")
        cursor.execute(query)
        connection.commit()
        print("SQLite table created")
        cap=cv2.VideoCapture(0)
        global sem
        counter=0
        while True:
            ret,img=cap.read()
            gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
            faces=face_cascade.detectMultiScale(gray,1.3,5)
            cop = img.copy()
            for (x,y,w,h) in faces:
                cop = cv2.rectangle(cop,(x,y),(x+w,y+h),(255,0,0),2)
            #processo solo 1 frame ogni 3 per velocizzare il programma
            cv2.imshow('img',cop)
            if(counter%3==0):
                dbManagment(img,cursor,connection)
            counter=counter+1
            if cv2.waitKey(40) == 27:
                break
   
        cv2.destroyAllWindows()
        cap.release()
    except sqlite3.Error as error:
        print("errore nella creazione della tabella", error)
    finally:
        if(connection):
            connection.close()
            print("connessione chiusa")



def main():
    global mode
    time.sleep(0.5)
    try:
        print("DIGITARE 'cam' PER LA MODALITA' FACE RECOGNITION,DIGITARE 'det' PER LA MODALITA' MOVEMENT DETECTION,'CTRL+C' PER USCIRE")
        ask = input()
        if(ask=="cam"):
            mode=1
            api = threading.Thread(target=Http_Server,args=("I will comunicate with the client",))
            api.daemon=True
            api.start()
            camera("I will save data on the database")
        elif(ask=="det"):
            mode=2
            api = threading.Thread(target=Http_Server,args=("I will comunicate with the client",))
            api.daemon=True
            api.start()
            movement_detection("I will detect movement")
        else:
            print("COMANDO ERRATO")
    except KeyboardInterrupt:
        return
    
        
if __name__== "__main__":
    main()
