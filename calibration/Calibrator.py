import cv2
import pickle
from .Functions import *
import random
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os
import time
class Predictor:
    def __init__(self, args):
        self.image_path = args.image
        self.data = args.calib_data
        o_x, o_y = args.origin 
        self.origin = (float(o_x), float(o_y))
        self.out_dir = args.out_dir
        try:
            self.img = cv2.imread(self.image_path)

            plt.imshow(self.img)
            plt.show()
            corners, appr_edge = pickle.load(open(self.data, 'rb'))
            self.corners = corners
            self.appr_edge = appr_edge
        except:
            raise Exception('calibration data or image not found, try retrain with \n python train.py --image <link-image>')
    
    def predict(self, x,y):
        try: 
            img_cp = self.img.copy()
            cv2.circle(img_cp, (int(x),int(y)), 5, (0,0,255), -1)
            lt = None
            rt = None
            lb = None 
            rb = None
            lt_dis = 9999
            rt_dis = 9999
            lb_dis = 9999
            rb_dis = 9999
            for c in self.corners:
                dis = distance(c, (x,y))
                if c[0] < x and c[1] < y and dis < lt_dis:
                    lt = c
                    lt_dis = dis
                elif c[0] > x and c[1] < y and dis < rt_dis:
                    rt = c
                    rt_dis = dis 
                elif c[0] < x and c[1] > y and dis < lb_dis:
                    lb = c
                    lb_dis = dis
                elif c[0] > x and c[1] > y and dis < rb_dis:
                    rb = c
                    rb_dis = dis
            real_coor = []
            for c in [lt, rt, lb, rb]:
                x_real = roundToPoint5((c[0] - self.origin[0])/self.appr_edge)*3
                y_real = roundToPoint5((c[1] - self.origin[1])/self.appr_edge)*3
                real_coor.append((x_real, y_real))
                cv2.circle(img_cp, (int(c[0]), int(c[1])), 3, (255,0,0), -1)
            cv2.imwrite('./img.jpg', img_cp)
            real_lt, real_rt, real_lb, real_rb = real_coor
            top_frac = (x - lt[0])/(rt[0]-lt[0])
            bot_frac = (x - lb[0])/(rb[0]-lb[0])
            top = (x, lt[1] + top_frac*(rt[1] - lt[1]))
            real_top = (real_lt[0] + top_frac*(real_rt[0] - real_lt[0]), real_lt[1] + top_frac*(real_rt[1] - real_lt[1]))
            
            bot = (x, lb[1] + bot_frac*(rb[1] - lb[1]))
            real_bot = (real_lb[0] + bot_frac*(real_rb[0]- real_lb[0]), real_lb[1] + top_frac*(real_rb[1] - real_lb[1]))

            tb_frac = (y-top[1])/(bot[1]-top[1])
            real_x = real_top[0]+ tb_frac*(real_bot[0]-real_top[0])
            real_y = real_top[1] + tb_frac*(real_bot[1] - real_top[1])
            cv2.putText(img_cp,"{real_x:.2f}, {real_y:.2f}".format(real_x=real_x,real_y=real_y), (int(x), int(y)),cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), thickness= 3)
            #print(real_lt, real_rt)
            #print(real_top)
            #print(real_lb, real_rb)
            #print(real_bot)
            #print(x, y)
            #print(real_x, real_y)
            #cv2.circle(img_cp, (int(top[0]), int(top[1])), 3, (0,0,255), -1)
            #cv2.circle(img_cp, (int(bot[0]), int(bot[1])), 3, (0,0,255), -1)
            #plt.imshow(img_cp)
            #plt.show()
            cv2.imwrite(self.out_dir+ self.image_path.split('/')[-1], img_cp)
            return real_x, real_y
        except:
            raise Exception('object coordinates not on working area')

