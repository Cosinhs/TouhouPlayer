# -*- coding: utf-8 -*- 
import win32api, win32con, win32gui, win32ui
import numpy as np
from matplotlib import pyplot as plt
from PIL import Image, ImageChops, ImageOps
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
import cv2 as cv
import os
import time
import numpy  
import thread

import Tkinter
# Coordinates for gameplay area 
#root = Tkinter.Tk()
#root.title('th06_imgget')        #窗口标题
#root.resizable(False, False)    #固定窗口大小
#windowWidth = 800               #获得当前窗口宽
#windowHeight = 500              #获得当前窗口高
#screenWidth,screenHeight = root.maxsize()     #获得屏幕宽和高
#geometryParam = '%dx%d+%d+%d'%(windowWidth, windowHeight, (screenWidth-windowWidth)/2, (screenHeight - windowHeight)/2)
#root.geometry(geometryParam)    #设置窗口大小及偏移坐标


GAME_RECT = {'x0': 35, 'y0': 42, 'dx': 480, 'dy': 560}
def take_screenshot(x0, y0, dx, dy): #截图
    """
    Takes a screenshot of the region of the active window starting from
    (x0, y0) with width dx and height dy.
    """

    hwnd = win32gui.GetForegroundWindow()   # Window handle
    wDC = win32gui.GetWindowDC(hwnd)        # Window device context
    dcObj = win32ui.CreateDCFromHandle(wDC)
    cDC = dcObj.CreateCompatibleDC()

    dataBitMap = win32ui.CreateBitmap()     # PyHandle object
    dataBitMap.CreateCompatibleBitmap(dcObj, dx, dy)
    cDC.SelectObject(dataBitMap)
    cDC.BitBlt((0,0),(dx, dy) , dcObj, (x0, y0), win32con.SRCCOPY)
    image = dataBitMap.GetBitmapBits(1)

    dcObj.DeleteDC()
    cDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, wDC)

    return Image.frombuffer("RGBA", (480, 560), image, "raw", "RGBA", 0, 1)

class Radar(object):
    def __init__(self, (hit_x, hit_y)):
        self.x0 = GAME_RECT['x0']
        self.y0 = GAME_RECT['y0']
        self.dx = GAME_RECT['dx']
        self.dy = GAME_RECT['dy']

        # TODO: Keep updating center to match character's hitbox
        self.center_x, self.center_y = (hit_x, hit_y)

        self.apothem = 50         # Distance within which to check for hostiles
        self.curr_fov = take_screenshot(self.x0, self.y0, self.dx, self.dy)
        self.obj_dists = (np.empty(0), np.empty(0))  # distances of objects in fov
        self.blink_time = .01           # Pause between screenshots
        self.diff_threhold = 90        # Diffs above this are dangerous

        # TODO: Call self.scan_fov only when self.curr_fov is updated
        self.scanner = LoopingCall(self.scan_fov)

    def update_fov(self):
        """Takes a screenshot and makes it the current fov."""
        # TODO: Only need to record the part we actually examine in scan_fov
        self.curr_fov = take_screenshot(self.x0, self.y0, self.dx, self.dy)
        #img = numpy.array(self.curr_fov) 
        

        
        # self.curr_fov.show()

    def get_diff(self):
        """Takes a new screenshots and compares it with the current one."""
        # time.sleep(.03) # TODO: Make this non-blocking
        old_fov = self.curr_fov
        # old_fov.show()
        self.update_fov()
        # self.curr_fov.show()
        diff_img = ImageChops.difference(old_fov, self.curr_fov)
        #diff_img.show()
        return ImageOps.grayscale(diff_img)

    def scan_fov(self):
        """
        Updates self.object_locs with a NumPy array of (x, y) coordinates
        (in terms of the current fov) of detected objects.
        """
        diff_array = np.array(self.get_diff())

        # Get the slice of the array representing the fov
        # NumPy indexing: array[rows, cols]
        x = self.center_x
        y = self.center_y
        apothem = self.apothem
        # Look at front, left, and right of hitbox
        fov_array = diff_array[x-apothem:x+apothem, y-apothem:y]
        fov_center = fov_array[fov_array[0].size/2]

        # Zero out low diff values; get the indices of non-zero values.
        # Note: fov_array is a view of diff_array that gets its own set of indices starting at 0,0
        fov_array[fov_array < self.diff_threhold] = 0
        #print np.nonzero(fov_array)
        obj_locs = np.transpose(np.nonzero(fov_array))
        #print obj_locs, obj_locs.shape

        # Update self.obj_dists with distances of currently visible objects
        if obj_locs.size > 0:
            self.obj_dists = self.get_distance(obj_locs, fov_center)
        else:
            self.obj_dists = (np.empty(0), np.empty(0))
        #print(self.obj_dists)

    def get_distance(self, locs, reference):
        """Get horizontal and vertical distances of objects in fov as a pair
        of NumPy arrays."""
        h_dists = (locs[:, 0] - reference[0])
        v_dists = (locs[:, 1] - reference[1])
        #print(h_dists[0])
        return (h_dists, v_dists)

    def start(self):
        self.curr_img = self.update_fov()
        
        self.scanner.start(self.blink_time, False)
        def opencvimg( threadName, delay):
            #img_gif = Tkinter.BitmapImage('temp.bmp')
            #label_img = Tkinter.Label(root, image = img_gif)
            #label_img.pack()
            #root.mainloop()

            while 1:
                cvimg = cv.cvtColor(numpy.asarray(self.curr_fov),cv.COLOR_RGB2BGR)  
                #cvimg = numpy.asarray(self.get_diff())  
                #im_at_mean = cv.adaptiveThreshold(im_gray, 255, cv.ADAPTIVE_THRESH_MEAN_C, cv.THRESH_BINARY, 5, 7)
                cv.resizeWindow("OpenCV", 480, 520);
                cv.imshow("OpenCV",cvimg)
                cv.waitKey(1)
                #cv.destroyAllWindows()
        try:
            thread.start_new_thread( opencvimg, ("Thread-1", 2, ) )
        except:
            print "Error: unable to start thread"

    
def main():
    radar = Radar((192, 385))
    
    #reactor.callWhenRunning(cv.imshow("OpenCV",cvimg))
    reactor.callWhenRunning(radar.start)
    reactor.run()

    # start = time.time()
    # radar.start()
    # arr = radar.scan_fov()
    # # print(arr)
    # print(time.time() - start)

if __name__ == '__main__':
    main()
