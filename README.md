# Fluxo SQL RAG LLM para Registros de Servico

Prototipo de aplicacao web que registra servicos em um banco SQL e cria uma
projecao vetorial em RAG para consulta por LLMs.

A ideia central e manter o SQLite como fonte primaria dos registros operacionais e
usar o ChromaDB como uma camada derivada de busca semantica. Cada registro salvo no
SQL e transformado em texto, convertido em embedding e indexado no banco vetorial.
Depois, uma pergunta em linguagem natural tambem vira embedding, recupera registros
similares e envia esses contextos para uma LLM local via LM Studio.

## Objetivo

Demonstrar um fluxo completo de consulta semantica sobre registros estruturados:

```text
formulario -> SQLite -> texto semantico -> embedding -> ChromaDB -> busca RAG -> LLM
```

O prototipo cobre:

- cadastro de registros de servico;
- persistencia dos dados originais em SQLite;
- controle do estado de indexacao no proprio SQL;
- geracao de embeddings via LM Studio;
- indexacao e busca semantica com ChromaDB;
- consulta em linguagem natural com resposta gerada por LLM;
- frontend simples em HTML, CSS e JavaScript puro;
- backend em FastAPI organizado em camadas.

## Arquitetura

```text
Usuario
  -> Frontend HTML/CSS/JS
  -> API FastAPI
  -> SQLite como fonte primaria
  -> LM Studio para embeddings
  -> ChromaDB como projecao vetorial
  -> LM Studio para resposta da LLM
```

O backend esta dividido em camadas:

```text
backend/app/
  nucleo/          configuracoes da aplicacao
  dominio/         entidade, objetos de valor e portas
  aplicacao/       casos de uso
  infraestrutura/  SQLite, ChromaDB, LM Studio e container
  interfaces/http/ rotas FastAPI
```

Pontos importantes da arquitetura:

- O SQLite guarda o registro original e o estado da indexacao.
- O ChromaDB nao substitui o SQL; ele e uma representacao vetorial derivada.
- O id do documento vetorial corresponde ao id do registro SQL.
- Se a geracao de embedding ou a indexacao falhar, o registro continua salvo no SQL.
- Registros pendentes, com erro, com hash alterado ou com outro modelo de embedding
  podem ser reprocessados pela camada de aplicacao.

## Stack

- **Frontend:** HTML, CSS e JavaScript puro com ES modules.
- **Backend:** Python 3.12, FastAPI e Uvicorn.
- **Validacao/configuracao:** Pydantic e pydantic-settings.
- **Banco SQL:** SQLite.
- **Banco vetorial:** ChromaDB persistido em disco.
- **Cliente HTTP:** httpx.
- **LLM e embeddings:** LM Studio com endpoints locais.
- **Execucao containerizada:** Docker Compose.

## Estrutura do Repositorio

```text
backend/
  Dockerfile
  requirements.txt
  app/
    principal.py
    nucleo/
    dominio/
    aplicacao/
    infraestrutura/
    interfaces/http/
  tests/
frontend/
  index.html
  styles.css
  js/
docker-compose.yml
README.md
```

## Requisitos

Para rodar com Docker:

- Docker;
- Docker Compose;
- LM Studio instalado e com servidor local ativo.

Para rodar sem Docker:

- Python 3.12;
- pip;
- LM Studio instalado e com servidor local ativo.

## Preparar o LM Studio

O LM Studio deve estar aberto separadamente da aplicacao.

1. Abra o LM Studio.
2. Carregue um modelo LLM para chat.
3. Garanta que o modelo de embedding configurado esteja disponivel.
4. Ative o servidor local.

Servidor esperado fora do Docker:

```text
http://localhost:1234/v1
```

Quando a aplicacao roda em Docker, o container acessa o LM Studio no host por:

```text
http://host.docker.internal:1234/v1
```

Modelo de embedding usado por padrao:

```text
text-embedding-nomic-embed-text-v1.5
```

Se houver apenas uma LLM carregada no LM Studio, ela sera usada automaticamente. Se
houver mais de uma, a interface exibira um seletor antes da consulta.

## Rodar com Docker

Na raiz do projeto:

```bash
docker compose up --build
```

Acesse:

```text
http://localhost:8080
```

Swagger/OpenAPI:

```text
http://localhost:8080/docs
```

Os dados locais ficam em:

```text
dados/
```

Essa pasta e ignorada pelo Git.

## Rodar sem Docker

Na raiz do projeto, crie e ative um ambiente virtual.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

Configure as variaveis para execucao local:

```powershell
$env:PYTHONPATH = "backend"
$env:BANCO_SQLITE = "dados/registros.db"
$env:DIRETORIO_CHROMA = "dados/chroma"
$env:LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
$env:MODELO_EMBEDDING = "text-embedding-nomic-embed-text-v1.5"
$env:LIMITE_CONTEXTO = "3"
$env:MAX_TOKENS_RESPOSTA = "900"
```

