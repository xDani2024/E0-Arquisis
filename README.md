# EnergyShark E0

API desarrollada para recibir, almacenar y consultar eventos de demanda eléctrica enviados mediante RabbitMQ.

## Información general

- Estudiante: Daniela Muñoz Poblete
- Dominio principal: https://energyshark-danielamp.tech
- Dominio alternativo: https://www.energyshark-danielamp.tech
- Healthcheck: https://energyshark-danielamp.tech/health
- Documentación Swagger: https://energyshark-danielamp.tech/docs
- Proveedor cloud: AWS
- Instancia: EC2 `t3.micro`
- Sistema operativo: Ubuntu
- Parte variable seleccionada: HTTPS

## Arquitectura

El sistema utiliza los siguientes componentes:

- `connector`: consume eventos desde RabbitMQ mediante AMQPS.
- `master`: API desarrollada con FastAPI.
- `database`: base de datos PostgreSQL 17.
- `nginx`: proxy inverso instalado directamente en EC2.
- `certbot`: administra el certificado HTTPS de Let's Encrypt.

Flujo de recepción de eventos:

```text
Central de eventos
    ↓
RabbitMQ
    ↓
connector
    ↓ POST /events
master
    ↓
PostgreSQL
```

Flujo de consultas:

```text
Usuario
    ↓ HTTPS
Nginx
    ↓ HTTP interno
master
    ↓
PostgreSQL
```

Los servicios `connector`, `master` y `database` son administrados mediante Docker Compose. Nginx y Certbot están instalados directamente en la instancia EC2.

## Acceso al servidor

La llave privada `.pem` se entrega exclusivamente mediante Canvas y no está incluida en el repositorio.

Antes de conectarse, se deben ajustar sus permisos:

```bash
chmod 400 <archivo.pem>
```

Conexión mediante SSH:

```bash
ssh -i <archivo.pem> ubuntu@18.227.248.78
```

Una vez conectado:

```bash
cd ~/energyshark-e0
docker compose ps
```

Los servicios `master`, `connector` y `database` deben aparecer como `healthy`.

## Variables de entorno

Crear el archivo local de variables a partir del ejemplo:

```bash
cp .env.example .env
```

Luego se deben completar las credenciales y parámetros asignados para PostgreSQL y RabbitMQ.

El archivo `.env` está excluido mediante `.gitignore` y no debe subirse al repositorio.

Las variables utilizadas son:

```text
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
DATABASE_URL
RABBITMQ_HOST
RABBITMQ_PORT
RABBITMQ_VHOST
RABBITMQ_USER
RABBITMQ_PASSWORD
RABBITMQ_QUEUE
MASTER_URL
```

## Ejecución con Docker Compose

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
docker compose logs --tail=50 connector
```

Detener los contenedores sin eliminar el volumen de PostgreSQL:

```bash
docker compose down
```

No se debe utilizar `docker compose down -v`, porque esa opción elimina el volumen y los registros almacenados.

## Endpoints

### Healthcheck

```http
GET /health
```

Comprueba que la API esté operativa y que pueda consultar PostgreSQL.

Ejemplo:

```bash
curl https://energyshark-danielamp.tech/health
```

### Historial

```http
GET /history
```

Entrega el historial paginado. Por defecto utiliza:

```text
page=1
limit=25
```

Ejemplo:

```bash
curl "https://energyshark-danielamp.tech/history?page=2&limit=25"
```

La respuesta contiene:

```json
{
  "page": 1,
  "limit": 25,
  "total": 100,
  "records": []
}
```

### Detalle de un evento

```http
GET /history/{id}
```

Ejemplo:

```bash
curl "https://energyshark-danielamp.tech/history/1"
```

Si el registro no existe, la API responde con estado `404`.

### Recepción de eventos

```http
POST /events
```

Este endpoint es utilizado por `connector` para enviar a `master` los eventos consumidos desde RabbitMQ.

### Filtros

`GET /history` permite filtrar por:

- `id`
- `idpk`
- `type`
- `receivedAt`
- `city`
- `demand`
- `unit`
- `validUntil`
- `metaContent`
- `constraints`

Ejemplos:

```bash
curl "https://energyshark-danielamp.tech/history?type=demand-set"
```

```bash
curl "https://energyshark-danielamp.tech/history?city=Hogwarts"
```

```bash
curl "https://energyshark-danielamp.tech/history?receivedAt=2026-08-30"
```

```bash
curl -G "https://energyshark-danielamp.tech/history" \
  --data-urlencode 'constraints={}'
