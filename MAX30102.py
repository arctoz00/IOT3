import time
import board
import busio
from adafruit_max30102 import MAX30102
from adafruit_minimqtt.adafruit_minimqtt import MQTT
import wifi
import socketpool

# Wi-Fi Configuration
WLAN_SSID = "Raspberrypi"
WLAN_PASS = "12345678"

# MQTT Configuration
AIO_SERVER = "io.adafruit.com"
AIO_SERVERPORT = 1883
AIO_USERNAME = "ismo0001"
AIO_KEY = "aio_Lzmz73ZIOrnNWRSpId9lTfMZgrJt"
HEART_RATE_FEED = f"{AIO_USERNAME}/feeds/heart-rate"
HEART_RATE_AVG_FEED = f"{AIO_USERNAME}/feeds/heart-rate-avg"

# Constants
RATE_SIZE = 4

# Initialize I2C and MAX30102
i2c = busio.I2C(board.SCL, board.SDA)
particle_sensor = MAX30102(i2c)

# Heart Rate Variables
rates = [0] * RATE_SIZE
rate_spot = 0
last_beat = 0
beats_per_minute = 0
beat_avg = 0

# Wi-Fi Connection
print("Connecting to Wi-Fi...")
wifi.radio.connect(WLAN_SSID, WLAN_PASS)
print(f"Connected to Wi-Fi: {WLAN_SSID}")

# MQTT Client Setup
pool = socketpool.SocketPool(wifi.radio)

def connected(client, userdata, flags, rc):
    print("Connected to MQTT Broker!")

def disconnected(client, userdata, rc):
    print("Disconnected from MQTT Broker!")

def message(client, topic, message):
    print(f"Message on {topic}: {message}")

mqtt_client = MQTT(
    broker=AIO_SERVER,
    port=AIO_SERVERPORT,
    username=AIO_USERNAME,
    password=AIO_KEY,
    socket_pool=pool
)
mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected
mqtt_client.on_message = message

print("Connecting to MQTT Broker...")
mqtt_client.connect()

def compute_heart_rate():
    global rates, rate_spot, last_beat, beats_per_minute, beat_avg

    ir_value = particle_sensor.raw_ir
    if ir_value < 50000:
        print("No finger detected.")
        return

    if particle_sensor.check():
        delta = time.monotonic() - last_beat
        last_beat = time.monotonic()

        beats_per_minute = 60 / delta

        if 20 < beats_per_minute < 255:
            rates[rate_spot] = beats_per_minute
            rate_spot = (rate_spot + 1) % RATE_SIZE
            
            beat_avg = sum(rates) / RATE_SIZE

            mqtt_client.publish(HEART_RATE_FEED, f"{beats_per_minute:.2f}")
            mqtt_client.publish(HEART_RATE_AVG_FEED, f"{beat_avg:.2f}")

            print(f"IR={ir_value}, BPM={beats_per_minute:.2f}, Avg BPM={beat_avg:.2f}")

# Main Loop
print("Heart Rate Monitoring System Initialized.")

try:
    while True:
        compute_heart_rate()
        time.sleep(0.1)

except KeyboardInterrupt:
    print("Exiting...")
mqtt_client.disconnect()
