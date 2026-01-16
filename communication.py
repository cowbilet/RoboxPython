from machine import UART, Pin
import json
import sys, select
import time
import _thread

# Create a global write lock for thread-safe writing
_write_lock = _thread.allocate_lock()

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
        with _write_lock:
            print(message)
            sys.stdout.flush()  # Ensure immediate output
    
    def sleep(self):
        self.sleeping = True
    
    def wake(self):
        self.sleeping = False

class BluetoothCommunuication(CommunicationInterface):
    def __init__(self, uart_port=0, baudrate=9600) -> None:
        self.name = "Bluetooth"
        self.sleeping = False
        try:
            self.uart = UART(uart_port, baudrate=baudrate, tx=Pin(0), rx=Pin(1))
            self.buffer = b""
            self.ok = True
        except:
            self.ok = False
    
    def available(self):
        return self.ok
    
    def read_line(self):
        # Okay so the issue with this was super annoying, if two messages are split unevenly over two reads like "HELLO" and "WORLD", we can get a buffer like "HELLOWORL" and then "D\n"
        # but if we only return the first line we see, then we never get "WORLD"
        if b"\n" in self.buffer:
            while b"\n" in self.buffer:
                line, self.buffer = self.buffer.split(b"\n", 1)
                if line.strip():
                    try:
                        return line.decode()
                    except:
                        return None
            return None
        
        # Add the UART to the buffer
        if not self.uart.any():
            return None
        
        data = self.uart.read()
        if not data:
            return None
        
        # Normalize line endings to \n
        self.buffer += data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        
        # Try again now that buffer grew
        return self.read_line()
    
    def write_message(self, message_type, content):
        message = generate_message(message_type, content)
        with _write_lock:
            print("Sending over BLE: {}".format(message))
            self.uart.write((f"{message}\n").encode())
            time.sleep(0.3)  # give time for the message to be sent
    
    def write(self, data):
        with _write_lock:
            self.uart.write(data+"\r\n")
    
    def sleep(self):
        if self.ok and not self.sleeping:
            with _write_lock:
                self.uart.write("AT+SLEEP\r\n")
            self.sleeping = True
    
    def wake(self):
        with _write_lock:
            self.uart.write("AT\r\n")
        self.sleeping = False

# The function to generate the structured JSON message
def generate_message(message_type, content):
    return json.dumps({"type": message_type, "message": content})