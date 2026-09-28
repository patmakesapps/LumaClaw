from scservo_sdk import PortHandler, sms_sts, COMM_SUCCESS

PORT = "/dev/ttyACM0"
BAUDRATE = 1000000
SERVO_ID = 1

port = PortHandler(PORT)
servo = sms_sts(port)

port.openPort()
port.setBaudRate(BAUDRATE)

position, result, error = servo.ReadPos(SERVO_ID)

if result == COMM_SUCCESS:
    print(f"Servo ID {SERVO_ID}")
    print(f"Current position: {position}")
else:
    print("Failed to read position")
    print("Result:", result)
    print("Error:", error)

port.closePort()