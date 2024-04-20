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

# Import the config file
import config

# Connect to WiFi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
while wlan.isconnected() == False:
  print('Waiting for connection...')
  time.sleep(1)
print("Connected to WiFi")

# OTA update
print('Starting OTA update')
if uota.check_for_updates():
  uota.install_new_firmware()
  print('New firmware installed, rebooting...')
  machine.reset()

# Initialize our MQTTClient and connect to the MQTT server
mqtt_client = MQTTClient(
  client_id = config.MQTT_CLIENT_ID,
  server = config.MQTT_BROKER,
  port = config.MQTT_PORT
  )

mqtt_client.connect()

# The topic to publish data to
mqtt_publish_topic = config.MQTT_PUBLISH_TOPIC

# Initialize the WiFi power pin
wifi_pin = machine.Pin(23, machine.Pin.OUT)

# Initialize the DHT11 power pin
dht_pin = machine.Pin(4, machine.Pin.OUT)

#initialize DHT11 sensor
dht_sensor = dht.DHT11(machine.Pin(5))

# Publish a data point to the topic every XX seconds
try:
  while True:
    # activate the wifi
    wifi_pin.high() # turn on wifi power
    wlan.active(True)

    # power on the DHT sensor
    dht_pin.on()
    # read the temperature and humidity
    try:
      dht_sensor.measure()
      temp_dht = float(dht_sensor.temperature())
      hum_dht = float(dht_sensor.humidity())
    except Exception as e:
      print(f'Failed to read temperature and humidity: {e}')
      continue
    time.sleep(1.0)
    # power off the DHT sensor
    dht_pin.off()

    # Publish the data to the topics! with %3.1f format
    try:
      mqtt_client.publish(f'{mqtt_publish_topic}/temperature', str(temp_dht), qos=1)
      mqtt_client.publish(f'{mqtt_publish_topic}/humidity', str(hum_dht), qos=1)
      print(f'Temperature: {temp_dht}')
      print(f'Humidity: {hum_dht}')
    except Exception as e:
      print(f'Failed to publish message: {e}')
      continue
    time.sleep(0.2)

    # power off the wifi
    wlan.active(False)
    wifi_pin.low() # turn off wifi power
    # Sleep
    machine.deepsleep(60000)
except Exception as e:
  print(f'Error: {e}')
finally:
  mqtt_client.disconnect()
  wlan.active(False)
  dht_pin.off()
  machine.reset()

