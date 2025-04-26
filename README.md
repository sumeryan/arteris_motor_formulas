markdown

\# Motor de Cálculo de Fórmulas com FastAPI

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)

Motor para avaliação de fórmulas complexas com suporte a múltiplas entidades e relacionamentos.

\## 📋 Funcionalidades

- ✅ Cálculo de fórmulas matemáticas complexas
- ✅ Suporte a múltiplos tipos de entidades
- ✅ Agregações com `SUM`
- ✅ Funções como `len()`
- ✅ Relacionamento entre entidades
- ✅ Validação de tipos de dados
- ✅ Docker integrado

\## 🚀 Começando

\### Pré-requisitos

- Docker 20.10+
- Docker Compose 1.29+
- Python 3.11 (opcional)

\### Instalação

1. Clone o repositório:

\```bash

git clone https://github.com/seu-usuario/motor-calculo-formulas.git

cd motor-calculo-formulas

Construa os containers:

bash

docker-compose build

Inicie o serviço:

bash

docker-compose up

Para desenvolvimento sem Docker:

bash

python -m venv venv

source venv/bin/activate  # Linux/MacOS

venv\Scripts\activate  # Windows

pip install -r requirements.txt

🛠 Uso

Executando o Servidor

bash

\# Com Docker (recomendado)

docker-compose up --build

\# Sem Docker

uvicorn app.main:app --reload

A API estará disponível em: http://localhost:8000

Documentação da API

Swagger UI: http://localhost:8000/docs

Redoc: http://localhost:8000/redoc

Exemplo de Requisição

json

POST /api/v1/calculate

{

"entities": [

{

"id": "contract\_1",

"entity\_type": ["Contract"],

"attributes": [

{"key": "value", "value": "1000", "type": "number"},

{"key": "tax", "value": "150", "type": "number"}

]

}

],

"formulas": [

"Contract.value + Contract.tax",

"Contract.value \* 2"

]

}

Exemplo de Resposta

json

{

"direct\_results": [

{

"entity\_id": "contract\_1",

"formula": "Contract.value + Contract.tax",

"resolved\_formula": "1000 + 150",

"result": 1150.0,

"result\_type": "float",

"error": null,

"success": true

}

],

"aggregated\_entities": []

}

📚 Documentação da API

Endpoints

POST /api/v1/calculate

Processa fórmulas e retorna resultados

Body:

json

{

"entities": [Entity],

"formulas": ["string"]

}

Respostas:

200: Sucesso

422: Erro de validação

500: Erro interno

🧪 Exemplos

Caso 1: Cálculos Simples

Exemplo completo na pasta /examples

Caso 2: Agregação Complexa

Exemplo completo na pasta /examples

🤝 Contribuição

Faça o fork do projeto

Crie sua branch (git checkout -b feature/nova-feature)

Commit suas mudanças (git commit -m 'Add nova feature')

Push para a branch (git push origin feature/nova-feature)

Abra um Pull Request

📄 Licença

Distribuído sob a licença MIT. Veja LICENSE para mais informações.

🛠 Tecnologias

FastAPI

Pydantic

asteval

Docker

Python 3.11

