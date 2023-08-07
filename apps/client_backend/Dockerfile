FROM --platform=linux/amd64 python:3.9-slim-bullseye

# get portaudio and ffmpeg
# RUN apt-get update \
#         && apt-get install build-essential libssl-dev ca-certificates libasound2 wget libportaudio2 libportaudiocpp0 portaudio19-dev libasound-dev libsndfile1-dev -y
RUN apt-get -y update
RUN apt-get -y upgrade
#RUN apt-get install -y ffmpeg

WORKDIR /code

COPY /dist/vocode-0.1.111a0-py3-none-any.whl /code/vocode-0.1.111a0-py3-none-any.whl
COPY /apps/client_backend/pyproject.toml /code/pyproject.toml
# COPY /apps/client_backend/poetry.lock /code/poetry.lock
RUN pip install --no-cache-dir --upgrade poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev --no-interaction --no-ansi
COPY /apps/client_backend/main.py /code/main.py

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]