```

Los parámetros temporales utilizan fechas ISO 8601. El parámetro `constraints` debe contener un objeto JSON válido.

## Requisitos funcionales

| Requisito | Estado | Descripción |
|---|---|---|
| RF1 | Logrado | La API entrega el historial con todos los campos del evento, además de `id` y `receivedAt`. |
| RF2 | Logrado | El endpoint `/history/{id}` entrega el detalle de un registro mediante el ID generado por la aplicación. |
| RF3 | Logrado | El historial está paginado por defecto con 25 registros y permite modificar `page` y `limit`. |
| RF4 | Logrado | El historial permite filtrar por las propiedades del evento, incluidos los campos temporales y anidados. |

## Requisitos no funcionales

| Requisito | Estado | Descripción |
|---|---|---|
| RNF1 | Logrado | Connector consume RabbitMQ mediante AMQPS, envía eventos mediante HTTP POST y reintenta la conexión ante interrupciones. |
| RNF2 | Logrado | Master y connector están containerizados y se comunican en la red interna de Docker Compose. |
| RNF3 | Logrado | Nginx funciona como proxy inverso instalado directamente en EC2. |
| RNF4 | Logrado | El servidor utiliza el dominio público `energyshark-danielamp.tech`. |
| RNF5 | Logrado | El sistema está desplegado en una instancia AWS EC2. |
| RNF6 | Logrado | PostgreSQL funciona como servicio independiente con un volumen persistente. |
| RNF7 | Logrado | Master, connector y database poseen healthchecks y aparecen como saludables. |

## Docker Compose

| Requisito | Estado | Descripción |
|---|---|---|
| RNF1 | Logrado | Master se construye y ejecuta mediante Docker Compose. |
| RNF2 | Logrado | PostgreSQL está integrado mediante Docker Compose y utiliza un volumen persistente. |
| RNF3 | Logrado | Connector se ejecuta mediante Docker Compose y se comunica con master mediante HTTP POST. |

## Parte variable: HTTPS

| Requisito | Estado | Descripción |
|---|---|---|
| RNF1 | Logrado | El dominio utiliza un certificado SSL emitido por Let's Encrypt. |
| RNF2 | Logrado | Nginx redirige automáticamente las solicitudes HTTP hacia HTTPS. |
| RNF3 | Logrado | Certbot comprueba automáticamente el certificado dos veces al día mediante `systemd`. |

El certificado cubre:

```text
energyshark-danielamp.tech
www.energyshark-danielamp.tech
```

La programación automática de Certbot utiliza:

```ini
OnCalendar=*-*-* 00,12:00:00
RandomizedDelaySec=43200
Persistent=true
```

La renovación fue comprobada mediante:

```bash
sudo certbot renew --dry-run
```

## Balanceo de carga

No implementado. Para la parte variable se seleccionó HTTPS, cuyos tres requisitos fueron completados. El balanceo de carga corresponde a la segunda alternativa opcional.

## Nginx

La configuración utilizada en EC2 está incluida en:

```text
nginx/energyshark.conf
```

Nginx recibe solicitudes por los puertos 80 y 443 y las dirige internamente a `master` en el puerto 8000.

Los certificados y las llaves privadas permanecen exclusivamente en EC2. El repositorio solo contiene las rutas utilizadas por Nginx.

## Persistencia

PostgreSQL utiliza el volumen:

```text
energyshark-e0_postgres_data
```

El volumen mantiene los registros aunque los contenedores sean detenidos o reconstruidos.

## Pruebas principales

Comprobar HTTPS:

```bash
curl -I http://energyshark-danielamp.tech/health
curl https://energyshark-danielamp.tech/health
```

Comprobar el historial:

```bash
curl "https://energyshark-danielamp.tech/history?limit=1"
```

Comprobar los contenedores:

```bash
docker compose ps
```

Comprobar Nginx:

```bash
sudo nginx -t
sudo systemctl is-active nginx
```

Comprobar la renovación:

```bash
sudo certbot renew --dry-run
systemctl list-timers --all | grep certbot
```

## Uso de inteligencia artificial

Las consultas y respuestas relevantes relacionadas con el desarrollo se encuentran en:

```text
ai-docs/prompts/
```

La IA fue utilizada como apoyo para:

- Diseñar la arquitectura.
- Configurar PostgreSQL y SQLAlchemy.
- Implementar y comentar el connector.
- Configurar healthchecks.
- Diagnosticar errores de Docker y DNS.
- Configurar Nginx, HTTPS y Certbot.
- Preparar pruebas y documentación.

## Seguridad

- La llave `.pem` no está incluida en GitHub.
- El archivo `.env` no está incluido en GitHub.
- Las credenciales no están incorporadas directamente en el código.
- PostgreSQL no está expuesto públicamente en EC2.
- RabbitMQ utiliza TLS.
- El acceso público utiliza HTTPS.
- Los certificados y llaves privadas permanecen en EC2.