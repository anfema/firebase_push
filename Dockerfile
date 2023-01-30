# syntax=docker/dockerfile:1
FROM python:3.11

ARG USERNAME=code
ARG USER_UID=1000
ARG USER_GID=$USER_UID

ENV PYTHONUNBUFFERED=1

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID --shell /bin/bash -m $USERNAME \
    && apt-get update \
    && apt-get --no-install-recommends install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && mkdir /data && chown $USER_UID:$USER_GID /data \
    && rm -rf /var/lib/apt/lists/

WORKDIR /code

# copy files required to build/install dependencies (this should cache the next `RUN` if none of the files was changed)
COPY Pipfile Pipfile.lock pyproject.toml /code/
COPY firebase_push/__init__.py /code/firebase_push/

RUN python -m pip install pipenv && pipenv sync --system --dev && rm -rf ~/.cache ~/.local

# COPY . /code/
VOLUME /code

USER $USERNAME

# This starts only the web service, you'll need another instance which starts the celery worker
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# To run the celery worker use this command:
# CMD ["celery", "--app", "demo", "worker"]