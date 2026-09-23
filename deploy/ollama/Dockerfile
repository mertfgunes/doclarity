FROM ollama/ollama:latest

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*

COPY proxy.py /proxy.py

ENV OLLAMA_HOST=0.0.0.0:11434

CMD ["sh", "-c", "ollama serve & sleep 5 && ollama pull llama3.2:3b && ollama pull nomic-embed-text && python3 /proxy.py"]
