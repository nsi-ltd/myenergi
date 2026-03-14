FROM python:3

WORKDIR /app
ADD requirements.txt requirements.txt
ADD myenergi.py myenergi.py

RUN apt-get update \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python"]
CMD ["-u", "myenergi.py"]
