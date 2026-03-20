# Myenergi.py

A simple Python script to register with the Myenergi API and post data periodically
to an MQTT topic. The collection rate is hard coded to 60 seconds but could be changed.

Sensor data are posted to <myenergi>/sensors/#

Boost timer settings for Eddi, Libbi, and Zappi are posted to <myenergi>/boost/#

The Python code can be run from the command line, but reqires environment variables to be set.

A Docker build configuration integrates the Python code into a Docker image.

A Docker compose script provides the startup of a running container.

The docker-compose.yml takes environment variables from the hidden .env file.

## .env file
* MQTT_HOST=\<IP address or domain name of MQTT broker service.\>
* MQTT_PORT=\<TCP port of MQTT broker service.\>
* MQTT_TOPIC=\<Topic for Myenergi posting (default '/myenergi')\>
* MYENERGI_URL=\<URL of Myeneri API\>
* MYENERGI_USER=\<User for Myenergi API, usally the site number\>
* MYENERGI_PASSWORD=\<API key\>

## Obtaining an API key
Follow instructions at https://support.myenergi.com/hc/en-gb/articles/5069627351185-How-do-I-get-an-API-key

## MQTT Topics

### \<MQTT_TOPIC\>\/sensors\/\<device\>/\<sno\>
This topic is populated with a JSON payload representing sensor data from this device.
### \<MQTT_TOPIC\>\/boost\/\<device\>/\<sno\>
This topic is populated with a JSON payload representing boost timer settings from this device. This is only collected for Eddi, Libbi, or Zappi devices.
### \<MQTT_TOPIC\>\/SetTimerSettings\/\<device\>/\<sno\>\/\<slt\>
The client posts to this topic to initiate a boost timer setting. \<slt\> defines the single timer slot to be updated.

A JSON payload is posted with the following data fields:

- bsh - Boost Start Hour
- bsm - Boost Start Minute
- bdh - Boost Duration Hour
- bdm - Boost Duration Minute
- bdd - Boost Days of Week

These are checked for valid data and no action is taken on error, but a message is written to the log.

- Minute can only be 0, 15, 30, or 45
- Start hour must be from 0-23
- Duration hour:minute must be from 0 to 8 hours

### \<MQTT_TOPIC\>\/status
The \'status\' topic is used to report counts of HTTP return codes. In addition the latest return code is reported along with the current sleep_time.

Sleep_time initialises to 60 seconds, but doubles every time a 429 code is returned. This progressively backs off the request rate.

## Request priority
When a \'SetTimerSettings\' is received the parameters are pushed onto a queue.

The main loop will first check if there is something in the queue, and will take the first entry and send an API call to update a single boost timer slot. This is repeated every \'sleep_time\' until the queue is empty. Only then the sensor data will be requested for all devices in the system. Any Eddi, Libbi, or Zappi devices are then interrogated to acquire the current boost settings. For example, if the system comprises an Eddit, harvi, and zappi, three API calls will be made in the same cycle.