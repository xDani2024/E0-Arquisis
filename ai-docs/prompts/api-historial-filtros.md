# Uso de IA: API, historial, paginación y filtros

## Herramienta utilizada

ChatGPT, modelo de OpenAI.

## Prompt

Estoy desarrollando la API de EnergyShark utilizando FastAPI, SQLAlchemy y PostgreSQL.

Los eventos recibidos tienen un `idpk` UUID único, un tipo `demand-set` y un `packageBody` que contiene demandas por ciudad, `validUntil`, `metaContent` y `constraints`.

Necesito implementar filtros para todas las propiedades del evento, incluidos campos anidados dentro del JSON almacenado en PostgreSQL y respuestas controladas para eventos duplicados y registros inexistentes.

La implementación debe utilizar sesiones de SQLAlchemy, mantener la paginación después de aplicar filtros y entregar respuestas JSON con los nombres establecidos en el enunciado.

## Respuesta IA

### Serialización

La IA propuso una función para convertir el modelo de base de datos al formato requerido por la API:

```python
def serialize_event(event: Event):
    return {
        "id": event.id,
        "idpk": event.idpk,
        "type": event.type,
        "packageBody": event.package_body,
        "receivedAt": event.received_at,
    }
```

Esta función mantiene los nombres solicitados por el enunciado, aunque las columnas internas de PostgreSQL utilicen nombres como `package_body` y `received_at`.

### Filtros implementados

La IA ayudó a incorporar filtros para:

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

Los filtros `id`, `idpk` y `type` utilizan columnas directas del modelo.

Los filtros `city`, `demand` y `unit` consultan los elementos de la lista `demands` almacenada dentro de `package_body`.

Los filtros `validUntil`, `metaContent` y `constraints` consultan propiedades del objeto JSONB almacenado en PostgreSQL.

### Filtros temporales

Para `receivedAt`, la IA propuso recibir una fecha y construir un rango entre el comienzo del día y el comienzo del día siguiente.

De esta forma, una consulta como:

```text
/history?receivedAt=2026-08-30
```

encuentra todos los eventos recibidos durante ese día, aunque `receivedAt` también contenga hora, minutos, segundos y zona horaria.

Para `validUntil` se aplicó el filtro sobre la fecha ISO 8601 almacenada dentro de `packageBody`.

FastAPI valida automáticamente las fechas incorrectas y responde con código `422`.

### Validación de constraints

El parámetro `constraints` llega como texto dentro de la URL.

La IA propuso:

1. Intentar convertir el texto mediante `json.loads`.
2. Responder con código `422` si no es JSON válido.
3. Comprobar que el valor convertido sea un objeto.
4. Compararlo con el valor almacenado dentro de `packageBody`.

Ejemplo válido:

```bash
curl -G "http://127.0.0.1:8000/history" \
  --data-urlencode 'constraints={}'
```

Ejemplo inválido:

```bash
curl -G "http://127.0.0.1:8000/history" \
  --data-urlencode 'constraints=no-es-json'
```

La entrada incorrecta responde:

```json
{
  "detail": "constraints must be valid JSON"
}
```