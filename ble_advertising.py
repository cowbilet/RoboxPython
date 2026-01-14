from machine import UART, Pin
import time

# HM-10 UART
uart = UART(0, tx=Pin(0), rx=Pin(1), baudrate=9600)

def send_at(cmd):
    uart.write(cmd + '\r\n')
    time.sleep(0.2)
    while uart.any():
        response = uart.readline().decode().strip()
        print(response)

# Test
send_at("AT")         # Should print OK
send_at("AT+NAMERoBox")   # Should print current name
