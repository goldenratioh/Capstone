from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import cv2
import numpy as np
import facenet
import detect_face
import os
import time
import pickle
from PIL import Image
import paho.mqtt.client as mqtt
import tensorflow.compat.v1 as tf
from face_cut import Face_cut
import pyrebase
from PIL import ImageFont, ImageDraw, Image

video= 0
modeldir = './model/20180402-114759.pb'
classifier_filename = './class/classifier.pkl'
npy='./npy'
train_img="./train_img"




#db 정보####################################################

config = {
    "apiKey": "AIzaSyAl-oNSvBpWa8GGnRSzUKZXKeRFXtClfnQ",
    "authDomain": "capstone-aae4f.firebaseapp.com",
    
     "databaseURL": "https://capstone-aae4f.firebaseio.com",
    "projectId": "capstone-aae4f",
    "storageBucket": "capstone-aae4f.appspot.com",
 
  }


#####################firebase 연동#########################
firebase_storage = pyrebase.initialize_app(config)
storage = firebase_storage.storage()

#############################################################



def uploadToDataBase(path_on_cloud,path_local):

        storage.child(path_on_cloud).put(path_local)

def on_connect(client, userdata, flag, rc):
        print("connect")
        client.subscribe("hansung/pc/imgdownload", qos = 0)


def on_message(client, userdata, msg) :
        global downloadFinsh 

        if msg.topic == "hansung/pc/imgdownload":
            print("download done")
            downloadFinsh = True
            face_camera.setStop(True)

broker_ip = "113.198.84.40" # 현재 이 컴퓨터를 브로커로 설정

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(broker_ip, 80)
client.loop_start()

#client.loop_forever()

act =""


