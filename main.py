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
from datetime import datetime

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

temperature = 0.00
heater_out = 0.00

def pwm_thread():
    while True:
        period = 5.00
        time_active = heater_out * period
        time_passive = (1.00 - heater_out) * period
        GPIO.output(17, 1)
        time.sleep(time_active)
        GPIO.output(17, 0)
        time.sleep(time_passive)

def pid(temperature):
    global heater_out

    set_point = 30.00
    error = set_point - temperature
    kp = 0.4

    heater_out = kp * error

    print("heater out: " + str(heater_out))

    if heater_out > 1.00:
        heater_out = 1.00
    elif heater_out < 0.00:
        heater_out = 0.00


def control_thread():
    global temperature
    while True:
        try:
            temperature = sensor.get_temperature()
            pid(temperature)
        except w1thermsensor.errors.SensorNotReadyError:
            pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/temperature')
def temperature():
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

    t_pwm = threading.Thread(target=pwm_thread)
    t_pwm.start()

    app.run(host='0.0.0.0', debug=False)
