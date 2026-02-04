
import os
import shutil
import csv
from typing import List, Optional

from fastapi import FastAPI, Depends, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from sqlalchemy import create_engine, Column, Integer, String, Float, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ---------------------------------------------------------
# 1. DATABASE SETUP
# ---------------------------------------------------------
SQLALCHEMY_DATABASE_URL = "sqlite:///./hsgtinh.db"
# Vercel Read-Only Filesystem Fix
if os.environ.get("VERCEL"):
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# 2. MODELS
# ---------------------------------------------------------
class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    sbd = Column(String, unique=True, index=True)  # Số báo danh
    name = Column(String, nullable=True)          # Họ và tên
    birth_year = Column(String, nullable=True)    # Năm sinh (NEW)
    province = Column(String, index=True, default="Lào Cai") # Mặc định Lào Cai
    school = Column(String, index=True)           # Đơn vị (Trường)
    subject = Column(String, index=True)          # Môn thi
    
    # Detail Scores
    score_listening = Column(Float, nullable=True)
    score_speaking = Column(Float, nullable=True)
    score_reading = Column(Float, nullable=True)
    score_writing = Column(Float, nullable=True)
    
    total_score = Column(Float, index=True)       # Tổng điểm
    prize = Column(String, nullable=True)         # Giải
    class_grade = Column(String, nullable=True)   # Lớp

# ---------------------------------------------------------
# 3. HELPER LOGIC (Ranking, Stats)
# ---------------------------------------------------------
PRIZE_ORDER = {
    "Nhất": 4, "Nhì": 3, "Ba": 2, "K.Khích": 1, 
    "Không giải": 0, "Không có giải": 0, "nan": 0, "": 0, None: 0
}

def get_prize_value(prize_str):
    if not prize_str: return 0
    return PRIZE_ORDER.get(prize_str.strip(), 0)

def get_ranking(db: Session, subject: str = None, province: str = None, school: str = None, 
                prize: str = None, page: int = 1, limit: int = 50):
    """
    Get ranked candidates with pagination support.
    
    Args:
        db: Database session
        subject: Filter by subject
        province: Filter by province
        school: Filter by school
        prize: Filter by prize (Nhất, Nhì, Ba, K.Khích)
        page: Page number (1-indexed)
        limit: Items per page (default 50)
    
    Returns:
        dict: {
            "data": List of ranked candidates for current page,
            "total": Total number of results,
            "page": Current page number,
            "limit": Items per page,
            "total_pages": Total number of pages
        }
    """
    query = db.query(Candidate)
    if subject:
        query = query.filter(Candidate.subject == subject)
    
    candidates = query.all()
    
    # Group by subject
    candidates_by_subject = {}
    for c in candidates:
        if c.subject not in candidates_by_subject:
            candidates_by_subject[c.subject] = []
        candidates_by_subject[c.subject].append(c)
        
    results_with_rank = []
    
    for subj, sub_candidates in candidates_by_subject.items():
        # Sort - Robustly handle types
        def sort_key(c):
            # Handle total_score
            score = -1.0
            if c.total_score is not None:
                try:
                    score = float(c.total_score)
                except (ValueError, TypeError):
                    score = -1.0
            
            # Handle prize
            prize_val = get_prize_value(c.prize)
            
            return (score, prize_val)

        sub_candidates.sort(key=sort_key, reverse=True)
        
        current_rank = 1
        for i, candidate in enumerate(sub_candidates):
            if i > 0:
                prev = sub_candidates[i-1]
                # Compare precisely
                curr_score = sort_key(candidate)[0]
                prev_score = sort_key(prev)[0]
                curr_prize = sort_key(candidate)[1]
                prev_prize = sort_key(prev)[1]
                
                if (curr_score == prev_score and curr_prize == prev_prize):
                    pass 
                else:
                    current_rank = i + 1
            
            # Filters
            if province and candidate.province != province:
                continue
            if school and candidate.school != school:
                continue
            if prize and candidate.prize != prize:
                continue
                
            results_with_rank.append({
                "rank": current_rank,
                "data": candidate
            })
            
    results_with_rank.sort(key=lambda x: x["rank"])
    
    # Pagination
    total = len(results_with_rank)
    total_pages = (total + limit - 1) // limit  # Ceiling division
    
    # Validate page number
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # Calculate offset
    offset = (page - 1) * limit
    paginated_data = results_with_rank[offset:offset + limit]
    
    return {
        "data": paginated_data,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }

