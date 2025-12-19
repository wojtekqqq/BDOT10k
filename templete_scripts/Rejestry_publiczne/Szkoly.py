import csv
import json
import psycopg2

# =====================
# PLIKI
# =====================
CSV_FILE = "/root/.local/share/QGIS/QGIS3/profiles/default/python/plugins/gml_application_schema_toolbox/dane/rspo_2025_12_17.csv"
JSON_FILE = "/root/.local/share/QGIS/QGIS3/profiles/default/python/plugins/gml_application_schema_toolbox/dane/rspo_drawski.json"

# =====================
# DB CONNECTION
# =====================
conn = psycopg2.connect(
    dbname="gis_db",
    user="gis_user",
    password="StrongPassword123!",
    host="qgis-postgis-1",
    port=5432
)
cur = conn.cursor()

# =====================
# 1️⃣ CREATE TABLE IF NOT EXISTS
# =====================
cur.execute("""
CREATE TABLE IF NOT EXISTS rspo_szkoly (
    numer_rspo TEXT PRIMARY KEY,
    nazwa TEXT,
    geom geometry(Point, 4326)
);
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS rspo_szkoly_geom_idx
ON rspo_szkoly
USING GIST (geom);
""")

conn.commit()

# =====================
# 2️⃣ LOAD JSON (RSPO → coords)
# =====================
with open(JSON_FILE, encoding="utf-8") as f:
    data = json.load(f)

geo = {}
for item in data["items"]:
    rspo = str(item.get("rspo"))
    hq = item.get("hqGeotag")
    if hq and hq.get("latitude") and hq.get("longitude"):
        geo[rspo] = (float(hq["longitude"]), float(hq["latitude"]))

# =====================
# 3️⃣ LOAD CSV + UPSERT
# =====================
inserted = 0
skipped = 0

with open(CSV_FILE, encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f, delimiter=";")
    reader.fieldnames = [h.strip() for h in reader.fieldnames]

    for row in reader:
        rspo = row.get("Numer RSPO")
        if not rspo:
            skipped += 1
            continue

        rspo = rspo.strip().strip('"')

        if rspo not in geo:
            skipped += 1
            continue

        lon, lat = geo[rspo]

        cur.execute(
            """
            INSERT INTO rspo_szkoly (
                numer_rspo,
                nazwa,
                geom
            )
            VALUES (
                %s,
                %s,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            )
            ON CONFLICT (numer_rspo) DO UPDATE
            SET
                nazwa = EXCLUDED.nazwa,
                geom = EXCLUDED.geom;
            """,
            (
                rspo,
                row.get("Nazwa"),
                lon,
                lat
            )
        )

        inserted += 1

conn.commit()

cur.close()
conn.close()

print(f"✔ Zapisano / zaktualizowano: {inserted}")
print(f"⚠ Pominięto: {skipped}")
