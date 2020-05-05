import requests
from requests.exceptions import HTTPError
import cv2
import base64
from imageio import imread
import matplotlib.pyplot as plt
import time
import keyboard

def cam():
    try:
        response = requests.get('http://127.0.0.1:5002/face_recognition')
        my = response.json()['data']
        mys= my.split('*')
        i=0
        
        for im in mys:
            jpg_original=base64.b64decode(im)
            with open("test"+str(i)+".jpg", 'wb') as f_output:
                f_output.write(jpg_original)
            i=i+1
        response.raise_for_status()
    except Exception as err:
        print('Other error occurred: {err}')
        return 
    else:
        print('Success!')
 


def loop_mov():
    print("DIGITARE CTRL+C PER USCIRE")
    while True:
        try:
            url = 'http://127.0.0.1:5002/movement_detection'
            response = requests.get(url)
            my = response.json()['data']
            print(my)
            time.sleep(5)
        except Exception as err:
            print('Other error occurred: {err}')
            return
        except KeyboardInterrupt:
            return
        
        
def main():
    while True:
        try:
            print("DIGITARE 'mov' PER AVERE INFORMAZIONI DI MOVIMENT, 'cam' PER SALVARE LE FACCE RICONOSCIUTE,'CTRL+C' per uscire")
            info = input()
            if(info=="mov"):
                loop_mov()
            if(info=="cam"):
                cam()
        except KeyboardInterrupt:
            return





if __name__== "__main__":
    main()