def get_statistics(db: Session, subject: str = None, province: str = None):
    query = db.query(Candidate)
    if subject:
        query = query.filter(Candidate.subject == subject)
    if province:
        query = query.filter(Candidate.province == province)
        
    candidates = query.all()
    total_candidates = len(candidates)
    
    prizes = {"Nhất": 0, "Nhì": 0, "Ba": 0, "K.Khích": 0}
    total_prizes = 0
    
    for c in candidates:
        if c.prize in prizes:
            prizes[c.prize] += 1
            total_prizes += 1
            
    prize_ratio = 0
    if total_candidates > 0:
        prize_ratio = round((total_prizes / total_candidates) * 100, 2)
        
    # Cutoff scores (National)
    cutoff_scores = {}
    if subject:
        national_query = db.query(Candidate).filter(Candidate.subject == subject).all()
        min_scores = {}
        for c in national_query:
            if c.prize in prizes and c.total_score is not None:
                if c.prize not in min_scores:
                    min_scores[c.prize] = c.total_score
                else:
                    min_scores[c.prize] = min(min_scores[c.prize], c.total_score)
        cutoff_scores = min_scores

    # Province Stats
    province_stats = {}
    for c in candidates:
        if c.prize in prizes:
            p_name = c.province if c.province else "Unknown"
            if p_name not in province_stats:
                province_stats[p_name] = {"total": 0, "Nhất": 0, "Nhì": 0, "Ba": 0, "K.Khích": 0}
            province_stats[p_name][c.prize] += 1
            province_stats[p_name]["total"] += 1
            
    all_provinces_list = []
    for name, stats in province_stats.items():
        all_provinces_list.append({
            "name": name,
            "count": stats["total"],
            "details": stats
        })
        
    all_provinces_list.sort(key=lambda s: (
        s["count"], 
        s["details"]["Nhất"], 
        s["details"]["Nhì"], 
        s["details"]["Ba"]
    ), reverse=True)

    # School Stats
    school_stats = {}
    for c in candidates:
        if c.prize in prizes:
            s_name = c.school if c.school else "Unknown"
            if s_name not in school_stats:
                school_stats[s_name] = {"total": 0, "Nhất": 0, "Nhì": 0, "Ba": 0, "K.Khích": 0}
            school_stats[s_name][c.prize] += 1
            school_stats[s_name]["total"] += 1
            
    all_schools_list = []
    for name, stats in school_stats.items():
        all_schools_list.append({
            "name": name,
            "count": stats["total"],
            "details": stats
        })
        
    all_schools_list.sort(key=lambda s: (
        s["count"], 
        s["details"]["Nhất"], 
        s["details"]["Nhì"], 
        s["details"]["Ba"]
    ), reverse=True)
    
    return {
        "total_candidates": total_candidates,
        "total_prizes": total_prizes,
        "prize_ratio": prize_ratio,
        "prizes": prizes,
        "cutoff_scores": cutoff_scores,
        "top_schools": all_schools_list[:5],
        "all_schools": all_schools_list,
        "all_provinces": all_provinces_list
    }

