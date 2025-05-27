FROM python:3.10-slim-buster
WORKDIR /app
COPY . /app

RUN apt update -y && apt install awscli -y

# Create necessary directories
RUN mkdir -p /app/Get_Data/BB && \
    mkdir -p /app/Get_Data/UD && \
    mkdir -p /app/logs && \
    chmod 777 /app/logs /app/Get_Data /app/Get_Data/BB /app/Get_Data/UD

# Install dependencies
RUN pip install -r requirements.txt
RUN pip install -e .

# Run application
CMD ["python", "main.py"]