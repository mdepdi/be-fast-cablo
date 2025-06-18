# LastMile Processing Database Setup

Sistem database lengkap untuk menyimpan hasil processing lastmile dengan PostgreSQL, SQLAlchemy, Pydantic, dan Alembic migrations.

## 🚀 **Quick Start**

### 1. Install Dependencies
```bash
pip install -r requirements-database.txt
```

### 2. Setup Database
```bash
# Check database connection
python setup_database.py --check

# Initialize database (default)
python setup_database.py

# Run migrations (recommended)
python setup_database.py --migrate
```

### 3. Environment Variables
```bash
export DATABASE_URL="postgresql://postgres:adminbvt@localhost:5433/db-cablo"
```

## 📊 **Database Schema**

### **Table: `lastmile_processing_results`**
Tabel utama untuk menyimpan hasil processing lastmile:

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `request_id` | VARCHAR(255) | Unique request identifier |
| `input_filename` | VARCHAR(500) | Original input file |
| `total_requests` | INTEGER | Total requests processed |
| `processed_requests` | INTEGER | Successfully processed requests |
| `processing_status` | VARCHAR(50) | Status: pending, processing, completed, failed |
| `processing_started_at` | TIMESTAMP | Processing start time |
| `processing_completed_at` | TIMESTAMP | Processing completion time |
| `processing_duration_seconds` | INTEGER | Total processing duration |
| `pulau` | VARCHAR(100) | Island name |
| `ors_base_url` | VARCHAR(500) | ORS server URL |
| `graph_path` | VARCHAR(500) | Graph file path |
| **`result_analysis`** | **JSONB** | **Complete geodataframe as GeoJSON** |
| **`summary_analysis`** | **JSONB** | **Summary statistics and analysis** |
| `output_files` | JSONB | List of generated files |
| `error_message` | TEXT | Error message if failed |
| `error_details` | JSONB | Detailed error information |
| `created_at` | TIMESTAMP | Record creation time |
| `updated_at` | TIMESTAMP | Last update time (auto-updated) |
| `created_by` | VARCHAR(255) | User/system creator |
| `metadata_info` | JSONB | Additional metadata |

### **Table: `lastmile_request_details`**
Detail untuk setiap request individual:

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `processing_result_id` | UUID | Reference to main result |
| `request_sequence` | INTEGER | Sequence number |
| `fe_name`, `ne_name` | VARCHAR(255) | Far End & Near End names |
| `fe_latitude`, `fe_longitude` | VARCHAR(50) | Far End coordinates |
| `ne_latitude`, `ne_longitude` | VARCHAR(50) | Near End coordinates |
| `segment_count` | INTEGER | Number of segments |
| `total_distance_m` | INTEGER | Total distance in meters |
| `overlapped_distance_m` | INTEGER | Overlapped distance |
| `new_build_distance_m` | INTEGER | New build distance |
| `overlapped_percentage` | INTEGER | Overlapped percentage |
| `new_build_percentage` | INTEGER | New build percentage |
| `processing_status` | VARCHAR(50) | Individual request status |
| `error_message` | TEXT | Error for this request |
| `request_geometry` | JSONB | GeoJSON geometry |
| `created_at`, `updated_at` | TIMESTAMP | Audit timestamps |

## 🔧 **Usage Examples**

### **Basic Database Operations**

```python
from sqlalchemy.orm import Session
from app.database.config import SessionLocal
from app.database.crud import processing_result_crud
from app.database.schemas import ProcessingStatus

# Create database session
db = SessionLocal()

# Get processing results
results = processing_result_crud.get_multi(db, limit=10)

# Get by status
completed = processing_result_crud.get_multi(
    db,
    query_params=ProcessingResultQuery(status=ProcessingStatus.COMPLETED)
)

# Get summary statistics
stats = processing_result_crud.get_summary_stats(db)

db.close()
```

### **Saving Processing Results**

```python
import geopandas as gpd
from app.database.utils import (
    create_processing_job,
    save_processing_results,
    geodataframe_to_geojson
)

# Create processing job
db = SessionLocal()
job = create_processing_job(
    db=db,
    request_id="REQ-2024001",
    input_filename="requests.csv",
    total_requests=100,
    pulau="Sulawesi",
    ors_base_url="http://localhost:6080",
    graph_path="./data/sulawesi_graph.graphml",
    created_by="system"
)

# After processing is complete
dissolved_gdf = your_geodataframe  # Your processed GeoDataFrame
analysis_summary = {
    "total_requests": 100,
    "total_distance_km": 145.6,
    "overlapped_percentage": 35,
    "new_build_percentage": 65,
    "processing_time_minutes": 12.5
}
output_files = ["output_dissolved.geojson", "output_summary.csv"]

# Save results
success = save_processing_results(
    db=db,
    processing_result_id=job.id,
    dissolved_gdf=dissolved_gdf,
    analysis_summary=analysis_summary,
    output_files=output_files
)

db.close()
```

### **Retrieving Results as GeoDataFrame**

