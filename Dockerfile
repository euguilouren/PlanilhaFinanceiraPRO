FROM python:3.11-slim

WORKDIR /app

# Dependências do sistema para WeasyPrint (PDF opcional)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev libcairo2 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Volumes para entrada/saída de dados
VOLUME ["/app/pasta_entrada", "/app/pasta_saida"]

# EMAIL_SENHA não deve ser declarado aqui — injete via variável de ambiente do host:
#   export EMAIL_SENHA="sua_senha" && docker compose up
# Ou use um arquivo .env (não commitado) com docker compose --env-file .env up

CMD ["python", "motor_automatico.py"]
