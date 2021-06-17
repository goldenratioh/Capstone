import paho.mqtt.client as mqtt


from data_preprocess import Data_preprocess

from train_main import Train_face

from face_recognition import Face_recognition


act = ""

def on_connect(client, userdata, flag, rc):
        print("connect")
        client.subscribe("hansung/pc/imgdownload", qos = 0)


def on_message(client, userdata, msg) :
        global downloadFinsh 
        global act

        if msg.topic == "hansung/pc/imgdownload":
            print("download done")
            act = str(msg.payload)
            downloadFinsh = True
            face_camera.setStop(True)
             
        

broker_ip = "113.198.84.40" # 현재 이 컴퓨터를 브로커로 설정

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(broker_ip, 80)
client.loop_start()

#client.loop_forever()
if __name__ == '__main__':
        print("main")
        downloadFinsh = False


        #카메라 먼저 실행 시킴
        face_camera = Face_recognition()
        face_camera.run()

        while True:
                #print(downloadFinsh)
                if downloadFinsh == True:
                        print(" 학습 시작")
                        Data_preprocess.run('1')
                        Train_face.run('1')
                        
                        downloadFinsh = False
                        face_camera = Face_recognition()
                        face_camera.run()
          

