FROM python:3.12-slim

WORKDIR /app

# Install the Synapse layer, then the example.
COPY synapse/ /opt/synapse/
RUN pip install --no-cache-dir '/opt/synapse[tracing,mcp]'

COPY synapse/examples/deep_research/agent.py /app/agent.py

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

EXPOSE 8080
CMD ["python", "agent.py"]