class Face_recognition():

    
    def __init__(self):
        self.stop = False
        print('face recognition 실행')
        


    def setStop(self, stop):
        self.stop = stop

    




    def run(self):
        with tf.Graph().as_default():
            gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.6)
            sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options, log_device_placement=False))
            with sess.as_default():
                pnet, rnet, onet = detect_face.create_mtcnn(sess, npy)
                minsize = 30  # minimum size of face
                threshold = [0.7,0.8,0.8]  # three steps's threshold
                factor = 0.709  # scale factor
                margin = 44
                batch_size =100 #1000
                image_size = 182
                input_image_size = 160
                HumanNames = os.listdir(train_img)
                HumanNames.sort()
                print('Loading Model')
                facenet.load_model(modeldir)
                images_placeholder = tf.get_default_graph().get_tensor_by_name("input:0")
                embeddings = tf.get_default_graph().get_tensor_by_name("embeddings:0")
                phase_train_placeholder = tf.get_default_graph().get_tensor_by_name("phase_train:0")
                embedding_size = embeddings.get_shape()[1]
                classifier_filename_exp = os.path.expanduser(classifier_filename)
                with open(classifier_filename_exp, 'rb') as infile:
                    (model, class_names) = pickle.load(infile,encoding='latin1')

                video_capture = cv2.VideoCapture("http://192.168.0.61:8090/stream/video.mjpeg")
                #video_capture = cv2.VideoCapture(0)
                print('Start Recognition')
                flag = 0 #인식이 성공했을 때 mqtt publish를 한번만 하기 위한 변수
                while True:
                    if self.stop == False:
                        ret, frame = video_capture.read()
                        #frame = cv2.resize(frame, (0,0), fx=0.5, fy=0.5)    #resize frame (optional)
                        timer =time.time()
                        if frame.ndim == 2:
                            frame = facenet.to_rgb(frame)
                        bounding_boxes, _ = detect_face.detect_face(frame, minsize, pnet, rnet, onet, threshold, factor)
                        faceNum = bounding_boxes.shape[0]
                        if faceNum > 0:
                            det = bounding_boxes[:, 0:4]
                            img_size = np.asarray(frame.shape)[0:2]
                            cropped = []
                            scaled = []
                            scaled_reshape = []
                            for i in range(faceNum):
                                emb_array = np.zeros((1, embedding_size))
                                xmin = int(det[i][0])
                                ymin = int(det[i][1])
                                xmax = int(det[i][2])
                                ymax = int(det[i][3])
                                try:
                                    # inner exception
                                    if xmin <= 0 or ymin <= 0 or xmax >= len(frame[0]) or ymax >= len(frame):
                                        print('Face is very close!')
                                        continue
                                    cropped.append(frame[ymin:ymax, xmin:xmax,:])
                                    cropped[i] = facenet.flip(cropped[i], False)
                                    scaled.append(np.array(Image.fromarray(cropped[i]).resize((image_size, image_size))))
                                    scaled[i] = cv2.resize(scaled[i], (input_image_size,input_image_size),
                                                            interpolation=cv2.INTER_CUBIC)
                                    scaled[i] = facenet.prewhiten(scaled[i])
                                    scaled_reshape.append(scaled[i].reshape(-1,input_image_size,input_image_size,3))
                                    feed_dict = {images_placeholder: scaled_reshape[i], phase_train_placeholder: False}
                                    emb_array[0, :] = sess.run(embeddings, feed_dict=feed_dict)
                                    predictions = model.predict_proba(emb_array)
                                    best_class_indices = np.argmax(predictions, axis=1)
                                    best_class_probabilities = predictions[np.arange(len(best_class_indices)), best_class_indices]
                                    if best_class_probabilities>0.87:
                                        cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)    #boxing face
                                        for H_i in HumanNames:
                                            if HumanNames[best_class_indices[0]] == H_i:
                                                result_names = HumanNames[best_class_indices[0]]
                                                if best_class_probabilities[0] > 0.90:
                                                    if flag != result_names: #정확도가 90% 넘으면 안드로이드에 토픽 전송

                                                        #도어락을 할경우 
                                                        
                                                            print("door")
                                                            client.publish("hansung/pc/doorlock","success",qos=0)
                                                       
                                                       
                                                            flag = result_names



                                                            
                                                            print("mqtt 전송")
                                                            ret, frame = video_capture.read() # 사진 촬영
                                                            input_datadir = './full'
                                                            img_name = input_datadir+"/"+result_names+'_full.jpg'
                                                            cv2.imwrite(img_name, frame) # 사진 저장
                                                            print(img_name)
                                                            Face_cut.facecrop(img_name) #여기서 저장한 사진을 얼굴 부위만 해서 잘라서 저장.

                                                            print("모든 이미지 저장완료")
                                                        
                                                            path_on_cloud_faceCut ="webcamCapture/"+result_names+"/"+"faceCut.jpg"
                                                            path_on_cloud_faceFull ="webcamCapture/"+result_names+"/"+"faceFull.jpg"
                                                            

                                                            path_on_local_faceCut= "./full/"+result_names+"_full_cut.jpg"
                                                            path_on_local_faceFull="./full/"+result_names+"_full.jpg"

                                                            print("이미지 경로 설정 완료")
                                                            uploadToDataBase(path_on_cloud_faceCut,path_on_local_faceCut)

                                                            print("cut")
                                                            uploadToDataBase(path_on_cloud_faceFull,path_on_local_faceFull)
                                                            print("full")

                                                            print("db에 저장을 완료하였습니다")
                                                            print(result_names + "보낸이름")
                                                            client.publish("hansung/pc/webCamCapture",result_names)
                                                            print("dwdwdw")

                                                            ### mqtt pub######




                                                        
                                                print("Predictions : [ name: {} , accuracy: {:.3f} ]".format(HumanNames[best_class_indices[0]],best_class_probabilities[0]))
                                                
                                                cv2.rectangle(frame, (xmin, ymin-20), (xmax, ymin-2), (0, 255,255), -1)
                                                #cv2.putText(frame, result_names, (xmin,ymin-5), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                                                 #               1, (0, 0, 0), thickness=1, lineType=1)
                                                cv2.putText(frame, result_names, (xmin,ymin-5), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                                                                1, (0, 0, 0), thickness=1, lineType=1)

                                    else :
                                        cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
                                        cv2.rectangle(frame, (xmin, ymin-20), (xmax, ymin-2), (0, 255,255), -1)
                                        cv2.putText(frame, "unKnown", (xmin,ymin-5), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                                                            1, (0, 0, 0), thickness=1, lineType=1)
                                except:   

                                    print("except")

                        endtimer = time.time()
                        fps = 1/(endtimer-timer)
                        cv2.rectangle(frame,(15,30),(135,60),(0,255,255),-1)
                        cv2.putText(frame, "fps: {:.2f}".format(fps), (20, 50),cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                        cv2.imshow('Face Recognition', frame)
                        key= cv2.waitKey(1)
                        if key== 113: # "q"
                            break
                    elif self.stop:
                        print('face recognition stop')
                        break

                video_capture.release()
                cv2.destroyAllWindows()


