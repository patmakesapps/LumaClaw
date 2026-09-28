from scservo_sdk import PortHandler, sms_sts, COMM_SUCCESS

PORT = "/dev/ttyACM0"
BAUDRATE = 1000000

port = PortHandler(PORT)
servo = sms_sts(port)

port.openPort()
port.setBaudRate(BAUDRATE)

print("Scanning servo IDs 1-20...")

for servo_id in range(1, 21):
    model, result, error = servo.ping(servo_id)

    if result == COMM_SUCCESS:
        print(f"FOUND ID {servo_id} | model {model}")

port.closePort()