# Declaración de uso de inteligencia artificial: conexión con PostgreSQL

## Prompt realizado

> Necesito conectar la API `master`, desarrollada con FastAPI, con una base de datos PostgreSQL. Quiero centralizar la conexión en un archivo `master/database.py`, cargar `DATABASE_URL` desde las variables de entorno, crear las sesiones con SQLAlchemy y disponer de una dependencia que abra y cierre una sesión para cada solicitud. ¿Cómo puedo implementarlo y qué función cumple cada parte?

## Herramienta utilizada

ChatGPT, modelo de OpenAI.

## Respuesta IA

La herramienta propuso crear en `master/database.py` la configuración de SQLAlchemy y la administración de las sesiones utilizadas por los endpoints de FastAPI.

La solución generada utiliza `python-dotenv` para cargar las variables locales, obtiene `DATABASE_URL` mediante `os.getenv` y detiene la aplicación con un error explícito cuando la variable no está configurada.

También se propuso utilizar `create_engine` con `pool_pre_ping=True`, de modo que SQLAlchemy compruebe el estado de las conexiones antes de reutilizarlas. Las sesiones se crean mediante `sessionmaker`, con confirmación manual de las transacciones.

Finalmente, se generó la función `get_db`, que entrega una sesión a cada solicitud y la cierra mediante un bloque `finally`.

El flujo propuesto fue:

```text
Endpoint FastAPI → get_db() → SessionLocal → engine → PostgreSQL
```

## Código generado con apoyo de IA

El contenido inicial de `master/database.py` fue propuesto completamente por ChatGPT:

```python
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL is not configured")


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    database = SessionLocal()

    try:
        yield database
    finally:
        database.close()
```