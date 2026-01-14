import time
import json
import _thread
import machine
from machine import UART, Pin
from roboxlib import ColorSensor

# ----------------------
# Hardware setup
# ----------------------
LED = Pin(25, Pin.OUT)
PROGRAM_FILENAME = "program.py"

# HM-10 UART (TX/RX)
uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))

# Optional color sensor
colorSensor = False
try:
    colorSensor = ColorSensor()
except:
    colorSensor = False

# ----------------------
# Command dictionary
# ----------------------
COMMANDS = {
    "x04STARTPROG": "start_program",
    "x02BEGINUPLD": "begin_upload",
    "x03ENDUPLD": "end_upload",
    "x01FIRMCHECK": "firmware_check",
    "x06RESTART": "reset_device",
    "x05COLORCALIBRATE": "calibrate_color",
    "x07BOOTLOADER": "boot_loader",
}

# ----------------------
# Helpers
# ----------------------
def generate_message(msg_type, message):
    """Format JSON message for Pico → BLE"""
    return json.dumps({"type": msg_type, "message": message}) + "\n"

def run_user_program():
    try:
        import program
    except Exception as e:
        uart.write(generate_message("error", str(e)))

# ----------------------
# UART (HM-10) mode
# ----------------------
def uart_mode():
    uart.write(generate_message("online", "Device ready over Bluetooth"))

    out_file = None
    buffer = b''  # Accumulate incoming bytes

    while True:
        if uart.any():
            data = uart.read(uart.any())  # Read all available bytes
            if not data:
                continue

            buffer += data
            print(buffer)
            # Process full lines only
            while b'\n' in buffer:
                print("test")
                line_bytes, buffer = buffer.split(b'\n', 1)
                try:
                    line = line_bytes.decode()
                    clean_line = line.strip()
                except UnicodeError:
                    continue  # ignore invalid bytes

                if not line:
                    continue
                
                command = COMMANDS.get(clean_line)
                
                # ----------------------
                # Command handling
                # ----------------------
                print(command)
                if command == "start_program":
                    LED.on()
                    uart.write(generate_message("console", "Starting the program"))
                    _thread.start_new_thread(run_user_program, ())

                elif command == "calibrate_color":
                    if not colorSensor:
                        uart.write(generate_message("error", "Color sensor not connected"))
                    else:
                        colorSensor.calibrate()
                        uart.write(generate_message("calibrated", ""))

                elif command == "begin_upload":
                    with open(PROGRAM_FILENAME, 'w'):
                        pass  # clear file
                    out_file = open(PROGRAM_FILENAME, "w")
                    uart.write(generate_message("console", "Ready to receive program"))

                elif command == "end_upload":
                    if out_file:
                        out_file.close()
                        out_file = None
                    LED.on()
                    uart.write(generate_message("download", "Program received"))

                elif command == "firmware_check":
                    print("FIRMWARE")
                    uart.write(generate_message("confirmation", True))

                elif command == "reset_device":
                    machine.reset()

                elif out_file:
                    LED.toggle()
                    print(line)
                    out_file.write(line+"\n")

# ----------------------
# Main
# ----------------------
def main():
    LED.on()
    uart_mode()  # Always use HM-10 BLE UART mode

main()
