FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./

RUN apt update && \
    apt install -y wget && \
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt install -y ./google-chrome-stable_current_amd64.deb && \
    apt install -y libglib2.0-0 libnss3 libfontconfig1 google-chrome-stable && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# CMD ["sleep", "3600"]
ENTRYPOINT ["python", "./main.py"]
