# Uso de IA: balanceo de carga con Nginx

## Herramienta utilizada

ChatGPT, modelo de OpenAI.

## Prompt

Tengo EnergyShark desplegado en una instancia AWS EC2. La API FastAPI funciona dentro de un contenedor `master`, PostgreSQL y connector se ejecutan mediante Docker Compose, y Nginx está instalado directamente en EC2.

Ya implementé HTTPS como parte variable, pero quiero implementar también el balanceo de carga opcional.

Necesito:

1. Ejecutar dos instancias independientes de master.
2. Permitir que Nginx alcance individualmente ambas instancias.
3. Mantener ambas conectadas al mismo PostgreSQL.
4. Distribuir las solicitudes entre las dos instancias.
5. Identificar qué instancia responde.
6. Mantener HTTPS y las líneas administradas por Certbot.
7. Comprobar que la API continúe funcionando si una instancia se detiene.
8. Implementar los cambios sin perder los eventos almacenados.

## Respuesta y apoyo recibido

La IA propuso mantener el servicio original `master` y agregar una segunda instancia llamada `master_replica`.

La arquitectura resultante fue:

```text
                      → master-1 → 127.0.0.1:8000
Usuario → Nginx
                      → master-2 → 127.0.0.1:8001
                                      ↓
                                 PostgreSQL
```

Ambas instancias utilizan la misma imagen, el mismo código FastAPI y la misma base de datos PostgreSQL.

## Cambios en Docker Compose

La IA propuso:

- Mantener `master` en el puerto local 8000.
- Agregar `master_replica` en el puerto local 8001.
- Limitar ambos puertos a `127.0.0.1`.
- Utilizar el mismo `master/Dockerfile`.
- Conectar ambas instancias al servicio `database`.
- Mantener healthchecks independientes.
- Iniciar la réplica después de que `master` esté saludable.

La configuración utiliza:

```text
127.0.0.1:8000:8000
127.0.0.1:8001:8000
```

Los puertos no quedan expuestos directamente a internet. Nginx, instalado en el host EC2, puede alcanzarlos mediante la interfaz local.

## Identificación de instancias

La IA propuso incorporar la variable:

```text
INSTANCE_NAME
```

Los valores configurados fueron:

```text
master-1
master-2
```

El endpoint `/health` fue actualizado para incluir:

```json
{
  "status": "healthy",
  "database": "connected",
  "instance": "master-1"
}
```

Esto permite comprobar qué contenedor respondió.

## Configuración de Nginx

Se agregó el grupo:

```nginx
upstream energyshark_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
}
```

El proxy fue actualizado a:

```nginx
proxy_pass http://energyshark_backend;
```

También se configuró:

```nginx
proxy_next_upstream error timeout http_502 http_503 http_504;
```

Esto permite intentar el siguiente backend cuando una instancia no responde.

Para identificar el servidor utilizado, se agregó:

```nginx
add_header X-EnergyShark-Backend $upstream_addr always;
```

Se conservaron las rutas de certificados, las reglas de redirección y los comentarios administrados por Certbot.

