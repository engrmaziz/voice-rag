FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc python3-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Make the script executable
RUN chmod +x entrypoint.sh
EXPOSE 7860
# Use the script as the entrypoint
CMD ["./entrypoint.sh"]