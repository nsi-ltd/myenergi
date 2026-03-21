import paho.mqtt.client as mqtt
import time
import sys
from datetime import datetime
import requests
from requests.auth import HTTPDigestAuth
import json
import re
from os import environ
from queue import Queue
from queue import Empty
from queue import Full

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
  global mqtt_topic
  
  print(f'Connected with result code {rc}')

  # Subscribing in on_connect() means that if we lose the connection and
  # reconnect then subscriptions will be renewed.
  print(f'Subscribing to topic : {mqtt_topic}/SetTimerSettings/#') 
  client.subscribe(mqtt_topic + '/SetTimerSettings/#')

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
  global mqtt_topic
  global instrument
  global queue
  
  topic = msg.topic
  payload = msg.payload.decode('utf-8')
  atoms = topic.split('/')
  
  print(f'Topic: {topic}, Payload: {payload}')
  print(f'Atoms: {repr(atoms)}')

  try :
    data=json.loads(payload)
    starthour = data['bsh']
    startminute = data['bsm']
    durationhour = data['bdh']
    durationminute = data['bdm']
    days = data['bdd']

    start = int(f'{starthour:02d}{startminute:02d}')
    duration = int(f'{durationhour:d}{durationminute:02d}')

    # check values are valid

    if len(atoms) != 5:
      print('Invalid topic format')
      return
    
    if starthour < 0 or starthour > 23:
      print(f'Invalid start hour : {starthour}')
      return
    
    if not startminute in [0,15,30,45]:
      print(f'Invalid start minute : {startminute}')
      return
    
    if duration < 0 or duration > 800:
      print(f'Invalid duration : {duration}')
      return
    
    if not durationminute in [0,15,30,45]:
      print(f'Invalid duration minute : {durationminute}')
      return
    
    if not re.fullmatch('^0[01]{7}$', days):
      print(f'Invalid days : {days}')
      return
    
    writedata = { 'topic' : topic, 'data' : atoms, 'id' : atoms[2].upper()[0] + atoms[3], 'slt' : atoms[4], 'start' : f'{start:04d}', 'duration' : f'{duration:03d}', 'days' : days, 'payload' : payload }
  
    queue.put(writedata)
  except Full :
    print('Exception thrown while adding to queue')

##############################
# MAIN CODE STARTS HERE
##############################

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
  print(f'MQTT-PORT not an integer : [{mqtt_port}]')
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

queue = Queue(20)

try :
  mqttc = mqtt.Client()
  mqttc.on_connect = on_connect
  mqttc.on_message = on_message
  mqttc.connect(mqtt_host, port, 60)
  mqttc.loop_start()

  print('Connected to MQTT broker')
except :
  print('Failed to connect to MQTT broker!')
  sys.exit(5)

sleep_time = 60
status_code = 0

sensor_200_count = 0
sensor_429_count = 0
sensor_other_count = 0

boost_200_count = 0
boost_429_count = 0
boost_other_count = 0

set_200_count = 0
set_429_count = 0
set_other_count = 0


while (True) :
  now = datetime.now()
  current_time = now.strftime("%Y-%m-%d %H:%M:%S")
  
  server="s18"

  if not queue.empty() :
    item = queue.get_nowait()
    print('Got item from queue : ' + repr(item))

    try :
      url = f'https://{server}.myenergi.net/cgi-boost-time-{item["id"]}-{item["slt"]}-{item["start"]}-{item["duration"]}-{item["days"]}'
      print(f'Setting boost timer with url : {url}')

      headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
      r = requests.get(url, auth=HTTPDigestAuth(myenergi_user,myenergi_password), headers=headers, timeout=20)
      
      print(r.status_code)

      status_code = r.status_code

      if r.status_code == 200:
        set_200_count += 1
        print(r.content)
      elif r.status_code == 429:
        set_429_count += 1
        print('Set - Too many requests, probably hit the rate limit')
        sleep_time *= 2
        queue.put(item)
      else :
        set_other_count += 1
        print(f'Set - Failed to set boost timer settings, status code : {r.status_code}')
    except :
      print("Failed to set boost timer settings")
  else :
    try :
      url = 'https://' + server + '.myenergi.net/cgi-jstatus-*'
      headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
      r = requests.get(url, auth=HTTPDigestAuth(myenergi_user,myenergi_password), headers=headers, timeout=20)

      status_code = r.status_code

      if r.status_code == 200:
        sensor_200_count += 1
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

                    status_code = r.status_code

                    if r.status_code == 200:
                      boost_200_count += 1
                      data=json.loads(r.content)

                      mqttc.publish(mqtt_topic + '/boost/' + j + '/' + str(l["sno"]), json.dumps(data), 2, True)
                    elif r.status_code == 429:
                      boost_429_count += 1
                      print('Boost - Too many requests, probably hit the rate limit')
                    else :
                      boost_other_count += 1
                      print(f'Boost - Failed to get boost timer settings, status code : {r.status_code}')

      r.close()

    except :
      print("Failed to login")
  if status_code == 200:
    sleep_time = 60
  elif status_code == 429:
    print(f'{current_time} - Increase time - Too many requests, probably hit the rate limit')
    sleep_time *= 2
  else :
    print (f'{current_time} - Increase time - Failed to login, status code : {status_code}')
    sleep_time *= 2

  mqttc.publish(mqtt_topic + '/status',
                json.dumps(
                  {"sleep_time": sleep_time,
                   "status_code": status_code,
                   "sensor_200_count": sensor_200_count,
                   "sensor_429_count": sensor_429_count,
                   "sensor_other_count": sensor_other_count,
                   "boost_200_count": boost_200_count,
                   "boost_429_count": boost_429_count,
                   "boost_other_count": boost_other_count,
                   "set_200_count": set_200_count,
                   "set_429_count": set_429_count,
                   "set_other_count": set_other_count
                  }), 2, True)

  mqttc.publish(mqtt_topic + '/status',
                json.dumps(
                  {"sleep_time": sleep_time,
                   "status_code": status_code,
                   "sensor_200_count": sensor_200_count,
                   "sensor_429_count": sensor_429_count,
                   "sensor_other_count": sensor_other_count,
                   "boost_200_count": boost_200_count,
                   "boost_429_count": boost_429_count,
                   "boost_other_count": boost_other_count,
                   "set_200_count": set_200_count,
                   "set_429_count": set_429_count,
                   "set_other_count": set_other_count
                  }), 2, True)

  time.sleep(sleep_time)