# ---------------------------------------------------------
# 4. IMPORT LOGIC
# ---------------------------------------------------------
def import_csv(file_path: str):
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    
    try:
        # FULL RESET for consistency
        session.query(Candidate).delete()
        print(f"Importing from {file_path}...")
        
        candidates = []
        
        with open(file_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            try:
                headers = next(reader)
            except StopIteration:
                return # Empty file
            
            headers = [h.strip().lower() for h in headers]
            
            def get_idx(possible_names):
                for name in possible_names:
                    if name in headers:
                        return headers.index(name)
                return -1
            
            idx_sbd = get_idx(['sbd'])
            idx_name = get_idx(['tenthisinh', 'name', 'họ và tên'])
            idx_birth = get_idx(['namsinh', 'birth_year', 'ngày sinh'])
            idx_school = get_idx(['truong', 'trường', 'trường thpt'])
            idx_subject = get_idx(['mon', 'môn'])
            idx_score = get_idx(['diem', 'điểm'])
            idx_prize = get_idx(['giai', 'giải'])
            
            for row in reader:
                def get_val(idx):
                    if idx != -1 and idx < len(row):
                        val = row[idx].strip()
                        if val and val.lower() != 'nan':
                            return val
                    return None
                
                def get_float(idx):
                    val = get_val(idx)
                    if val:
                        try:
                            return float(val.replace(',', '.'))
                        except:
                            return None
                    return None

                sbd_val = get_val(idx_sbd)
                if not sbd_val:
                    continue
                    
                cand = Candidate(
                    sbd=sbd_val,
                    name=get_val(idx_name),
                    birth_year=get_val(idx_birth),
                    province="Lào Cai", # Default for provincial exam
                    school=get_val(idx_school),
                    subject=get_val(idx_subject),
                    class_grade=None,
                    score_listening=None,
                    score_speaking=None,
                    score_reading=None,
                    score_writing=None,
                    total_score=get_float(idx_score),
                    prize=get_val(idx_prize)
                )
                candidates.append(cand)
            
            # Deduplicate by SBD (keep last or first? First seems safer for ordered CSV)
            unique_candidates = {}
            for c in candidates:
                if c.sbd not in unique_candidates:
                    unique_candidates[c.sbd] = c
            
            candidates = list(unique_candidates.values())
            
        session.add_all(candidates)
        session.commit()
        print(f"Imported {len(candidates)} records successfully.")
        
    except Exception as e:
        session.rollback()
        print(f"Import error: {e}")
    finally:
        session.close()

def ensure_data_loaded():
    """Check if DB is empty and try to load CSV if found."""
    db = SessionLocal()
    try:
        # Check if we have any candidates
        try:
             # Look for at least one record
            if db.query(Candidate).first():
                return
        except:
             # Table might not exist yet
            pass

        # If we are here, we need to load data
        csv_name = "diemthihsgtinh.csv"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        possible_paths = [
            os.path.join(current_dir, csv_name), # Absolute path
            csv_name, # Relative path
            f"/var/task/{csv_name}" # Vercel typical path
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Found dataset at: {path}")
                import_csv(path)
                break
        else:
            print("Warning: Dataset CSV not found in any expected location.")
            
    except Exception as e:
        print(f"Error checking data consistency: {e}")
    finally:
        db.close()


# ---------------------------------------------------------
# 5. WEBSOCKET MANAGER
# ---------------------------------------------------------
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        await self.broadcast_count()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_count(self):
        count = len(self.active_connections)
        # Broadcast roughly periodically or on change
        # For simplicity, we broadcast to all on every connect/disconnect
        # but catching errors cleanly
        for connection in self.active_connections:
            try:
                await connection.send_json({"online": count})
            except:
                pass

manager = ConnectionManager()

# ---------------------------------------------------------
# 6. FASTAPI APP
# ---------------------------------------------------------
app = FastAPI(title="HSGQG System")

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

@app.websocket("/ws/active")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Just keep connection open. Client doesn't need to send anything.
            # But we read to handle disconnects cleanly.
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast_count()
    except Exception:
        manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)
    ensure_data_loaded()

@app.get("/")
async def read_home():
    return FileResponse(os.path.join('static', 'home.html'))

@app.get("/ranking")
async def read_ranking_page():
    return FileResponse(os.path.join('static', 'ranking.html'))

@app.get("/search")
async def read_search_page():
    return FileResponse(os.path.join('static', 'search.html'))

@app.get("/stats")
async def read_stats_page():
    return FileResponse(os.path.join('static', 'stats.html'))

# API
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_location = f"uploaded_{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    
    import_csv(file_location)
    return {"info": f"File '{file.filename}' imported successfully"}

@app.get("/api/ranking")
def api_ranking(subject: str = None, province: str = None, school: str = None, 
                prize: str = None, page: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    try:
        ensure_data_loaded() # Move inside try block to catch init errors
        
        # Sanitize inputs
        if subject: subject = subject.strip() 
        if province: province = province.strip()
        if school: school = school.strip()
        if prize: prize = prize.strip()
        
        return get_ranking(db, subject, province, school, prize, page, limit)
    except Exception as e:
        print(f"ERROR in api_ranking: {e}")
        import traceback
        traceback.print_exc()
        # Return empty safe response with error detail
        return {
            "data": [],
            "total": 0,
            "page": 1,
            "limit": limit,
            "total_pages": 0,
            "error": str(e)
        }

@app.get("/api/stats")
def api_stats(subject: str = None, province: str = None, db: Session = Depends(get_db)):
    ensure_data_loaded()
    return get_statistics(db, subject, province)

@app.get("/api/search")
def api_search(q: str, page: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    ensure_data_loaded()
    
    # Query all matching candidates
    all_results = db.query(Candidate).filter(Candidate.sbd.contains(q)).all()
    
    # Also search by Name
    name_results = db.query(Candidate).filter(Candidate.name.contains(q)).all()
    
    # Merge results unique
    seen_ids = set()
    merged_results = []
    
    for r in all_results + name_results:
        if r.id not in seen_ids:
            merged_results.append(r)
            seen_ids.add(r.id)
    
    # Pagination
    total = len(merged_results)
    total_pages = (total + limit - 1) // limit
    
    # Validate page
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # Slice results
    offset = (page - 1) * limit
    paginated_results = merged_results[offset:offset + limit]
    
    return {
        "data": paginated_results,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }

@app.get("/api/subjects")
def get_subjects(db: Session = Depends(get_db)):
    ensure_data_loaded()
    return [r[0] for r in db.query(Candidate.subject).distinct().order_by(Candidate.subject).all() if r[0]]

@app.get("/api/provinces")
def get_provinces(db: Session = Depends(get_db)):
    ensure_data_loaded()
    return [r[0] for r in db.query(Candidate.province).distinct().order_by(Candidate.province).all() if r[0]]

@app.get("/api/schools")
def get_schools(province: str = None, db: Session = Depends(get_db)):
    ensure_data_loaded()
    query = db.query(Candidate.school).distinct().order_by(Candidate.school)
    if province:
        query = query.filter(Candidate.province == province)
    return [r[0] for r in query.all() if r[0]]

if __name__ == "__main__":
    import uvicorn
    # Clean up common garbage before running
    if os.path.exists("__pycache__"):
        shutil.rmtree("__pycache__", ignore_errors=True)
        
    print("Starting server on http://localhost:3434")
    uvicorn.run("app:app", host="0.0.0.0", port=3434, reload=True)
