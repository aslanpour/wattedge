from pijuice import PiJuice #sudo apt-get install pijuice-gui
import RPi.GPIO as GPIO

relay_pin = 20
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
pijuice = PiJuice(1, 0x14)

GPIO.setmode(GPIO.BCM)
GPIO.setup(relay_pin, GPIO.LOW)

#GPIO.setup(relay_pin, GPIO.HIGH)

print("END")