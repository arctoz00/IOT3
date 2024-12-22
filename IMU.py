import time
import math
import board
import busio
import wifi
import socketpool
from adafruit_mpu6050 import MPU6050
from adafruit_minimqtt.adafruit_minimqtt import MQTT

# Wi-Fi 
WLAN_SSID = "Raspberrypi"
WLAN_PASS = "12345678"

# MQTT 
AIO_SERVER = "io.adafruit.com"
AIO_SERVERPORT = 1883
AIO_USERNAME = "ismo0001"
AIO_KEY = "aio_Lzmz73ZIOrnNWRSpId9lTfMZgrJt"
ACCELERATION_FEED = f"{AIO_USERNAME}/feeds/acceleration"
FALL_DETECTION_FEED = f"{AIO_USERNAME}/feeds/fall-detection"

# Konstanter
FALL_SPIKE_THRESHOLD = 14.0
STABILITY_WINDOW = 5  # seconds
SENSOR_INTERVAL = 0.3  # seconds
MQTT_SEND_INTERVAL = 2  # seconds

# Initialisér I2C and MPU6050
i2c = busio.I2C(board.SCL, board.SDA)
mpu = MPU6050(i2c)

# Wi-Fi forbindelse
print("Connecting to Wi-Fi...")
wifi.radio.connect(WLAN_SSID, WLAN_PASS)
print(f"Connected to Wi-Fi: {WLAN_SSID}")

# MQTT Client setup
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

def compute_total_acceleration():
    acc = mpu.acceleration
    ax, ay, az = acc
    return math.sqrt(ax**2 + ay**2 + az**2)

def detect_fall(total_acceleration):
    global fall_reported, fall_reset_time

    if total_acceleration > FALL_SPIKE_THRESHOLD and not fall_reported:
        print("Potential fall detected!")
        fall_reported = True
        fall_reset_time = time.time()
        mqtt_client.publish(FALL_DETECTION_FEED, "1")
        print("Fall detection published to Adafruit IO")

    if fall_reported and time.time() - fall_reset_time > STABILITY_WINDOW:
        fall_reported = False
        mqtt_client.publish(FALL_DETECTION_FEED, "0")
        print("Fall detection reset to 0 on Adafruit IO")

# Main Loop
fall_reported = False
fall_reset_time = 0
last_sensor_update = 0
last_mqtt_send_time = 0

print("Fall Detection System Initialized.")

try:
    while True:
        current_time = time.time()

        # Non-blocking sensor kode
        if current_time - last_sensor_update >= SENSOR_INTERVAL:
            total_acceleration = compute_total_acceleration()
            detect_fall(total_acceleration)

            # Acceleration data til MQTT
            if current_time - last_mqtt_send_time >= MQTT_SEND_INTERVAL:
                mqtt_client.publish(ACCELERATION_FEED, str(total_acceleration))
                print(f"Published acceleration to Adafruit IO: {total_acceleration:.2f}")
                last_mqtt_send_time = current_time

            last_sensor_update = current_time

except KeyboardInterrupt:
    print("Exiting...")
mqtt_client.disconnect()
