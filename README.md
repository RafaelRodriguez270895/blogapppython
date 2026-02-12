
# Blog Demo (Vintage) — Flask + SQLAlchemy + Docker

Demo de un blog “old-school” (estilo ~2014–2016): server-rendered con Flask, SQLite, templates, RSS, panel admin clásico y funciones típicas de esa época.

Incluye:
- Posts con **tags** (many-to-many)
- **Búsqueda** simple tipo vintage (SQL `LIKE`) con paginación
- **Archivo por fechas**: `/archive/<year>/<month>`
- **RSS feed**: `/feed.xml`
- Panel **Admin** con:
  - Draft / Published
  - **Scheduled publish** (posts con `publish_at` futuro no aparecen en público)
  - **Soft delete** (no borra físico, marca como eliminado)
  - **Moderación de comentarios** (aprobar/rechazar/eliminar)
- “Vintage libs”: **Flask-Login** + **Flask-WTF** (CSRF)

---

## Requisitos

- Docker + Docker Compose

---

## Ejecutar con Docker

En la raíz del proyecto:

```bash
docker compose up --build
````

App disponible en:

* Blog: [http://localhost:8000/](http://localhost:8000/)
* Login: [http://localhost:8000/login](http://localhost:8000/login)
* Admin: [http://localhost:8000/admin](http://localhost:8000/admin)
* Moderación: [http://localhost:8000/admin/comments](http://localhost:8000/admin/comments)
* RSS: [http://localhost:8000/feed.xml](http://localhost:8000/feed.xml)

---

## Credenciales por defecto

El contenedor crea un usuario admin si no existe:

* Usuario: `admin`
* Password: tomado de la variable `ADMIN_PASSWORD` (por defecto: `admin123`)

Se configuran en `docker-compose.yml`:

```yaml
environment:
  ADMIN_PASSWORD: "admin123"
```

---

## Persistencia de la base de datos

Se usa SQLite en `/data/blog.db` y se persiste con un volumen:

* Dentro del contenedor: `/data/blog.db`
* Docker volume: `blogdata`

Si borras el volumen, se reinicia la data.

---

## Inicialización automática (entrypoint)

El contenedor ejecuta al arrancar:

* `flask initdb` → crea tablas + usuario admin (si no existe)
* `flask seed` → llena contenido de ejemplo (si la DB está vacía)

Archivo: `entrypoint.sh`

---

## Rutas principales

### Públicas

* `/` → Home con paginación
* `/p/<slug>` → Post + comentarios
* `/tag/<name>` → Posts por tag
* `/search?q=...` → búsqueda por título o contenido
* `/archive/<year>/<month>` → archivo mensual
* `/feed.xml` → RSS

### Admin (requiere login)

* `/admin` → lista de posts
* `/admin/new` → crear post
* `/admin/edit/<id>` → editar post
* `/admin/delete/<id>` → soft delete (POST)
* `/admin/comments` → moderación de comentarios

---

## CSRF (explicación rápida)

La app usa Flask-WTF, así que los formularios POST incluyen token CSRF:

* Formularios WTForms: `{{ form.csrf_token }}`
* Formularios manuales: `{{ csrf_token() }}`

Si intentas enviar un POST sin token (ej. desde una web externa o curl), Flask-WTF lo rechaza con 400.

---

## Notas “vintage”

Esta app intentionally mantiene patrones clásicos:

* Renderizado server-side con Jinja2
* Búsqueda simple con `LIKE` (no full-text)
* Admin manual (sin SPA)
* SQLite para demo local

---

## Estructura del proyecto

```
.
├─ app.py
├─ forms.py
├─ requirements.txt
├─ Dockerfile
├─ docker-compose.yml
├─ entrypoint.sh
└─ templates/
   ├─ base.html
   ├─ index.html
   ├─ post.html
   ├─ tag.html
   ├─ search.html
   ├─ archive.html
   ├─ login.html
   ├─ admin_posts.html
   ├─ admin_edit.html
   ├─ admin_comments.html
   └─ error.html
```

---

## Troubleshooting

### Error: `sqlite3.OperationalError: no such table: ...`

Asegúrate de:

1. estar usando el `entrypoint.sh`
2. que el volumen `/data` exista
3. que el contenedor tenga permisos para crear `/data/blog.db`

Rebuild:

```bash
docker compose down
docker compose up --build
```

Si quieres reiniciar la data:

```bash
docker compose down -v
docker compose up --build
```

---

## Licencia

Demo educativa / académica.


