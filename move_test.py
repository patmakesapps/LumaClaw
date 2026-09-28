import time
from scservo_sdk import PortHandler, sms_sts

PORT = "/dev/ttyACM0"
BAUDRATE = 1_000_000
SERVO_ID = 1

CLAW_CLOSED = 3025
CLAW_OPEN = 2825

SPEED = 200
ACCELERATION = 50

port = PortHandler(PORT)
servo = sms_sts(port)

if not port.openPort():
    raise RuntimeError(f"Could not open {PORT}")

if not port.setBaudRate(BAUDRATE):
    raise RuntimeError("Could not set baud rate")


def open_claw():
    print("Opening claw...")
    servo.WritePosEx(
        SERVO_ID,
        CLAW_OPEN,
        SPEED,
        ACCELERATION
    )


def close_claw():
    print("Closing claw...")
    servo.WritePosEx(
        SERVO_ID,
        CLAW_CLOSED,
        SPEED,
        ACCELERATION
    )


open_claw()
time.sleep(2)

close_claw()
time.sleep(2)

port.closePort()