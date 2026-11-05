import psycopg2
from backend.app.config.settings import settings

conn = psycopg2.connect(settings.DATABASE_URL)
cur = conn.cursor()

suspicious_terms = [
    '%institute%', '%school%', '%college%', '%campus%', '%academy%',
    '%hospital%', '%clinic%', '%health post%', '%pharmacy%',
    '%bank%', '%atm%', '%cooperative%', '%finance%',
    '%police%', '%ward office%', '%municipality%', '%post office%',
    '%hardware%', '%furniture%', '%tailor%', '%workshop%', '%garage%',
    '%auto service%', '%petrol%', '%diesel%', '%dry cleaners%',
    '%beauty parlour%', '%salon%', '%cyber%', '%printing%', '%stationery%'
]

query = "SELECT id, name, category FROM places WHERE " + " OR ".join(["LOWER(name) LIKE %s" for _ in suspicious_terms])
cur.execute(query, suspicious_terms)
rows = cur.fetchall()
print(f"Total suspicious non-tourist entities found: {len(rows)}")
for r in rows[:25]:
    print(r)

if len(rows) > 0:
    delete_query = "DELETE FROM places WHERE " + " OR ".join(["LOWER(name) LIKE %s" for _ in suspicious_terms])
    cur.execute(delete_query, suspicious_terms)
    conn.commit()
    print(f"Deleted {cur.rowcount} non-tourist junk records successfully.")

cur.execute("SELECT COUNT(*) FROM places;")
remaining = cur.fetchone()[0]
print(f"Remaining pristine places: {remaining}")

conn.close()
