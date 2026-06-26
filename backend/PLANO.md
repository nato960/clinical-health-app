# Plano: API FastAPI com Arquitetura em Camadas + PostgreSQL

## Contexto

Projeto de estudo para construir uma API CRUD com FastAPI, seguindo separação em camadas (API, Service, Repository, Core) e validação com Pydantic. O banco de dados será PostgreSQL, provisionado via Docker Compose. O diretório `app/` já existe e está vazio; as dependências FastAPI, SQLAlchemy e Pydantic já estão instaladas no `venv/`.

---

## Estado Atual do Projeto

```javascript
FastAPI test/
├── app/          ← vazio, tudo será criado aqui
├── venv/         ← já configurado
└── requirements.txt  ← FastAPI 0.138, SQLAlchemy 2.0, Pydantic 2.13
```

**Dependências que ainda precisam ser adicionadas ao requirements.txt:**

- `asyncpg` — driver PostgreSQL async para SQLAlchemy (usado pela aplicação)
- `psycopg2-binary` — driver PostgreSQL sync, mantido **exclusivamente para o Alembic** (migrations rodam em contexto síncrono)
- `alembic` — migrations de banco de dados
- `pydantic-settings` — gerenciamento de configurações via `.env`
- `python-dotenv` — leitura do arquivo `.env`

---

## Estrutura de Pastas Final

```javascript
FastAPI test/
├── app/
│   ├── main.py                  ← ponto de entrada da aplicação
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── routers/
│   │           ├── __init__.py
│   │           └── doctors.py   ← endpoints REST do recurso Doctor
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            ← configurações via variáveis de ambiente
│   │   └── database.py          ← engine e sessão do SQLAlchemy
│   ├── models/
│   │   ├── __init__.py
│   │   ├── enums.py             ← enums compartilhados (ex: Speciality)
│   │   ├── address.py           ← modelo ORM Address (reutilizado por múltiplas entidades)
│   │   └── doctor.py            ← modelo ORM Doctor
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── doctor.py            ← schemas Pydantic (request/response)
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── doctor_repository.py ← acesso ao banco (queries SQL via ORM)
│   └── services/
│       ├── __init__.py
│       └── doctor_service.py    ← lógica de negócio / orquestração
├── alembic/                     ← gerado pelo alembic init
├── alembic.ini
├── docker-compose.yml
├── .env                         ← variáveis de ambiente (não commitar)
├── .env.example                 ← modelo do .env para o repositório
└── requirements.txt
```

---

## Responsabilidade de Cada Camada

| Camada         | Arquivo                                 | Responsabilidade                                                               |
| -------------- | --------------------------------------- | ------------------------------------------------------------------------------ |
| **API**        | `api/v1/routers/doctors.py`             | Recebe requisição HTTP, valida via schema, delega ao service, retorna resposta |
| **Schema**     | `schemas/doctor.py`                     | Define shape dos dados de entrada e saída com Pydantic                         |
| **Service**    | `services/doctor_service.py`            | Orquestra regras, chama repository, lança exceções de negócio                  |
| **Repository** | `repositories/doctor_repository.py`     | Executa queries no banco via ORM, não conhece HTTP                             |
| **Model**      | `models/doctor.py`, `models/address.py` | Mapeamento ORM das tabelas no banco de dados                                   |
| **Core**       | `core/config.py`, `core/database.py`    | Configuração global: env vars, engine, sessão DB                               |

> **Regra de ouro:** cada camada só conhece a camada imediatamente abaixo dela. A API não fala com o repository diretamente.

---

## Etapas de Implementação

### Etapa 1 — Configuração do Ambiente

1. Adicionar as novas dependências ao `requirements.txt`
2. Instalar com `pip install -r requirements.txt` (dentro do venv)
3. Criar o arquivo `.env` na raiz com as variáveis:
4. Criar `.env.example` com os mesmos campos (valores em branco ou fictícios)

---

### Etapa 2 — Docker Compose (PostgreSQL)

Criar `docker-compose.yml` na raiz:

```yaml
version: "3.9"
services:
  db:
    image: postgres:16
    container_name: fastapi_postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: fastapi_db
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

Subir com: `docker compose up -d`

---

### Etapa 3 — Core: Config e Database

**app/core/config.py** — usa `pydantic-settings` para ler o `.env`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    app_env: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()
```

