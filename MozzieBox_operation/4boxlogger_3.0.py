import Adafruit_DHT as dht
import csv
import time
import datetime
import os
import math
import imageio
from picamera import PiCamera
from gpiozero import LED
from gpiozero import PWMLED

# Upgrade: a start function that controls recording start time, see the function for comments
# 1-26 changed line with open(CSVFilePath, 'a+', newline='') as csvfile:
# 2-1 added to the folder name hour+minute
# DEBUG = True
# User variables - sampling variables
# Please define me!!!
EXP_NAME = 'newcode'
UseBox1 = True
UseBox2 = False
UseBox3 = False
UseBox4 = False


savePics = True

# Collecting a picture from each box, each minute
DURATION_RECORDING = 8 # days of recording
LET_THERE_BE_LIGHT = 3 # number of days of light/dark cycle
#NUM_SAMPLES = DURATION_RECORDING * 86,400/COLLECT_PERIOD # number of samples in duration recording days

SUNRISE = 8 #sunrise starts 8am
SUNSET = 20 #sunset starts 8pm
DUSK_PERIOD = 30 #minutes

DHT1_PIN = 21
LED1_PIN = 16
DHT2_PIN = 23
LED2_PIN = 22
DHT3_PIN = 25
LED3_PIN = 24
DHT4_PIN = 27
LED4_PIN = 26


pin7 = LED(4)
pin11 = LED(17)
pin12 = LED(18)



def switchCamera(cam):
    global exposures
    if not(math.isnan(exposures[cam-1])):
#        camera.shutter_speed = exposures[cam-1]
        pass
    if cam == 1:
        pin7.off()
        pin11.off()
        pin12.on()
        i2c = "i2cset -y 1 0x70 0x00 0x04"
        os.system(i2c)
    elif cam == 2:
        pin7.on()
        pin11.off()
        pin12.on()
        i2c = "i2cset -y 1 0x70 0x00 0x05"
        os.system(i2c)
    elif cam == 3:
        pin7.off()
        pin11.on()
        pin12.off()
        i2c = "i2cset -y 1 0x70 0x00 0x06"
        os.system(i2c)
    elif cam == 4:
        pin7.on()
        pin11.on()
        pin12.off()
        i2c = "i2cset -y 1 0x70 0x00 0x07"
        os.system(i2c)
    
    
OUTPUT_DIR = ('/media/pi/KINGSTON/Boxlogger/' + EXP_NAME + '-' +  str(datetime.datetime.now().year) + "-" + str(datetime.datetime.now().month) + "-" + str(datetime.datetime.now().day) + "-" + str(datetime.datetime.now().hour) + "-" + str(datetime.datetime.now().minute))
exposures = [float('nan'),float('nan'),float('nan'),float('nan')]
switchCamera(1)
camera = PiCamera()
camera.resolution = (2000, 1500)
camera.iso = 400
#camera.shutter_speed = 100000
camera.framerate = 10
camera.brightness = 55
camera.contrast = 45
camera.color_effects = (128,128) # this forces the image to be black and white.
camera.awb_mode = 'shade'



pwm1 = PWMLED(LED1_PIN, frequency = 200)
pwm2 = PWMLED(LED2_PIN, frequency = 200)
pwm3 = PWMLED(LED3_PIN, frequency = 200)
pwm4 = PWMLED(LED4_PIN, frequency = 200)

# camera.start_preview(fullscreen=False, window=(10, 10, 600, 600))

DAYS_OF_RUN = 0 # counter for how many days we have been running
CURRENT_DAY = datetime.datetime.now().day
PIC_COUNTER  = 0 # counter for how many pictures we have taken

def led_level():
    currentDT = datetime.datetime.now() # entire datetime object
    global CURRENT_DAY
    global DAYS_OF_RUN
    cday = currentDT.day
    if cday != CURRENT_DAY:
        DAYS_OF_RUN += 1
        CURRENT_DAY = cday
        
    chour = currentDT.hour
    cmin = currentDT.minute
    csec = currentDT.second

    print("Day " + str(DAYS_OF_RUN) + " " + str(chour) +":" + str(cmin))
    if DAYS_OF_RUN <= LET_THERE_BE_LIGHT:
        if chour < SUNRISE:
            return 0 #before sunrise
        elif chour == SUNRISE and cmin < DUSK_PERIOD:
            print("Sun is rising!: " + str(round((cmin/DUSK_PERIOD),2))+"/1")
            return cmin/DUSK_PERIOD #smooth 30min sunrise
        elif chour < SUNSET:
            return 1 # daytime
        elif chour == SUNSET and cmin < DUSK_PERIOD:
            print("Sun is setting!: " + str(round(1-(cmin/DUSK_PERIOD),2))+"/1")
            return 1-(cmin/DUSK_PERIOD) #smooth 30 minute dusk
        else:
            return 0  # 0 brightness at night
    else:
        return 0

