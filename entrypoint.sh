#!/bin/sh
set -e

export FLASK_APP=${FLASK_APP:-app.py}

# crea tablas + admin + post ejemplo si no existen
flask initdb || true

# llena con contenido random si hay pocos posts
flask seed || true

exec "$@"
