import RPi.GPIO as GPIO
import board
import neopixel
from w1thermsensor import W1ThermSensor

pixels = neopixel.NeoPixel(board.D18, 30)


pixels.fill((255, 255, 180))

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
GPIO.output(17, 1)


sensor = W1ThermSensor()
temperature = sensor.get_temperature()
print("The temperature is %s celsius" % temperature)
