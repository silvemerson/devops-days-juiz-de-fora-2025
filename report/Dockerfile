FROM alpine AS downloader
WORKDIR /tmp
RUN wget -q https://github.com/k8sgpt-ai/k8sgpt/releases/latest/download/k8sgpt_Linux_x86_64.tar.gz && \
    tar -xzf k8sgpt_Linux_x86_64.tar.gz

FROM python:3.10-slim

WORKDIR /k8sgpt-report

COPY requirements.txt .
COPY coleta_relatorio.py .
COPY app.py .

RUN pip install -r requirements.txt

COPY --from=downloader /tmp/k8sgpt /usr/local/bin/k8sgpt

RUN chmod +x /usr/local/bin/k8sgpt

EXPOSE 5000

ENTRYPOINT ["python", "app.py"]
