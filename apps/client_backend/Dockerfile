FROM python:3.9-slim-bullseye

# get portaudio and ffmpeg
RUN apt-get update \
        && apt-get install build-essential libssl-dev ca-certificates libasound2 wget libportaudio2 libportaudiocpp0 portaudio19-dev libasound-dev libsndfile1-dev -y
RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get install -y ffmpeg

WORKDIR /code
COPY /dist/vocode-0.1.110-py3-none-any.whl /code/vocode-0.1.110-py3-none-any.whl
COPY /apps/client_backend/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY /apps/client_backend/main.py /code/main.py

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]