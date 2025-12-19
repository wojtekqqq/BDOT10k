#!/bin/bash

# ======================
# KONFIGURACJA
# ======================
DB_NAME="gis_db"
DB_USER="gis_user"
DB_PASS="StrongPassword123!"
DB_ENCODING="UTF8"
DB_LOCALE="C.UTF-8"

# ======================
# UPRAWNIENIA
# ======================
if [[ $EUID -ne 0 ]]; then
  echo "❌ Uruchom jako root (sudo)"
  exit 1
fi

# ======================
# UŻYTKOWNIK
# ======================
echo "➡️ Sprawdzanie użytkownika PostgreSQL..."

sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1
if [ $? -ne 0 ]; then
  echo "➡️ Tworzę użytkownika ${DB_USER}"
  sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
else
  echo "ℹ️ Użytkownik ${DB_USER} już istnieje"
fi

# ======================
# BAZA DANYCH (BEZ DO / FUNKCJI!)
# ======================
echo "➡️ Sprawdzanie bazy danych..."

sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1
if [ $? -ne 0 ]; then
  echo "➡️ Tworzę bazę ${DB_NAME}"
  sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} \
    OWNER ${DB_USER} \
    ENCODING '${DB_ENCODING}' \
    LC_COLLATE '${DB_LOCALE}' \
    LC_CTYPE '${DB_LOCALE}' \
    TEMPLATE template0;"
else
  echo "ℹ️ Baza ${DB_NAME} już istnieje"
fi

# ======================
# POSTGIS
# ======================
echo "➡️ Instalacja PostGIS..."

sudo -u postgres psql -d "${DB_NAME}" -c "CREATE EXTENSION IF NOT EXISTS postgis;"
sudo -u postgres psql -d "${DB_NAME}" -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;"

# ======================
# UPRAWNIENIA
# ======================
echo "➡️ Nadanie uprawnień..."

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

echo "✅ Gotowe!"
