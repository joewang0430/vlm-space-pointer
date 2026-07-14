"""Serial communication test: send LED on/off commands to the Arduino
over COM3 and print back whatever the Arduino reports.

Requires arduino/serial_test/serial_test.ino to already be uploaded.
"""

import time
import serial

PORT = "COM3"
BAUD_RATE = 9600


def main():
    with serial.Serial(PORT, BAUD_RATE, timeout=2) as arduino:
        # Opening the serial port resets the Arduino; give it time to boot.
        time.sleep(2)

        for command in ["1", "0", "1", "0"]:
            arduino.write(command.encode())
            print(f"sent: {command}")
            time.sleep(0.5)
            response = arduino.readline().decode(errors="replace").strip()
            print(f"received: {response}")
            time.sleep(1)


if __name__ == "__main__":
    main()