**app/core/database.py** — cria engine e session factory **async** do SQLAlchemy:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,  # detecta conexões mortas antes de usá-las
    pool_recycle=1800,   # recicla conexões a cada 30min
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():  # dependency injection para as rotas
    async with SessionLocal() as db:
        yield db
```

> `expire_on_commit=False` é obrigatório no modo async: sem ele, acessar atributos de um objeto após `commit` dispara um lazy load que falha porque a sessão já foi fechada.

> **.env:** o `DATABASE_URL` deve usar o prefixo `postgresql+asyncpg://`
> Exemplo: `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/fastapi_db`

---

### Etapa 4 — Models ORM

**app/models/enums.py** — enums compartilhados entre models e schemas:

```python
import enum

class Speciality(enum.Enum):
    CARDIOLOGIA = "CARDIOLOGIA"
    DERMATOLOGIA = "DERMATOLOGIA"
    ORTOPEDIA = "ORTOPEDIA"
    PEDIATRIA = "PEDIATRIA"
    PSIQUIATRIA = "PSIQUIATRIA"
    GINECOLOGIA = "GINECOLOGIA"
    NEUROLOGIA = "NEUROLOGIA"
```

**app/models/address.py** — entidade reutilizável por Doctor, Patient e outras:

```python
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.database import Base

class Address(Base):
    __tablename__ = "addresses"

    id         : Mapped[int]       = mapped_column(primary_key=True)
    street     : Mapped[str | None] = mapped_column(String, default=None)
    city       : Mapped[str | None] = mapped_column(String, default=None)
    state      : Mapped[str | None] = mapped_column(String(2), default=None)
    zip_code   : Mapped[str | None] = mapped_column(String, default=None)
    created_at : Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at : Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**app/models/doctor.py**:

```python
from datetime import date, datetime
from sqlalchemy import String, Date, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import Speciality

class Doctor(Base):
    __tablename__ = "doctors"

    id         : Mapped[int]          = mapped_column(primary_key=True)
    name       : Mapped[str]          = mapped_column(String)
    email      : Mapped[str]          = mapped_column(String)
    crm        : Mapped[str]          = mapped_column(String, unique=True)
    birth_date : Mapped[date | None]  = mapped_column(Date, default=None)
    phone      : Mapped[str | None]   = mapped_column(String, default=None)
    speciality : Mapped[Speciality]   = mapped_column(SAEnum(Speciality))
    active     : Mapped[bool]         = mapped_column(Boolean, default=True)
    created_at : Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at : Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    address_id : Mapped[int | None]        = mapped_column(ForeignKey("addresses.id"), default=None)
    address    : Mapped["Address | None"]  = relationship("Address", lazy="selectin")
```



> `Mapped[str]` implica `NOT NULL` e `Mapped[str | None]` implica `NULL` — `nullable` explícito não é mais necessário.

> `lazy="selectin"` é obrigatório no async — o padrão `lazy="select"` exigiria um `await` implícito ao acessar o atributo, o que não é possível em async.

> `enums.py` separado evita importação circular: os mesmos enums são usados tanto nos models quanto nos schemas Pydantic.

---

### Etapa 5 — Schemas Pydantic

**app/schemas/doctor.py** — separa schema de entrada do de saída:

```python
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel
from app.models.enums import Speciality

