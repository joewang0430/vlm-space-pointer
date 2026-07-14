"""Combined test: toggles the laser on/off over serial while the
Arduino (running arduino/combined_test/combined_test.ino) sweeps the
pan servo continuously in the background -- lets both be re-verified
together after re-wiring.
"""

import time
import serial

PORT = "COM3"
BAUD_RATE = 9600


def main():
    with serial.Serial(PORT, BAUD_RATE, timeout=2) as arduino:
        time.sleep(2)  # let the board reset and reach loop()

        for command in ["1", "0", "1", "0"]:
            arduino.write(command.encode())
            print(f"sent: {command}")
            time.sleep(0.5)
            response = arduino.readline().decode(errors="replace").strip()
            print(f"received: {response}")
            time.sleep(1.5)


if __name__ == "__main__":
    main()
