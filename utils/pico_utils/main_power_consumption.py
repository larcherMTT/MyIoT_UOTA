''' Sample script to test the pico power consumption'''
import time
import machine

while True:
    current_time = time.time()
    print("Busy loop")
    while time.time() - current_time < 5:
        pass

    #toggle led for 5 seconds
    # led_pin = machine.Pin("LED", machine.Pin.OUT)
    # led_pin.on()
    # time.sleep(5)
    # led_pin.off()
    # del led_pin

    # the led pin increase the power consumption so we will disable it
    print("Sleeping for 5 seconds (time.sleep)")
    time.sleep(5)

    #toggle led for 5 seconds
    # led_pin = machine.Pin("LED", machine.Pin.OUT)
    # led_pin.on()
    # time.sleep(5)
    # led_pin.off()
    # del led_pin

    print("Sleeping for 5 seconds (machine.lightsleep)")
    machine.lightsleep(5000)

    #toggle led for 5 seconds
    # led_pin = machine.Pin("LED", machine.Pin.OUT)
    # led_pin.on()
    # time.sleep(5)
    # led_pin.off()
    # del led_pin

    #toggle led for 5 times
    led_pin = machine.Pin("LED", machine.Pin.OUT)
    for i in range(5):
        led_pin.toggle()
        time.sleep(1)
    led_pin.off()
    #set low power mode
    del led_pin
    #machine reset
    machine.reset()
    #toggle led for 5 times
    led_pin = machine.Pin("LED", machine.Pin.OUT)
    for i in range(5):
        led_pin.toggle()
        time.sleep(1)
    led_pin.off()
    #set low power mode
    del led_pin






