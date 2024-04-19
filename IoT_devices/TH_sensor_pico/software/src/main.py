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

# Initialize the LED
dht_pin = machine.Pin(4, machine.Pin.OUT)

#initialize DHT11 sensor
dht_sensor = dht.DHT11(machine.Pin(5))

# Publish a data point to the topic every XX seconds
try:
  while True:
    # activate the wifi
    wlan.active(True)

    # power on the DHT sensor
    dht_pin.on()
    time.sleep(0.1)
    # read the temperature and humidity
    dht_sensor.measure()
    temp_dht = float(dht_sensor.temperature())
    hum_dht = float(dht_sensor.humidity())

    # Publish the data to the topics! with %3.1f format
    mqtt_client.publish(f'{mqtt_publish_topic}/temperature', str(temp_dht))
    mqtt_client.publish(f'{mqtt_publish_topic}/humidity', str(hum_dht))
    print(f'Temperature: {temp_dht}')
    print(f'Humidity: {hum_dht}')

    # power off the wifi
    wlan.active(False)
    # power off the DHT sensor
    dht_pin.off()
    # machine reset
    machine.reset()
    # Sleep for 60 seconds
    machine.lightsleep(60000)
except Exception as e:
  print(f'Failed to publish message: {e}')
finally:
  mqtt_client.disconnect()
  wlan.active(False)
  dht_pin.off()
  machine.reset()