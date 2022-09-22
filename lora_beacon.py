# SPDX-FileCopyrightText: 2018 Brent Rubell for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import time
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
import adafruit_ssd1306
import adafruit_rfm9x
import os
import RPi.GPIO as GPIO

BEACON_TEXT = 'LoRa Beacon'
BEACON_FREQ = 915.00

# New message indicator
new_msg_recv = False

# Time to wait for clear frequency in sec (should be ~30)
freq_clear_time = 30

# Set up buttons for use
# Button A
btnA = DigitalInOut(board.D5)
btnA.direction = Direction.INPUT
btnA.pull = Pull.UP

# Button B
btnB = DigitalInOut(board.D6)
btnB.direction = Direction.INPUT
btnB.pull = Pull.UP

# Button C
btnC = DigitalInOut(board.D12)
btnC.direction = Direction.INPUT
btnC.pull = Pull.UP

# Create the I2C interface.
i2c = busio.I2C(board.SCL, board.SDA)

# 128x32 OLED Display
reset_pin = DigitalInOut(board.D4)
display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, reset=reset_pin)

# Clear the display.
display.fill(0)
display.show()
width = display.width
height = display.height

# Configure LoRa Radio
GPIO.setup(board.D25, GPIO.OUT)
GPIO.output(board.D25, 0)
time.sleep(0.01)
GPIO.output(board.D25, 0)

CS = DigitalInOut(board.CE1)
RESET = DigitalInOut(board.D25)

RESET.switch_to_output()
RESET.value = False
time.sleep(0.01)
RESET.value = True

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, BEACON_FREQ)
rfm9x.high_power = True
rfm9x.tx_power = 23
rfm9x.spread_factor = 12
rfm9x.code_rate = 8
rfm9x.destination = 0xff

def show_status(message):
    global new_msg_rev
    display.fill(0)
    display.text('LoRa Beacon', 35, 0, 1)
    x_off = (display.width - len(message)*5)/2
    display.text(message, int(x_off), 12, 1)
    if new_msg_recv:
        display.text('New message!', 35, 24, 1)
    display.show()


# Main beacon loop
def beacon_loop():
    global new_msg_recv

    print('--- LoRa Beacon Ready---')

    while True:

        show_status('Sending pings...')

        ping_success = True

        for p in range(23, 4, -6):
            rfm9x.tx_power = p
            beacon_tx_text = f'{BEACON_TEXT} p={p}'
            beacon_data = bytes(f'{beacon_tx_text}\0','utf-8')
            if not rfm9x.send(beacon_data):
                ping_success = False
                break
            print(beacon_tx_text)
            time.sleep(0.5)

        if not ping_success:
            print('error sending pings')
            show_status('error sending pings')
            time.sleep(5)

        show_status('Listening...')

        end_times = time.time() + 20
        while time.time() < end_times:

           if not btnA.value:
                new_msg_recv = False
                show_status('Listening...')

           packet = rfm9x.receive()
           if packet is not None:
               try:
                   packet_text = str(packet, "ascii")
                   print("> {0}".format(packet_text))
                   new_msg_recv = True
                   show_status('Heard a reply!')
               except:
                   print("got packet, but it was not valid. noise?")
                   show_status('Ew! Noise?')

# Clear the frequency before starting
def clear_freq():

    freq_clear = False
    while not freq_clear:

        show_status('Clearing freq...')
        print('Clearing frequency...')

        packet = rfm9x.receive(timeout=freq_clear_time)

        if packet is not None:
            show_status('Freq not clear!')
            print('Frequency was not clear. Beacon not starting')
            while btnA.value:
                time.sleep(0.1)
        else:
            freq_clear = True

if __name__ == '__main__':
    print('Starting LoRa Beacon')
    clear_freq()
    beacon_loop()