```python
from app.database.utils import get_processing_result_geodataframe

db = SessionLocal()

# Get result as GeoDataFrame
gdf = get_processing_result_geodataframe(db, processing_result_id)

if gdf is not None:
    print(f"Retrieved {len(gdf)} features")
    print(f"Columns: {list(gdf.columns)}")
    print(f"CRS: {gdf.crs}")

db.close()
```

## 🛠 **Database Management Commands**

```bash
# Initialize database
python setup_database.py --init

# Run migrations
python setup_database.py --migrate

# Reset database (DANGER - deletes all data)
python setup_database.py --reset

# Check connection
python setup_database.py --check

# Show table information
python setup_database.py --info
```

## 🔄 **Alembic Migrations**

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Downgrade
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history --verbose
```

## 📈 **Performance Features**

### **Indexes**
- Primary keys: UUID with indexes
- Request ID: Indexed for fast lookups
- Status: Indexed for filtering
- Timestamps: Indexed for date range queries
- Geographic references: Indexed for spatial queries

### **JSONB Benefits**
- Efficient storage of GeoJSON data
- Fast queries on JSON attributes
- Support for GIN indexes for complex queries
- Native PostgreSQL JSON operators

### **Auto-Update Triggers**
- `updated_at` automatically updated on record changes
- Consistent audit trail

## 🔒 **Data Validation**

Pydantic schemas provide comprehensive validation:

```python
from app.database.schemas import (
    LastMileProcessingResultCreate,
    ProcessingJobRequest,
    GeoJSONFeatureCollection
)

# Automatic validation
job_request = ProcessingJobRequest(
    input_file_path="data/requests.csv",
    pulau="Sulawesi",
    created_by="user123"
)
```

## 🧪 **Testing Database Operations**

```python
# Example test script
def test_database_operations():
    db = SessionLocal()

    try:
        # Test create
        job = create_processing_job(
            db=db,
            request_id=f"TEST-{uuid.uuid4()}",
            input_filename="test.csv",
            total_requests=1,
            pulau="Test",
            ors_base_url="http://test",
            graph_path="./test.graphml"
        )

        print(f"✅ Created job: {job.id}")

        # Test retrieve
        retrieved = processing_result_crud.get(db, job.id)
        print(f"✅ Retrieved job: {retrieved.request_id}")

        # Test update status
        updated = processing_result_crud.update_status(
            db, job.id, ProcessingStatus.COMPLETED
        )
        print(f"✅ Updated status: {updated.processing_status}")

    finally:
        db.close()

if __name__ == "__main__":
    test_database_operations()
```

## 🚨 **Troubleshooting**

### **Connection Issues**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check database exists
psql -h localhost -p 5433 -U postgres -l

# Test connection
python setup_database.py --check
```

### **Migration Errors**
```bash
# Check current state
alembic current

# Check if migration is needed
alembic check

# Force revision (if needed)
alembic stamp head
```

### **Performance Issues**
```sql
-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY size_bytes DESC;

-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public';
```

## 📝 **Integration Example**

```python
# Complete integration example
class LastMileProcessor:
    def __init__(self):
        self.db = SessionLocal()

    def process_file(self, csv_file: str, pulau: str = "Sulawesi"):
        try:
            # Create processing job
            job = create_processing_job(
                db=self.db,
                request_id=f"PROC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                input_filename=csv_file,
                total_requests=self.count_requests(csv_file),
                pulau=pulau,
                ors_base_url="http://localhost:6080",
                graph_path=f"./data/{pulau.lower()}_graph.graphml"
            )

            # Update status to processing
            processing_result_crud.update_status(
                self.db, job.id, ProcessingStatus.PROCESSING
            )

            # Your processing logic here
            dissolved_gdf = self.run_lastmile_processing(csv_file)

            # Save results
            success = save_processing_results(
                db=self.db,
                processing_result_id=job.id,
                dissolved_gdf=dissolved_gdf,
                analysis_summary=self.generate_summary(dissolved_gdf),
                output_files=self.save_output_files(dissolved_gdf)
            )

            return job.id if success else None

        except Exception as e:
            mark_processing_failed(
                self.db, job.id, str(e), {"traceback": traceback.format_exc()}
            )
            raise

        finally:
            self.db.close()
```

## 🎯 **Best Practices**

1. **Always use database sessions properly**
   ```python
   db = SessionLocal()
   try:
       # Your operations
       pass
   finally:
       db.close()
   ```

2. **Use CRUD operations for consistent data handling**
3. **Validate data with Pydantic schemas**
4. **Monitor database performance with built-in stats**
5. **Regular backup of JSONB data**
6. **Use environment variables for configuration**

---

## ✨ **Ready to Use!**

Database Anda sudah siap untuk menyimpan hasil processing lastmile dengan:
- ✅ **JSONB columns** untuk `result_analysis` dan `summary_analysis`
- ✅ **Complete CRUD operations**
- ✅ **Pydantic validation**
- ✅ **Alembic migrations**
- ✅ **GeoDataFrame ↔ GeoJSON conversion utilities**
- ✅ **Performance optimizations**
- ✅ **Error handling & logging**