Suba a API:

```powershell
python -m uvicorn app.principal:aplicacao_api --host 0.0.0.0 --port 8000
```

Acesse:

```text
http://localhost:8000
```

Swagger/OpenAPI:

```text
http://localhost:8000/docs
```

## Como Usar a Interface

### 1. Novo registro

Preencha o formulario com:

- funcionario;
- cliente ou local;
- tipo de servico;
- status;
- data;
- descricao;
- problemas encontrados;
- observacoes importantes.

Ao salvar, a aplicacao:

1. grava o registro no SQLite;
2. gera o texto semantico do registro;
3. solicita o embedding ao LM Studio;
4. indexa o documento no ChromaDB;
5. marca no SQLite se a indexacao foi concluida ou falhou.

### 2. Registros

A aba de registros lista os dados salvos no SQLite. Essa listagem nao depende do
ChromaDB, pois o SQL e a fonte primaria.

### 3. Consulta IA

Na aba de consulta:

1. confirme ou selecione o modelo LLM carregado;
2. escreva uma pergunta em linguagem natural;
3. envie a consulta.

Exemplo:

```text
Quais servicos tiveram problema com sensores?
```

A aplicacao gera embedding da pergunta, busca registros similares no ChromaDB e envia
os contextos recuperados para a LLM responder.

## Endpoints Principais

| Metodo | Caminho | Funcao |
| --- | --- | --- |
| `GET` | `/api/saude` | Verifica se a API esta ativa. |
| `GET` | `/api/registros` | Lista registros salvos no SQLite. |
| `POST` | `/api/registros` | Cria registro e tenta indexar no RAG. |
| `POST` | `/api/consulta` | Executa consulta semantica com LLM. |
| `GET` | `/api/modelos/chat` | Lista modelos LLM carregados no LM Studio. |
| `POST` | `/api/modelos/chat/selecionar` | Seleciona o modelo de chat ativo. |

## Como Testar

Compilar os arquivos Python:

```bash
python -m compileall backend
```

Rodar testes unitarios:

```bash
python -m unittest discover -s backend/tests
```

Validar o Docker Compose:

```bash
docker compose config
```

Teste manual recomendado:

1. Inicie o LM Studio.
2. Suba a aplicacao com Docker ou Uvicorn.
3. Cadastre um registro pela interface.
4. Abra a aba "Registros" e confirme que ele aparece.
5. Abra a aba "Consulta IA".
6. Faca uma pergunta relacionada ao registro.
7. Verifique se a resposta usa o conteudo cadastrado.

## Proximos Passos

### Integrar com mais fontes de LLMs

A arquitetura ja possui portas para embeddings e geracao de resposta. O proximo passo
natural e criar adaptadores adicionais alem do LM Studio:

- **OpenAI API:** usar modelos hospedados para chat e embeddings, com boa estabilidade
  operacional e baixa friccao de integracao.
- **Azure OpenAI:** alternativa para ambientes corporativos que precisam de governanca,
  controle de acesso e integracao com recursos Azure.
- **Ollama:** opcao local para executar modelos abertos diretamente na maquina ou em
  servidor proprio, mantendo dados fora de provedores externos.
- **Google Gemini:** provedor de modelos generativos e embeddings, util para comparar
  qualidade de respostas e recuperacao em outro ecossistema.
- **Anthropic Claude:** boa opcao para geracao textual; para embeddings, pode ser
  combinado com outro provedor especializado.
- **OpenRouter:** camada agregadora para acessar varios modelos por uma API unica,
  facilitando testes comparativos.
- **Together AI, Groq ou Fireworks:** provedores de inferencia com foco em desempenho,
  uteis para avaliar latencia e custo por resposta.
- **Hugging Face Inference ou Text Embeddings Inference:** caminho para hospedar ou
  consumir modelos abertos de embeddings com maior controle tecnico.

Uma evolucao recomendada e criar uma configuracao de provedor:

```text
PROVEDOR_LLM=lm_studio | openai | azure_openai | ollama | gemini | openrouter
PROVEDOR_EMBEDDINGS=lm_studio | openai | huggingface | ollama
```

Com isso, os casos de uso continuariam dependendo das mesmas portas:

- `ServicoEmbeddings`
- `ServicoLLM`

E a infraestrutura escolheria o adaptador concreto em tempo de configuracao.

### Melhorias adicionais

- Expor reindexacao de registros pendentes por endpoint administrativo.
- Mostrar fontes e contextos recuperados na interface.
- Adicionar filtros por funcionario, cliente, status e data.
- Persistir historico de perguntas e respostas.
- Configurar limiar de similaridade para evitar respostas com contexto fraco.
- Criar avaliacao automatizada de qualidade da recuperacao.
- Separar a integracao com LM Studio em componentes menores.
- Adicionar autenticacao e controle de acesso.

