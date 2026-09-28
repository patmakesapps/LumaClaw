from scservo_sdk import PortHandler, sms_sts, COMM_SUCCESS

PORT = "/dev/ttyACM0"
BAUDRATE = 1000000
SERVO_ID = 1

port = PortHandler(PORT)
servo = sms_sts(port)

if not port.openPort():
    raise RuntimeError(f"Could not open {PORT}")

if not port.setBaudRate(BAUDRATE):
    raise RuntimeError(f"Could not set baud rate to {BAUDRATE}")

model_number, comm_result, error = servo.ping(SERVO_ID)

if comm_result == COMM_SUCCESS:
    print(f"FOUND servo ID {SERVO_ID}")
    print(f"Model number: {model_number}")
else:
    print(f"No response from servo ID {SERVO_ID}")
    print("Communication result:", comm_result)
    print("Servo error:", error)

port.closePort()