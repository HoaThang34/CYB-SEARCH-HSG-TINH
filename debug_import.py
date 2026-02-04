
import os
import sys
from app import import_csv, SessionLocal, Candidate, engine

# Force recreate
# from app import Base
# Base.metadata.drop_all(bind=engine)

print("Running manual import debug...")
file_path = "diemthihsgtinh.csv"
if os.path.exists(file_path):
    import_csv(file_path)
else:
    print(f"File not found: {file_path}")

db = SessionLocal()
count = db.query(Candidate).count()
print(f"Total candidates in DB: {count}")

if count > 0:
    first = db.query(Candidate).first()
    print(f"First candidate: {first.name} - {first.sbd} - {first.birth_year}")
else:
    print("DB is empty.")
db.close()
