# Uso de IA: Docker y Docker Compose

## Herramienta utilizada

ChatGPT, modelo de OpenAI.

## Prompt

Tengo una aplicación EnergyShark compuesta por:

1. Una API `master` desarrollada con FastAPI.
2. Un servicio `connector` desarrollado en Python que consume RabbitMQ.
3. Una base de datos PostgreSQL.

Necesito containerizar los tres componentes mediante Docker Compose.

`master` debe conectarse a PostgreSQL, `connector` debe enviar eventos mediante HTTP POST hacia `master` y los tres servicios deben compartir una red interna.

También necesito:

- Persistencia para PostgreSQL.
- Variables de entorno sin incorporar credenciales al código.
- Healthchecks para los tres contenedores.
- Dependencias basadas en el estado saludable de los servicios.
- Reinicio automático de los servicios.
- Un Dockerfile para `master`.
- Un Dockerfile para `connector`.
- Evitar que PostgreSQL quede expuesto públicamente en EC2.

Explícame la configuración propuesta y los comandos necesarios para construir, iniciar y comprobar los servicios.

## Respuesta IA

La IA propuso utilizar un archivo `docker-compose.yml` con tres servicios:

```text
database
master
connector
```

Docker Compose crea una red interna para el proyecto. Cada servicio puede localizar a los demás utilizando su nombre.

La comunicación interna queda configurada de la siguiente manera:

```text
connector → http://master:8000/events
master → database:5432
```

## Servicio database

La IA propuso utilizar:

```text
postgres:17-alpine
```

La configuración recibe mediante variables de entorno:

```text
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
```

PostgreSQL utiliza un volumen persistente:

```text
postgres_data:/var/lib/postgresql/data
```

El volumen mantiene los eventos aunque el contenedor sea detenido o reconstruido.

En EC2 no se publica el puerto de PostgreSQL hacia internet. Solamente los servicios pertenecientes a la red de Docker Compose pueden conectarse utilizando:

```text
database:5432
```

## Servicio master

`master` se construye utilizando:

```text
master/Dockerfile
```

La IA propuso ejecutar FastAPI mediante Uvicorn:

```text
uvicorn master.main:app --host 0.0.0.0 --port 8000
```

El contenedor recibe una dirección de conexión a PostgreSQL mediante la variable:

```text
DATABASE_URL
```

La dirección utiliza el nombre interno `database`:

```text
postgresql+psycopg://usuario:contraseña@database:5432/base_de_datos
```

El puerto 8000 se publica para que Nginx, instalado directamente en EC2, pueda comunicarse con la API.

`master` depende de que PostgreSQL se encuentre saludable antes de iniciar.

## Servicio connector

`connector` se construye utilizando:

```text
connector/Dockerfile
```

El contenedor recibe mediante variables de entorno:

```text
RABBITMQ_HOST
RABBITMQ_PORT
RABBITMQ_VHOST
RABBITMQ_USER
RABBITMQ_PASSWORD
RABBITMQ_QUEUE
MASTER_URL
```

La comunicación con la API utiliza:

```text
MASTER_URL=http://master:8000/events
```

El nombre `master` es resuelto mediante la red interna de Docker Compose.

`connector` depende de que `master` aparezca saludable antes de iniciar.

## Variables de entorno

La IA propuso almacenar los valores reales en:

```text
.env
```

Este archivo está excluido mediante `.gitignore`.

El repositorio contiene:

```text
.env.example
```

con valores de ejemplo que permiten conocer las variables requeridas sin publicar credenciales.

## Healthchecks

La IA ayudó a configurar healthchecks para los tres servicios.

### PostgreSQL

PostgreSQL utiliza:

```bash
pg_isready
```

para comprobar que la base de datos pueda aceptar conexiones.

### Master

Master consulta:

```text
/health
```

El endpoint comprueba que FastAPI esté funcionando y ejecuta una consulta sencilla sobre PostgreSQL.

### Connector

Connector utiliza un archivo de estado:

```text
/tmp/connector_healthy
```

El archivo es revisado por el healthcheck del contenedor sin necesidad de crear una API HTTP adicional.

## Dependencias

La IA propuso utilizar condiciones de salud para establecer el orden de inicio:

```text
database saludable
    ↓
master saludable
    ↓
connector
```

Esto evita que `master` intente utilizar PostgreSQL antes de que la base de datos pueda aceptar conexiones y evita que `connector` envíe eventos antes de que la API esté disponible.

## Reinicio automático

Los servicios utilizan:

```text
restart: unless-stopped
```

Esto permite reiniciar los contenedores después de una caída o del reinicio de EC2, excepto cuando fueron detenidos manualmente.

## Dockerfiles

La IA apoyó la creación de:

```text
master/Dockerfile
connector/Dockerfile
```

Ambos utilizan una imagen de Python, instalan las dependencias desde `requirements.txt`, copian el código correspondiente y definen el comando de ejecución.

La versión definitiva se encuentra en los Dockerfiles del repositorio.

## Comandos utilizados

Validar la configuración:

```bash
docker compose config --quiet
```

Construir e iniciar los servicios:

```bash
docker compose up -d --build
```

Revisar el estado:

```bash
docker compose ps
```

Revisar los registros del connector:

```bash
docker compose logs --tail=100 connector
```

Reconstruir solamente master:

```bash
docker compose up -d --build master
```

Reconstruir solamente connector:

```bash
docker compose up -d --build connector
```

Detener los servicios sin eliminar los datos:

```bash
docker compose down
```

No se debe utilizar:

```bash
docker compose down -v
```

durante una actualización, porque `-v` elimina el volumen de PostgreSQL.
