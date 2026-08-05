from gpiozero import AngularServo
from time import sleep

SERVO_PIN = 18

SAFE_MIN_ANGLE = 60
SAFE_MAX_ANGLE = 120
CENTER_ANGLE = 90

MIN_PULSE_WIDTH = 0.00075
MAX_PULSE_WIDTH = 0.00225

POSES = {
    "open": 60,
    "half": 90,
    "closed": 120,
}

servo = AngularServo(
    SERVO_PIN,
    min_angle=0,
    max_angle=180,
    min_pulse_width=MIN_PULSE_WIDTH,
    max_pulse_width=MAX_PULSE_WIDTH,
    initial_angle=None,
)


def check_angle(angle):
    if not SAFE_MIN_ANGLE <= angle <= SAFE_MAX_ANGLE:
        raise ValueError(
            f"Angle must be between {SAFE_MIN_ANGLE} and "
            f"{SAFE_MAX_ANGLE} degrees."
        )


def move_slowly(start_angle, end_angle, step_delay=0.03):
    check_angle(start_angle)
    check_angle(end_angle)

    step = 1 if end_angle >= start_angle else -1

    for angle in range(start_angle, end_angle, step):
        servo.angle = angle
        sleep(step_delay)

    servo.angle = end_angle
    sleep(0.3)


def move_to_pose(current_angle, pose_name):
    if pose_name not in POSES:
        raise ValueError(f"Unknown pose: {pose_name}")

    target_angle = POSES[pose_name]

    print(
        f"Moving from {current_angle}° "
        f"to {pose_name} at {target_angle}°."
    )

    move_slowly(current_angle, target_angle)
    return target_angle


if __name__ == "__main__":
    try:
        print("SG90 claw controller")
        print("1 - Center the bare servo")
        print("2 - Test assembled claw poses")

        mode = input("Choose mode 1 or 2: ").strip()

        if mode == "1":
            input(
                "Remove the horn, then press Enter "
                "to center the servo..."
            )

            servo.angle = CENTER_ANGLE
            sleep(1)

            print(f"Servo centered at {CENTER_ANGLE} degrees.")
            print("Disconnect servo power before installing the horn.")

        elif mode == "2":
            input(
                "Confirm the claw is clear and near its centered "
                "position, then press Enter..."
            )

            current_angle = CENTER_ANGLE
            servo.angle = current_angle
            sleep(1)

            print("Pose mode ready: open, half, closed, or quit.")

            while True:
                pose_name = input("Choose a pose: ").strip().lower()

                if pose_name == "quit":
                    break

                try:
                    current_angle = move_to_pose(
                        current_angle,
                        pose_name,
                    )
                except ValueError as error:
                    print(error)

        else:
            print("Invalid mode. Choose 1 or 2.")

    finally:
        servo.detach()
        print("Servo signal released.")