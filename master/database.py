import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL is not configured")

# Se crea un motor de base de datos con SQLAlchemy utilizando la URL proporcionada.
# pool_pre_ping=True comprueba que una conexión almacenada siga funcionando antes de reutilizarla.
# Si PostgreSQL reinició y la conexión quedó obsoleta, SQLAlchemy intenta reemplazarla
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

# Se crea una fábrica de sesiones:
# bind=engine: vincula las sesiones con PostgreSQL.
# autoflush=False: evita enviar cambios automáticamente antes de determinadas consultas.
# autocommit=False: exige ejecutar commit() expresamente para guardar cambios.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

# Se define una clase base para los modelos de SQLAlchemy.
class Base(DeclarativeBase):
    pass

# SQLAlchemy registra el modelo dentro de Base.metadata.
def get_db():
    database = SessionLocal()

    try:
        yield database
    finally:
        database.close()