try:
    import RPi.GPIO as GPIO
    import picamera
    import w1thermsensor
    import neopixel
    import board
except ImportError:
    print("Could not import hardware libraries, running as simulator..")
    # Import mockups
    from mock import picamera
    from mock import w1thermsensor
    from mock import neopixel
    from mock import gpio
    GPIO = gpio.gpio
    board = neopixel.board

from flask import Flask, render_template, Response, request
import io
from threading import Condition
import threading
import time
from datetime import datetime

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

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
sensor = w1thermsensor.W1ThermSensor()
pixels = neopixel.NeoPixel(board.D18, 30)
pixels.fill((255, 255, 180))
mutex = threading.Lock()

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)

temperature = 0.00
heater_out = 0.00
Iterm = 0.00

g_data = {'temp': [], 'Iterm': [], 'heater_out': []}

def pwm_thread():
    while True:
        period = 5.00
        time_active = heater_out * period
        time_passive = (1.00 - heater_out) * period
        if time_passive < 0:
            time_passive = 0
        if time_active < 0:
            time_active = 0

        GPIO.output(17, 1)
        time.sleep(time_active)
        GPIO.output(17, 0)
        time.sleep(time_passive)

def pid(temperature):
    global heater_out
    global Iterm

    set_point = 28.00
    error = set_point - temperature

    kp = 0.4
    ki = 0.001

    Iterm += (error * ki)

    # Windup
    if (Iterm > 1.00):
        Iterm = 1.00
    elif Iterm < 0.00:
        Iterm = 0.00

    heater_out = kp * error + Iterm

    print("Iterm: " + str(Iterm))

    if heater_out > 1.00:
        heater_out = 1.00
    elif heater_out < 0.00:
        heater_out = 0.00

    print("heater out: " + str(heater_out))

    g_data['temp'].append(temperature)
    g_data['Iterm'].append(Iterm)
    g_data['heater_out'].append(heater_out)


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

@app.route('/graph')
def graph():
    return render_template('graph.html')

@app.route('/graph_data')
def graph_data():
    # Return the data to be plotted
    data = []
    i = 1
    for g in g_data:
        data.append({'xaxis': 'x'+str(i), 'yaxis': 'y'+str(i), 'y': g_data[g], 'x': list(range(1, len(g_data[g]))), 'mode': 'lines', 'name': g})
        i += 1
    return {'data': data}

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
