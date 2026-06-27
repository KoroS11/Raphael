import sqlite3, json
conn = sqlite3.connect('data/raphael.db')

print('=== WIND SPEED ===')
for r in conn.execute("SELECT station_name, value, observed_at FROM raw_observations WHERE layer_type='weather' AND station_name LIKE '%wind_speed%' LIMIT 5").fetchall():
    print(r)

print('\n=== WIND DIRECTION ===')
for r in conn.execute("SELECT station_name, value, observed_at FROM raw_observations WHERE layer_type='weather' AND station_name LIKE '%wind_direction%' LIMIT 3").fetchall():
    print(r)

print('\n=== PLUME OUTPUT SAMPLE ===')
for r in conn.execute("SELECT zone_id, value, explanation FROM ml_outputs WHERE model_type='gaussian_plume' LIMIT 2").fetchall():
    print(r[:2], json.loads(r[2]))

print('\n=== STATION COORDS ===')
for r in conn.execute("""SELECT DISTINCT station_name, 
    json_extract(raw_payload, '$.coordinates.latitude'),
    json_extract(raw_payload, '$.coordinates.longitude')
    FROM raw_observations WHERE layer_type='aq' 
    AND json_extract(raw_payload, '$.coordinates.latitude') IS NOT NULL
    GROUP BY station_name""").fetchall():
    print(r)

conn.close()
