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

async def measure():
  try:
    # activate the wifi
    wifi_pin.high() # turn on wifi power
    wlan.active(True)
    while wlan.isconnected() == False:
      print('Waiting for connection...')
      time.sleep(1)

    # power on the DHT sensor
    dht_pin.on()
    # read the temperature and humidity
    dht_sensor.measure()
    temp_dht = float(dht_sensor.temperature())
    hum_dht = float(dht_sensor.humidity())
    # power off the DHT sensor
    dht_pin.off()

    # Publish the data to the topics!
    mqtt_client.publish(f'{mqtt_publish_topic}/temperature', str(temp_dht), qos=1)
    mqtt_client.publish(f'{mqtt_publish_topic}/humidity', str(hum_dht), qos=1)
    print(f'Temperature: {temp_dht}')
    print(f'Humidity: {hum_dht}')
    time.sleep(0.2)

    # Garbage collect
    gc.collect()
    #sending info on RAM usage
    mqtt_client.publish(f'{mqtt_publish_topic}/ram', str(gc.mem_free()), qos=1)

    # power off the wifi
    wlan.active(False)
    wifi_pin.low() # turn off wifi power

  except asyncio.CancelledError:  # Task sees CancelledError
    print('Trapped cancelled error.')
    try:
      mqtt_client.publish(f'{mqtt_publish_topic}/error', 'CancelledError', qos=1)
    except Exception as e:
      print(f'Failed to publish message: {e}')
    raise
  except Exception as e:
    print(f'Error: {e}')
    try:
      mqtt_client.publish(f'{mqtt_publish_topic}/error', str(e), qos=1)
    except Exception as e:
      print(f'Failed to publish message: {e}')

async def main():
    try:
        while True:
          await asyncio.wait_for(measure(), 5) # Wait for 5 seconds
          # Sleep
          machine.deepsleep(60000)
    except asyncio.TimeoutError:  # Mandatory error trapping
        print('measure got timeout')
        try:
          await asyncio.wait_for(mqtt_client.publish(f'{mqtt_publish_topic}/error', 'TimeoutError', qos=1), 1)
        except Exception as e:
          print(f'Failed to publish message: {e}')
    finally:
      machine.reset()

# Run the main function
asyncio.run(main())
machine.reset()





