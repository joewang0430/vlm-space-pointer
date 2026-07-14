"""One-off helper: print whatever the Arduino sends over serial for a
few seconds, used to read debug output from servo_test.ino.
"""

import time
import serial

PORT = "COM3"
BAUD_RATE = 9600
DURATION_SECONDS = 60

with serial.Serial(PORT, BAUD_RATE, timeout=2) as arduino:
    time.sleep(3)  # let the board reset and reach loop()
    end_time = time.time() + DURATION_SECONDS
    while time.time() < end_time:
        line = arduino.readline().decode(errors="replace").strip()
        if line:
            print(line)
