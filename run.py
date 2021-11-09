import RPi.GPIO as GPIO
import board
import neopixel

pixels = neopixel.NeoPixel(board.D18, 30)


pixels.fill((255, 255, 255))

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
GPIO.output(17, 0)