class Trainer:
    def __init__(self, args):
        self.image_path = args.image
        self.out_dir = args.out_dir
        try:
            self.img = cv2.imread(self.image_path)
        except: 
            raise Exception('image not found')
    def train(self):
        img_gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        dst = cv2.Canny(img_gray, 50, 200, None, 3)
        # Copy edges to the images that will display the results in BGR
        cdstP = cv2.cvtColor(dst, cv2.COLOR_GRAY2BGR)

        linesP = cv2.HoughLinesP(dst, 1, np.pi / 180, 50, None, 80, 50)    
        #print(linesP)
        columns = []
        rows = []
        if linesP is not None:
            for i in linesP:
                l = i[0]
                if isColumn(l): 
                    columns.append(l)
                    cv2.line(cdstP, (l[0], l[1]), (l[2], l[3]), (0,0,255), 1, cv2.LINE_AA)
                else:
                    rows.append(l)
                    cv2.line(cdstP, (l[0], l[1]), (l[2], l[3]), (0,0,255), 1, cv2.LINE_AA)
        #print(len(rows))
        #print(len(columns))
        corners = []
        for r in rows:
            for c in columns:
                b,c1 = colQuad(c)
                a, c2 = rowQuad(r)
                if (r[0] + b*r[1] + c1)*(r[2]+b*r[3] +c1) < 0 and (a*c[0] + c[1] + c2)*(a*c[2]+c[3] +c2) < 0:  
                    x, y = cross((b,c1), (a,c2))
                    checked = False 
                    for i, p in enumerate(corners):
                        if distance(p, (x,y))< 5:
                            #print(distance(p, (x,y)))
                            corners[i] = ((x+ p[0])/2, (y+p[1])/2)
                            checked = True
                            break
                    if not checked:        
                        corners.append((x,y))
        random.seed()
        mins = []
        for i in range(3):
            id = random.randrange(0, len(corners))
            #print(id)
            min = 9999
            for j,c in enumerate(corners):
                dis = distance(c, corners[id])
                if dis < min and dis > 0:
                    min = dis
            mins.append(min)
        
        appr_edge_length =  np.mean(mins)
        #print(appr_edge_length)
        
        saveData = (corners, appr_edge_length)
        pickle.dump(saveData, open('./calibration/calib.pkl', 'wb'))
        for i, (x, y) in enumerate(corners):
            cv2.circle(self.img, (int(x),int(y)), 5, (0,0, 255), -1)
            #cv2.putText(self.img, str(i), (int(x),int(y)),cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)
        plt.imshow(self.img)
        plt.show()
        cv2.imwrite(self.out_dir + self.image_path.split('/')[-1], self.img)
        return 0


class UndistortMethodTester:
    def __init__(self, args):
        self.image_path = args.image
        self.out_dir = args.out_dir
        self.dataset_path = args.distortedImagePath
        try:
            self.img = cv2.imread(self.image_path, 0)
            corners_path = './calibration/corners.tsv'
            corners = pd.read_csv(corners_path, sep = '\t', header=None).to_numpy().T.reshape(-1)
            print(corners.shape)
            corners = np.array([np.array([np.float32(pairs.split(', ')[0]), np.float32(pairs.split(', ')[1])]) for pairs in corners]).reshape(-1, 1, 2)
            #print(corners.shape)
            stime = time.time()
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners2 = cv2.cornerSubPix(self.img, corners, (11,11),  (-1, -1), criteria)
            #print(corners2)
            objp = np.zeros((10*18, 3), np.float32)
            objp[:, :2] = np.mgrid[0:10, 0:18].T.reshape(-1,2)
            #print(objp)
            #cv2.drawChessboardCorners(self.img, (10, 18), corners2, True)
            #cv2.imshow('img', self.img)
            #cv2.waitKey()
            etime = time.time()
            print(etime - stime)
            self.objectpoints = [objp]
            self.imgpoints = [corners2]
        except: 
            raise Exception('image not found')
    def undistort(self):
        s1time = time.time()
        ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(self.objectpoints, self.imgpoints, self.img.shape[::-1], None, None)
        h, w = self.img.shape[:2]
        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (w,h), 1, (w,h))
        #print(roi)
        s2time = time.time()
        print(s2time - s1time)
        print('alo')
        times = []
        for i in os.listdir(self.dataset_path):
            stime = time.time()
            path = os.path.join(self.dataset_path, i)
            img = cv2.imread(path)
            dst = cv2.undistort(img, mtx, dist, None, newcameramtx)
            x, y, w, h = roi
            dst = dst [y:y+h, x: x+ w]
            etime = time.time()
            times.append(stime - etime)
            #plt.imshow(img)
            #plt.show()
            #cv2.imwrite(path, dst)
        ftime = np.mean(times)
        print(ftime)
