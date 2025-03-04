"""
Threaded bouncing boxes with frame buffer

Uses a single shot function for second core SPI handler.
This cleans itself when the function exits removing the
need for a garbage collection call.

"""
import math
import time
from time import sleep
from ili9341 import Display, color565
from machine import Pin, SPI
import machine
import framebuf
from random import random, seed, randint
from utime import sleep_us, ticks_cpu, ticks_us
import gc
import os
import _thread


class Box(object):
    """Bouncing box."""

    def __init__(self, screen_width, screen_height, size, color):
        """Initialize box.

        Args:
            screen_width (int): Width of screen.
            screen_height (int): Width of height.
            size (int): Square side length.
            color (int): RGB565 color value.
        """
        self.size = size
        self.w = screen_width
        self.h = screen_height
        self.color = color
        # Generate non-zero random speeds between -5.0 and 5.0
        seed(ticks_cpu())
        r = random() * 10.0
        self.x_speed = r - 5
        r = random() * 10.0
        self.y_speed = r - 5

        self.x = self.w / 2
        self.y = self.h / 2

    def update_pos(self):
        """Update box position and speed."""

        # update position
        self.x += self.x_speed
        self.y += self.y_speed

        # limit checking
        if self.x < 0:
            self.x = 0
            self.x_speed = -self.x_speed
        elif self.x > (self.w - self.size):
            self.x = self.w - self.size
            self.x_speed = -self.x_speed
        if self.y < 0:
            self.y = 0
            self.y_speed = -self.y_speed
        elif self.y > (self.h - self.size):
            self.y = self.h - self.size
            self.y_speed = -self.y_speed

        # extra processing load
        # for num in range(1, 200):
        #     num2 = math.sqrt(num)

    def draw(self, side):
        """Draw box."""
        global fbuf

        x = int(self.x)
        y = int(self.y) - side * 120
        size = self.size
        fbuf.fill_rect(x, y, size, size, self.color)


def free(full=False):
    gc.collect()
    F = gc.mem_free()
    A = gc.mem_alloc()
    T = F + A
    P = '{0:.2f}%'.format(F / T * 100)
    if not full:
        return P
    else:
        return ('Total:{0} Free:{1} ({2})'.format(T, F, P))


# set landscape screen
screen_width = 320
screen_height = 240
screen_rotation = 90

spi = SPI(0,
          baudrate=31250000,
          polarity=1,
          phase=1,
          bits=8,
          firstbit=SPI.MSB,
          sck=Pin(18),
          mosi=Pin(19),
          miso=Pin(16))

display = Display(spi, dc=Pin(20), cs=Pin(22), rst=Pin(21),
                  width=screen_width, height=screen_height,
                  rotation=screen_rotation)

print(spi)

# FrameBuffer needs 2 bytes for every RGB565 pixel
buffer_width = screen_width
buffer_height = screen_height // 2
buffer = bytearray(buffer_width * buffer_height * 2)
fbuf = framebuf.FrameBuffer(buffer, buffer_width, buffer_height, framebuf.RGB565)

render_frame = False


def main_loop():
    """Test code."""

    global fbuf, buffer, buffer_width, buffer_height
    global render_frame

    render_frame = False

    try:

        boxes = [Box(screen_width - 1, screen_height - 1, randint(7, 40),
                     color565(randint(30, 256), randint(30, 256), randint(30, 256))) for i in range(100)]

        print(free(True))

        start_time = ticks_us()
        frame_count = 0
        side = 2
        while True:
            if side == 2:
                side = 1
            else:
                side = 2
            
            for b in boxes:
                b.update_pos()

            while render_frame:
                # previous frame still rendering
                pass

            for b in boxes:
                b.draw(side - 1)

            # render frame to lcd
            render_frame = side
            # start spi handler on core 1
            spi_thread = _thread.start_new_thread(render_thread, (2,))

            frame_count += 1
            if frame_count == 100:
                frame_rate = 100 / ((ticks_us() - start_time) / 1000000)
                print(frame_rate / 2.0)
                start_time = ticks_us()
                frame_count = 0

    except KeyboardInterrupt:
        pass


def render_thread(id):
    global fbuf, buffer, buffer_width, buffer_height, render_frame, spi
    global display, screen_width, screen_height, screen_rotation

    # No need to wait for start signal as thread only started when buffer is ready

    # render display
    if render_frame == 1:
        display.block(0, 0, buffer_width - 1, buffer_height - 1, buffer)
    if render_frame == 2:
        display.block(0, buffer_height, buffer_width - 1, buffer_height * 2 - 1, buffer)
    # clear buffer
    fbuf.fill(0)

    # signal finished back to main thread
    render_frame = False

    # thread will exit and self clean removing need for garbage collection
    return


main_loop()

