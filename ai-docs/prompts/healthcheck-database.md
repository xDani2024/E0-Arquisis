# Declaración de uso de inteligencia artificial: mejora del healthcheck de master

## Prompt realizado

> Antes de desplegar la nueva versión en EC2, quiero revisar todo el código del proyecto para comprobar si está correcto y si cumple los requisitos del enunciado. Revisa especialmente la API, PostgreSQL, Docker Compose, los healthchecks, el connector, la seguridad y los archivos necesarios para la entrega.

## Herramienta utilizada

ChatGPT, modelo de OpenAI.

## Respuesta IA

Durante la revisión, ChatGPT detectó que el endpoint `/health` de `master` respondía siempre con el estado `healthy`, pero no comprobaba si la API podía conectarse con PostgreSQL.

La implementación anterior era:

```python
@app.get("/health")
def health():
    return {"status": "healthy"}
```

La herramienta indicó que este endpoint solo demostraba que FastAPI podía responder una solicitud HTTP. Si PostgreSQL se encontraba caído o inaccesible, `/health` igualmente podía responder exitosamente, aunque las funciones de almacenamiento y consulta no estuvieran operativas.

Para que el `HEALTHCHECK` verificara también la conexión con la base de datos, ChatGPT propuso ejecutar una consulta simple mediante la sesión de SQLAlchemy.

## Código generado con apoyo de IA

La modificación propuesta fue:

```python
@app.get("/health")
def health(
    database: Session = Depends(get_db),
):
    database.execute(select(1))

    return {
        "status": "healthy",
        "database": "connected",
    }
```