# Choosing a specific version instead of latest for more control over
# system and package versions, and to avoid breaking changes.
FROM ubuntu:mantic

RUN apt-get update && \
    apt-get install -y libpq-dev python3 python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /messegger
COPY . .
RUN pip3 install --break-system-packages -r requirements.txt

CMD ["python3", "run.py"]
