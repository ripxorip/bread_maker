import RPi.GPIO as GPIO
from flask import Flask, render_template, Response, request
import io
import picamera
from threading import Condition
from w1thermsensor import W1ThermSensor
import neopixel
import board
import threading
import time

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

# App Globals (do not edit)
app = Flask(__name__)
camera = picamera.PiCamera(resolution='640x480', framerate=24)
output = StreamingOutput()
#Uncomment the next line to change your Pi's Camera rotation (in degrees)
#camera.rotation = 90
camera.start_recording(output, format='mjpeg')
sensor = W1ThermSensor()
pixels = neopixel.NeoPixel(board.D18, 30)
pixels.fill((255, 255, 180))
mutex = threading.Lock()

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
GPIO.output(17, 1)


def pid(temperature):
    if temperature < 30.00:
        GPIO.output(17, 1)
    else:
        GPIO.output(17, 0)

def control_thread():
    while True:
        mutex.acquire()
        try:
            temperature = sensor.get_temperature()
        finally:
            mutex.release()
            print("Processing")
            pid(temperature)
            time.sleep(1)

@app.route('/')
def index():
    return render_template('index.html') #you can customze index.html here

@app.route('/temperature')
def temperature():
    mutex.acquire()
    try:
        temperature = sensor.get_temperature()
    finally:
        mutex.release()
    return str(temperature) + ' C'

def gen(output):
    #get camera frame
    while True:
        with output.condition:
            output.condition.wait()
            frame = output.frame
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen(output),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    t = threading.Thread(target=control_thread)
    t.start()
    app.run(host='0.0.0.0', debug=False)
