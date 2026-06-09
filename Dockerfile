FROM python:3.11-slim

# Install gh CLI
RUN apt-get update && apt-get install -y curl git && \
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list && \
    apt-get update && apt-get install -y gh && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml .
COPY autopr/ autopr/
COPY server.py agent.py main.py ./

RUN pip install --no-cache-dir -e .

# Configure gh with token at runtime
ENV GH_TOKEN=""
ENV DASHSCOPE_API_KEY=""
ENV PORT=7860

EXPOSE 7860
CMD ["python", "main.py"]
