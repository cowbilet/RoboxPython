from machine import UART, Pin
import json
import sys, select
# Interface for the communication
class CommunicationInterface:
    def __init__(self) -> None:
        pass
    def available(self):
        raise NotImplementedError
    def read_line(self):
        raise NotImplementedError
    def write_message(self, message_type, content):
        raise NotImplementedError
# Constants for USB communication
USB_CHARGING_PIN = Pin('GPIO24', Pin.IN)
class USBCommunication(CommunicationInterface):
    def __init__(self) -> None:
        self.name = "USB"
        # Added just so that we have a consistent interface
        self.sleeping = False
        self.poller = select.poll()
        self.poller.register(sys.stdin, select.POLLIN)
    def available(self):
        return True
    def read_line(self):
        if not self.poller.poll(0):
            return None
        line = sys.stdin.readline()
        return line.rstrip("\n") if line else None
    def write_message(self, message_type, content):
        message = generate_message(message_type, content)    
        print(message)

class BluetoothCommunuication(CommunicationInterface):
    def __init__(self, uart_port=0, baudrate=9600) -> None:
        self.name = "Bluetooth"
        self.sleeping = False
        try:
            self.uart = UART(uart_port, baudrate=baudrate)
            self.buffer = b""
            self.ok = True
        except:
            self.ok = False
    def available(self):
        return self.ok
    def read_line(self):
        if not self.uart.any():
            return None

        data = self.uart.read()
        if not data:
            return None

        self.buffer += data

        if b"\n" not in self.buffer:
            return None

        line, self.buffer = self.buffer.split(b"\n", 1)
        try:
            return line.decode().rstrip("\n")
        except:
            return None
    def write_message(self, message_type, content):
        message = generate_message(message_type, content)
        self.uart.write(message + "\n")
    def sleep(self):
        if self.ok and not self.sleeping:
            self.uart.write("AT+SLEEP\r\n")
            self.sleeping = True
        self.sleeping = True
    def wake(self):
        if self.ok and self.sleeping:
            self.uart.write("AT\r\n")
            self.sleeping = False
# The function to generate the structured JSON message
def generate_message(message_type, content):
    return json.dumps({"type": message_type, "message": content})

