import select
import sys
import time
import json
import _thread
import machine
import os
from roboxlib import ColorSensor
from communication import USBCommunication, BluetoothCommunuication, generate_message

DEBUG = True
CURRENT_FIRMWARE_VERSION = "1.0.0"
# ----------------------
# Hardware setup
# ----------------------
LED = machine.Pin(25, machine.Pin.OUT)
PROGRAM_FILENAME = "program.py"
colorSensor = False
try:
    colorSensor = ColorSensor()
except:
    colorSensor = False
# ----------------------
# Command dictionary
# ----------------------
COMMANDS = {
    "x01FIRMCHECK": "firmware_check",
    "x02BEGINUPLD": "begin_upload",
    "x03ENDUPLD": "end_upload",
    "x04STARTPROG": "start_program",    
    "x05COLORCALIBRATE": "calibrate_color",
    "x06RESTART": "reset_device",
    "x07BOOTLOADER": "boot_loader",
    # Functionally the same as RESTART but for state management
    "x08DISCONNECT": "disconnect_device",
}
# ----------------------
# Communication setup
# ----------------------
ble = BluetoothCommunuication()
usb = USBCommunication()

communications = []
current_communication_method = None
if usb.available():
    communications.append(usb)
if ble.available():
    communications.append(ble)
# ----------------------
# Helpers
# ----------------------
def run_user_program(comm):
    try:
        import program
    except Exception as e:
        comm.write_message("error", str(e))
while True:
    for comm in communications:
        if comm.sleeping:
            continue
        line = comm.read_line()
        if line:
            if (DEBUG):
                print(generate_message("console", "Received over {}: {}".format(comm.name, line)))
            command = COMMANDS.get(line)
            if command == "firmware_check":
                if DEBUG:
                    print(generate_message("console", "Firmware check over {}".format(comm.name)))
                # Reject if already connected over another interface
                if (current_communication_method and current_communication_method != comm):
                    comm.write_message("error", "Already connected over another interface")
                    continue
                # If we are connected via USB, set bluetooth to sleep
                if comm == usb:
                    if ble in communications:
                        if DEBUG:
                            print(generate_message("console", "Putting BLE to sleep"))
                        ble.sleep()
                current_communication_method = comm
                comm.write_message("firmware", CURRENT_FIRMWARE_VERSION)
            elif command == "start_program":
                LED.on()
                comm.write_message("console", "Starting the program")
                time.sleep(0.3)
                _thread.start_new_thread(run_user_program, (comm,))
            elif command == "begin_upload":
                os.remove(PROGRAM_FILENAME) if PROGRAM_FILENAME in os.listdir() else None
                out_file = open(PROGRAM_FILENAME, "w")
                comm.write_message("console", "Begin upload")
                if (DEBUG):
                    print(generate_message("console", "Beginning upload over {}".format(comm.name)))
                time.sleep(0.1)
            elif command == "end_upload":
                if out_file:
                    out_file.close()
                    out_file = None
                    comm.write_message("console", "Upload complete")
                else:
                    comm.write_message("error", "No upload in progress")
                time.sleep(0.1)
            elif command == "calibrate_color":
                if not colorSensor:
                    comm.write_message("error", "The color sensor is not properly connected")
                else:
                    colorSensor.calibrate()
                    comm.write_message("calibrated", "")
            elif command == "reset_device":
                ble.wake() if ble in communications and ble.sleeping else None
                machine.reset()
            
            elif out_file:
                if DEBUG:
                    print(generate_message("console", "Writing to file over {}: {}".format(comm.name, line)))
                LED.toggle()
                out_file.write(line + "\n")