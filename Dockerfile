# Estágio de construção
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    pip install --user -r requirements.txt

# Estágio final
FROM python:3.11-slim

WORKDIR /app

# Copiar as dependências instaladas
COPY --from=builder /root/.local /root/.local
COPY . .

# Variáveis de ambiente
ENV PYTHONPATH=/app
ENV PATH=/root/.local/bin:$PATH

# Porta exposta
EXPOSE 8000

