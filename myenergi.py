import paho.mqtt.client as mqtt
import time
import sys
from datetime import datetime
import requests
from requests.auth import HTTPDigestAuth
import json
from os import environ

print('Starting myenergi.py')

try :
  mqtt_host = environ['MQTT_HOST']
except KeyError :
  print('Missing variable : MQTT_HOST')
  sys.exit(1)

try :
  mqtt_port = environ['MQTT_PORT']
except KeyError :
  print('Missing variable : MQTT_PORT, using default 1883')
  mqtt_port = '1883'

try :
  mqtt_topic = environ['MQTT_TOPIC']
except KeyError :
  print('Missing variable : MQTT_TOPIC, using default myenergi')
  mqtt_topic = 'myenergi'

try :
  port = int(mqtt_port)
except ValueError :
  print('MQTT-PORT not an integer : [' + mqtt_port + ']')
  sys.exit(2)

try :
  myenergi_user = environ['MYENERGI_USER']
except KeyError :
  print('Missing variable : MYENERGI_USER')
  sys.exit(3)

try :
  myenergi_password = environ['MYENERGI_PASSWORD']
except KeyError :
  print('Missing variable : MYENERGI_PASSWORD')
  sys.exit(4)

try:
  myenergi_url = environ['MYENERGI_URL']
except KeyError :
  print('Missing variable : MYENERGI_URL')
  sys.exit(5)

try :
  mqttc = mqtt.Client()
  mqttc.connect(mqtt_host, port, 60)
  mqttc.loop_start()

  print('Connected to MQTT broker')
except :
  print('Failed to connect to MQTT broker!')
  sys.exit(5)

while (True) :
  now = datetime.now()
  current_time = now.strftime("%H:%M:%S")
  sleep_time = 240
  
  server="s18"

  try :
    url = 'https://' + server + '.myenergi.net/cgi-jstatus-*'
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    r = requests.get(url, auth=HTTPDigestAuth(myenergi_user,myenergi_password), headers=headers, timeout=20)

    if r.status_code == 200:
      data=json.loads(r.content)
      
      for i in data:
        if "asn" not in i:
          for j in i.keys():
            k = i[j]

            if k:
              l = k[0]

              if "sno" in l:
                mqttc.publish(mqtt_topic + '/sensors/' + j + '/' + str(l["sno"]), json.dumps(l), 2, True)

                # now try and get the boost timer settings
                dc = str(l["deviceClass"])[0]

                if dc in ['Z', 'E', 'L']:
                  url = 'https://' + server + '.myenergi.net/cgi-boost-time-' + dc + str(l["sno"])
                  r = requests.get(url, auth=HTTPDigestAuth(myenergi_user,myenergi_password), headers=headers, timeout=20)

                  if r.status_code == 200:
                    data=json.loads(r.content)

                    mqttc.publish(mqtt_topic + '/boost/' + j + '/' + str(l["sno"]), json.dumps(data), 2, True)


    r.close()
    sleep_time = 60
  except :
    print("Failed to login")
    sleep_time = 60

  time.sleep(sleep_time)
  
