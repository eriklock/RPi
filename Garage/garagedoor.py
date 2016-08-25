#!/usr/bin python

"""
Monitors a magnetic switch attached to the garage door, indicating whether
the door is open or closed. A spare garage remote is also connected so that
the door can be open/closed remotely.

Switch is normally-open, so circuit will be closed when door is closed.
Using pull-up resistor, so closed door will be logic low.

"""

import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import time

"""Pi GPIO setup"""

#Indicate pins are referenced by numbers on board
GPIO.setmode(GPIO.BOARD)

#Set magnetic switch pin and garage remote pin
switch = 36 
remote = 38
GPIO.setup(switch, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(remote, GPIO.OUT)

isOpen = False
lastState = False
remotePressed = False
state = False

def door_change(switch):
    """Callback function for when switch state changes"""
    global isOpen, state
    input = GPIO.input(switch)
    if input:
        print(time.strftime("%a, %d %b %Y %I:%M:%S %p", time.localtime()) + " - OPEN")
        isOpen = True
        state = "open"
    else:
        print(time.strftime("%a, %d %b %Y %I:%M:%S %p", time.localtime()) + " - CLOSED")
        isOpen = False
        state = "closed"

#The interrupt monitoring the switch
GPIO.add_event_detect(switch, GPIO.BOTH, callback=door_change, bouncetime=2000)


"""MQTT client setup"""

def on_connect(mqtt_client, userdata, rc):
    """The callback for when the client receives a
    CONNACK response from the server.
    """
    print("Connected with result code "+str(rc))
    mqtt_client.subscribe("garage/door", 2)
    mqtt_client.subscribe("garage/remote", 2)
    mqtt_client.publish("garage/door", state, retain=True)

def on_message(mosq, obj, msg):
    """Received message will be to activate the door"""
    print("Received message: " + msg.payload + " on topic " + msg.topic)
    if (msg.payload == "open" or msg.payload == "close") and msg.topic == "garage/remote":
        global remotePressed
        print("Remote pressed")
        remotePressed = True

broker = "192.168.0.210" #RPi3
mqtt_client = mqtt.Client(client_id="2")
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(broker)
mqtt_client.loop_start()

"""Program Start"""

print("Beginning garage door client")
door_change(switch) #Set the initial state
lastState = isOpen

try:  
    while True:
        #Check for signal to open/close door
        if remotePressed:
            #"Press" remote button
            GPIO.output(remote, GPIO.HIGH)
            time.sleep(1.5)
            GPIO.output(remote, GPIO.LOW)

            remotePressed = False

        #Publish new door state on change
        if lastState != isOpen:
            mqtt_client.publish("garage/door", state, retain=True)
            lastState = isOpen
        time.sleep(1)
        
except KeyboardInterrupt:           
    GPIO.cleanup()
    
