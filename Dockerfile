FROM ubuntu:22.04

ARG GRADIO_SERVER_PORT=80
ENV GRADIO_SERVER_PORT=${GRADIO_SERVER_PORT}
EXPOSE ${GRADIO_SERVER_PORT}

RUN apt update
RUN apt install -y python3.11
RUN apt install -y python3-pip
RUN apt install -y ffmpeg
RUN apt install -y imagemagick

COPY ./policy.xml /etc/ImageMagick-6/policy.xml
COPY ./requirements.txt /workspace/requirements.txt

RUN python3 -m pip install --upgrade pip

RUN pip3 install -r /workspace/requirements.txt

RUN playwright install --with-deps chromium

COPY ./__INSTANCE__ /workspace/__INSTANCE__

COPY ./setup_update_folders.py /workspace/setup_update_folders.py

COPY ./ui.py /workspace/ui.py

COPY ./default_config.ini /workspace/default_config.ini

COPY . /workspace

WORKDIR /workspace

CMD python3 /workspace/setup_update_folders.py ; python3 /workspace/ui.py