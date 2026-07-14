import time
import cv2
import serial

with serial.Serial("COM3", 9600, timeout=2) as arduino:
    time.sleep(2)
    print("banner:", arduino.readline().decode(errors="replace").strip())

    arduino.write(b"1\n")
    time.sleep(0.3)
    print("laser on ack:", arduino.readline().decode(errors="replace").strip())

    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
    time.sleep(0.3)
    ok, frame = cap.read()
    cap.release()
    print("frame captured:", ok)
    if ok:
        cv2.imwrite("captures/laser_check.jpg", frame)

    arduino.write(b"0\n")
    time.sleep(0.3)
    print("laser off ack:", arduino.readline().decode(errors="replace").strip())
