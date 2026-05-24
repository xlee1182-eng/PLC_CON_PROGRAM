FROM python:3.12.6-slim

COPY . /source

RUN apt update \
 && apt install -y dos2unix python3-pip

RUN pip install --upgrade pip

RUN dos2unix /source/docker-entrypoint.sh

RUN chmod +x /source/docker-entrypoint.sh

RUN cp /source/Config.json.default /source/Config.json

WORKDIR /source

RUN pip install -r requirements.txt

ENTRYPOINT [ "/source/docker-entrypoint.sh" ]
