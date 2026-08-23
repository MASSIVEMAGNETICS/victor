FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY . /app
RUN python -m unittest discover -s tests -v
VOLUME ["/data"]
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/health',timeout=3).read()"
CMD ["python","serve_omni.py","--db","/data/signal_society_25.db","--host","0.0.0.0","--port","8787"]