if not os.path.exists(OUTPUT_DIR):
    os.mkdir(OUTPUT_DIR)

def takePicture(cam, PIC_COUNTER):
    if savePics:
        switchCamera(cam)
        camera.start_preview(fullscreen=False, window=(10, 10, 600, 600))
        time.sleep(1.5)
        image_filename = os.path.join(OUTPUT_DIR, 'Box{:1d}/Box{:1d}_Pic{:06d}.jpg'.format(cam, cam, PIC_COUNTER))
        camera.stop_preview()
        camera.capture(image_filename)

def getTemp(box,pin):
    CSVFilePath = os.path.join(OUTPUT_DIR, 'Box{:1d}'.format(box), EXP_NAME + 'Box{:1d}_humid.csv'.format(box))
    with open(CSVFilePath, 'a+', newline='') as csvfile:
        writer = csv.writer(csvfile)
        humidity, temperature = dht.read_retry(dht.DHT22, pin, retries = 4)
        dt = str(datetime.datetime.now().replace(microsecond=0))
        if humidity is not None:
            temperature = round(temperature,1)
            humidity = round(humidity,1)
            print('Box' + str(box) + ': Temp=' + str(temperature) + '*C  Humidity=' + str(humidity) + '%')
        else:
            print('Box{:1d}: No data collected'.format(box))
        writer.writerow([dt, temperature, humidity])

def createFolders(box):
    BoxPath = os.path.join(OUTPUT_DIR, 'Box{:1d}'.format(box)) 
    if not os.path.exists(BoxPath):
        os.mkdir(BoxPath)
    with open(os.path.join(BoxPath, (EXP_NAME + 'Box{:1d}_humid.csv'.format(box))), 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['time', 'temp (C)', 'humidity', 'Box{:1d}'.format(box), EXP_NAME])

def setupBox(box):
    createFolders(box)
    switchCamera(box)
    camera.start_preview(fullscreen=False, window=(10, 10, 600, 600))
    pause = input('Setup Box{:1d} and then Press Enter'.format(box))
    camera.stop_preview()
    exposures[box-1] = camera.exposure_speed
    
if UseBox1:
    setupBox(1)
if UseBox2:
    setupBox(2)
if UseBox3:
    setupBox(3)
if UseBox4:
    setupBox(4)

start = False # give start a default value of false
while DAYS_OF_RUN < DURATION_RECORDING:
# for i in range(NUM_SAMPLES):
    # TODO i * COLLECT_PERIOD is a weak approximation for time...come back and improve
    if not start:
        minut = datetime.datetime.now().minute
        hour = datetime.datetime.now().hour
        if minut == 0 and hour == 8:
         start = True # change start to true if the current hour and minute is 8 and 0
    
    level = led_level()
    
    while datetime.datetime.now().second > 1:
        pass
    if datetime.datetime.now().second < 15:
        if UseBox1:
            pwm1.value = level
            getTemp(1,DHT1_PIN)
            if DAYS_OF_RUN >= 0 and start: 
                takePicture(1,PIC_COUNTER) # only when start is changed to be ture, the recording starts

        while datetime.datetime.now().second < 16:
            pass
        
    if 15 <= datetime.datetime.now().second < 30:
        if UseBox2:
            pwm2.value = level
            getTemp(2,DHT2_PIN)
            takePicture(2,PIC_COUNTER)
            
        while datetime.datetime.now().second < 31:
            pass
        
    if 30 <= datetime.datetime.now().second < 45:
        if UseBox3:
            pwm3.value = level
            getTemp(3,DHT3_PIN)
            takePicture(3,PIC_COUNTER)
            
        while datetime.datetime.now().second < 46:
            pass
        
    if 45 <= datetime.datetime.now().second < 60:
        if UseBox4:
            pwm4.value = level
            getTemp(4,DHT4_PIN)
            takePicture(4,PIC_COUNTER)
            
        while datetime.datetime.now().second > 1:
            pass
        
    PIC_COUNTER += 1
        
    
