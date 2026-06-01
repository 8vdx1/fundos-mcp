FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
ENV FUNDOS_API_KEY=""
ENV FUNDOS_BASE_URL="https://www.kela.com"
CMD ["python", "server.py"]
