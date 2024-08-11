"""
This is the main script that runs on the pi-pico. It reads the temperature and
humidity from the DHT11 sensor and publishes it to the MQTT broker.
"""

import network
import time
from umqtt.simple import MQTTClient
import machine
import dht
import uota
import uasyncio as asyncio
import gc

# Import the config file
import config

# Enable automatic garbage collection
gc.enable()

# Initialize wlan
wlan = network.WLAN(network.STA_IF)

# initialize outputs
ADC_voltage = 0
temp_dht = 0
hum_dht = 0
ram_free = 0

# Initialize our MQTTClient and connect to the MQTT server
mqtt_client = MQTTClient(
  client_id = config.MQTT_CLIENT_ID,
  server = config.MQTT_BROKER,
  port = config.MQTT_PORT
  )

def wifi_connect():
  global wlan
  wlan.active(True)
  wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
  max_retries = 10
  while wlan.isconnected() == False and max_retries > 0:
    print('Waiting for connection...')
    time.sleep(1)
    max_retries -= 1
  if max_retries == 0:
    print('Failed to connect to WiFi')
    return False
  print("Connected to WiFi")
  return True

def mqtt_connect():
  global mqtt_client
  try:
    mqtt_client.connect()
  except Exception as e:
    print(f'Error: {e}')

# Connect to WiFi
machine.Pin(23, machine.Pin.OUT).high() # wifi module power
time.sleep(1.0)
if not wifi_connect():
  machine.reset()

# OTA update
print('Starting OTA update')
if uota.check_for_updates():
  uota.install_new_firmware()
  print('New firmware installed, rebooting...')
  machine.reset()

# Connect to MQTT
mqtt_connect()

# The topic to publish data to
mqtt_publish_topic = config.MQTT_PUBLISH_TOPIC

# Initialize PINS
la6 = machine.Pin(28, machine.Pin.OUT) # Logic-Analyzer for block of code
la0 = machine.Pin(27, machine.Pin.OUT) # Logic-Analyzer for awake time
pin_29 = machine.Pin(29, machine.Pin.OUT) # Pin 29 used for ADC3 and WiFi
dht_pin = machine.Pin(4, machine.Pin.OUT) # DHT11 power

la6.low()
la0.high()

#initialize DHT11 sensor
dht_sensor = dht.DHT11(machine.Pin(5))

async def read_onboard_voltage():
    global ADC_voltage
    pin_29.init(machine.Pin.IN) # to read the ADC 3 voltage correctly
    ADC_raw = machine.ADC(3).read_u16()
    ADC_voltage = ((ADC_raw * 3) / 65535) * 3.3
    print(f'Voltage: {ADC_voltage}')
    pin_29.init(mode=machine.Pin.ALT, pull=machine.Pin.PULL_DOWN, alt=7) # to set back correctly for wifi module to work

async def read_dht():
  global temp_dht, hum_dht
  # power on the DHT sensor
  dht_pin.on()
  # read the temperature and humidity
  dht_sensor.measure()
  temp_dht = float(dht_sensor.temperature())
  hum_dht = float(dht_sensor.humidity())
  # power off the DHT sensor
  dht_pin.off()

  # Print the data
  print(f'Temperature: {temp_dht}')
  print(f'Humidity: {hum_dht}')

async def read_ram():
  if config.DEBUG_MODE:
    global ram_free
    #reading info on RAM usage
    ram_free = gc.mem_free()
    print(f'RAM: {ram_free}')

async def send_data(temp, hum, voltage, ram):
  mqtt_client.publish(f'{mqtt_publish_topic}/temperature', str(temp), qos=1)
  mqtt_client.publish(f'{mqtt_publish_topic}/humidity', str(hum), qos=1)
  mqtt_client.publish(f'{mqtt_publish_topic}/voltage', str(voltage), qos=1)
  if config.DEBUG_MODE:
    mqtt_client.publish(f'{mqtt_publish_topic}/ram', str(ram), qos=1)

async def measure_and_send():
  try:
    la0.high()
    # tasks
    tasks = [
      read_onboard_voltage(),
      read_dht(),
      read_ram()
    ]

    # Run all async functions concurrently (async isn't really parallel)
    la6.high()
    await asyncio.gather(*tasks)
    la6.low()

    # activate the wifi
    machine.Pin(23, machine.Pin.OUT).high() # wifi module power
    time.sleep(0.2)
    la6.high()
    time.sleep(0.2)
    wlan = network.WLAN(network.STA_IF)
    wifi_connect()

    # mqtt connect
    mqtt_connect()

    # publish data
    await send_data(temp_dht, hum_dht, ADC_voltage, ram_free)

    # prepare to sleep
    la6.low()
    time.sleep(0.5)
    mqtt_client.disconnect()
    wlan.disconnect()
    wlan.active(False)
    time.sleep(1.5) # wait for deactivation
    machine.Pin("WL_GPIO1", machine.Pin.OUT).low() # smps low power mode
    machine.Pin(23, machine.Pin.OUT).low() # wifi module power
    la0.low()
    time.sleep(0.5)

  except asyncio.CancelledError:  # Task sees CancelledError
    print('Trapped cancelled error.')
    mqtt_client.publish(f'{mqtt_publish_topic}/error', 'CancelledError', qos=1)
  except Exception as e:
    print(f'Error: {e}')
    mqtt_client.publish(f'{mqtt_publish_topic}/error', str(e), qos=1)

async def main():
    try:
        while True:
          await asyncio.wait_for(measure_and_send(), 12) # Wait
          # Sleep
          machine.deepsleep(60000)
    except asyncio.TimeoutError:  # Mandatory error trapping
        print('measure got timeout')
        try:
          await asyncio.wait_for(mqtt_client.publish(f'{mqtt_publish_topic}/error', 'TimeoutError', qos=1), 1)
        except Exception as e:
          print(f'Failed to publish message: {e}')
    finally:
      # Sleep
      machine.deepsleep(60000)
      machine.reset()

# Run the main function
asyncio.run(main())
machine.reset()
