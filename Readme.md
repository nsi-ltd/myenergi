**Myenergi.py**

A simple Python script to register with the Myenergi API and post data periodically
to an MQTT topic. The collection rate is hard coded to 60 seconds but could e changed.

The Python code can be run from the command line, but reqires environment variables to be set.

A Docker build configuration integrates the Python code into a Docker image.

A Docker compose script provides the startup of a ruunning container.

The docker-compose.yml takes environment variables from the hidden .env file.

**.env file**
MQTT_HOST=<IP address or domain name of MQTT broker service.>
MQTT_PORT=<TCP port of MQTT broker service.>
MQTT_TOPIC=<Topic for Myenergi posting (default '/myenergi')>
MYENERGI_URL=<URL of Myeneri API>
MYENERGI_USER=<User for Myenergi API, usally the site number>
MYENERGI_PASSWORD=<API key>

**Obtaining an API key**
Follow instructions at https://support.myenergi.com/hc/en-gb/articles/5069627351185-How-do-I-get-an-API-key