class AddressSchema(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    model_config = {"from_attributes": True}

class DoctorCreate(BaseModel):   # POST body
    name: str
    email: str
    crm: str
    birth_date: Optional[date] = None
    phone: Optional[str] = None
    speciality: Speciality
    address: Optional[AddressSchema] = None

class DoctorUpdate(BaseModel):   # PUT body (campos opcionais)
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[AddressSchema] = None

class DoctorResponse(BaseModel): # resposta da API
    id: int
    name: str
    email: str
    crm: str
    birth_date: Optional[date]
    phone: Optional[str]
    speciality: Speciality
    active: bool
    address: Optional[AddressSchema]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

---

### Etapa 6 — Repository

**app/repositories/doctor\_repository.py** — só faz acesso a dados:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.doctor import Doctor
from app.schemas.doctor import DoctorCreate, DoctorUpdate

class DoctorRepository:
    async def get_all(self, db: AsyncSession) -> list[Doctor]: ...
    async def get_by_id(self, db: AsyncSession, doctor_id: int) -> Doctor | None: ...
    async def create(self, db: AsyncSession, data: DoctorCreate) -> Doctor: ...
    async def update(self, db: AsyncSession, doctor: Doctor, data: DoctorUpdate) -> Doctor: ...
    async def deactivate(self, db: AsyncSession, doctor: Doctor) -> None: ...
```

> Queries usam `select()` em vez de `.query()` — a API legada não funciona com `AsyncSession`.

> `deactivate` faz soft delete: seta `active = False` em vez de deletar o registro.

---

### Etapa 7 — Service

**app/services/doctor\_service.py** — orquestra e lança exceções:

```python
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.doctor_repository import DoctorRepository
from app.schemas.doctor import DoctorCreate, DoctorUpdate

class DoctorService:
    def __init__(self):
        self.repo = DoctorRepository()

    async def get_all(self, db: AsyncSession): ...
    async def get_by_id(self, db: AsyncSession, doctor_id: int): ...  # lança 404 se não achar
    async def create(self, db: AsyncSession, data: DoctorCreate): ...
    async def update(self, db: AsyncSession, doctor_id: int, data: DoctorUpdate): ...
    async def deactivate(self, db: AsyncSession, doctor_id: int): ...
```

---

### Etapa 8 — Router (API Layer)

**app/api/v1/routers/doctors.py** — endpoints REST:

| Método | Rota            | Ação                   |
| ------ | --------------- | ---------------------- |
| GET    | `/doctors`      | lista todos os ativos  |
| GET    | `/doctors/{id}` | busca por ID           |
| POST   | `/doctors`      | cadastra novo          |
| PUT    | `/doctors/{id}` | atualiza dados         |
| DELETE | `/doctors/{id}` | desativa (soft delete) |

Todos os handlers são `async def`. Usa `Depends(get_db)` para injeção da `AsyncSession` e `Depends(DoctorService)` para o serviço. Chamadas ao service levam `await`.

---

### Etapa 9 — Main (Entry Point)

**app/main.py** — registra os routers e configura o app:

```python
from fastapi import FastAPI
from app.api.v1.routers import doctors

app = FastAPI(title="FastAPI Study")
app.include_router(doctors.router, prefix="/api/v1/doctors", tags=["Doctors"])
```

---

### Etapa 10 — Migrations com Alembic

1. Inicializar: `alembic init alembic`
2. Editar `alembic.ini`: apontar `sqlalchemy.url` com URL **síncrona** (sem `+asyncpg`):
   `sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/fastapi_db`
3. Editar `alembic/env.py`: importar `Base` dos models e usar `Base.metadata`
4. Criar primeira migration: `alembic revision --autogenerate -m "create doctors and addresses tables"`
5. Aplicar: `alembic upgrade head`

> **Atenção:** Alembic roda como CLI síncrono — não usa o `create_async_engine` da aplicação. Por isso `psycopg2-binary` permanece no requirements: é o driver usado exclusivamente pelo Alembic. A aplicação FastAPI usa `asyncpg`. São dois contextos distintos.

---

### Etapa 11 — Verificação End-to-End

1. Docker Compose rodando: `docker compose up -d`
2. Migrations aplicadas: `alembic upgrade head`
3. App rodando: `uvicorn app.main:app --reload`
4. Testar via Swagger UI em `http://localhost:8000/docs`
5. Validar todos os endpoints CRUD (cadastrar, listar, buscar, atualizar, desativar)
6. Confirmar que `speciality: "INVALIDA"` é rejeitado (422)
7. Confirmar que a resposta inclui `address` aninhado, `created_at` e `updated_at`

---

## Conceitos-Chave para Estudar em Cada Etapa

- **Etapa 3:** `pydantic-settings`, variáveis de ambiente, `create_async_engine`, `AsyncSession`, `async_sessionmaker`, `expire_on_commit=False`, por que `.query()` não funciona em modo async
- **Etapa 4:** `SAEnum` vs enum Python, `lazy="selectin"` no async, `ForeignKey` + `relationship`, por que separar `enums.py`; `Mapped[str]` vs `Mapped[str | None]` (NOT NULL vs NULL), `mapped_column` vs `Column` (novo vs legado)
- **Etapa 5:** diferença entre Model ORM e Schema Pydantic — propósitos distintos; `from_attributes=True` no Pydantic v2
- **Etapa 6/7:** inversão de dependência — Service não sabe SQL, Repository não sabe HTTP; soft delete vs. delete físico
- **Etapa 8:** `Depends()` do FastAPI — injeção de dependência nativa
- **Etapa 10:** migrations declarativas vs. imperativas no Alembic; dois drivers distintos (asyncpg vs. psycopg2)
