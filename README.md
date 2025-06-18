# Fast LastMile API

A FastAPI service for processing lastmile routing requests using OpenRouteService (ORS) and NetworkX for path optimization with fiber optic infrastructure overlay.

## Features

- **CSV File Upload**: Upload CSV files containing lastmile routing requests
- **Column Mapping**: Flexible column mapping for different CSV formats
- **API Key Authentication**: Secure API access with Bearer token authentication
- **Multiple Output Formats**: Results in Parquet, GeoPackage, and CSV formats
- **Health Checks**: Built-in health monitoring for the API and dependencies
- **Docker Support**: Containerized deployment with Docker Compose

## Project Structure

```
fast-last-mile/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management
│   ├── auth.py              # API key authentication
│   ├── models.py            # Pydantic models
│   ├── utils.py             # Utility functions
│   ├── core/
│   │   ├── __init__.py
│   │   └── lastmile_processor.py  # Core processing logic
│   └── routers/
│       ├── __init__.py
│       └── lastmile.py      # API endpoints
├── data/                    # Data files (graphs, fiber optic data)
├── uploads/                 # Temporary upload storage
├── outputs/                 # Processing results
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker container configuration
├── docker-compose.yml      # Docker Compose configuration
├── env.example             # Environment variables template
└── README.md               # Project documentation
```

## Installation

### Prerequisites

- Python 3.11+
- OpenRouteService (ORS) server running on localhost:6080
- Required data files:
  - Graph file (GraphML format)
  - Fiber optic shapefile
  - Population CSV file

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fast-last-mile
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env file with your configuration
   ```

5. **Run the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Docker Deployment

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

2. **Or run individual commands**
   ```bash
   # Build the image
   docker build -t fast-lastmile-api .

   # Run the container
   docker run -p 8000:8000 \
     -e API_KEY=your-secret-key \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/outputs:/app/outputs \
     fast-lastmile-api
   ```

## Configuration

### Environment Variables

Copy `env.example` to `.env` and configure:

```env
# API Configuration
API_KEY=your-super-secret-api-key-here
API_TITLE=Fast LastMile API
API_VERSION=1.0.0
DEBUG=False

# Server Configuration
HOST=0.0.0.0
PORT=8000

# ORS Configuration
ORS_BASE_URL=http://localhost:6080

# File Storage
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
MAX_FILE_SIZE_MB=100

# Default Processing Parameters
DEFAULT_PULAU=Sulawesi
DEFAULT_GRAPH_PATH=./data/sulawesi_graph.graphml
DEFAULT_FO_PATH=./data/fo_sulawesi/fo_sulawesi.shp
DEFAULT_POP_PATH=./data/pop.csv
```

## API Usage

### Authentication

All API endpoints require authentication using Bearer token:

```bash
curl -H "Authorization: Bearer your-api-key" \
     http://localhost:8000/api/v1/lastmile/health
```

### Endpoints

#### 1. Health Check
```bash
GET /api/v1/lastmile/health
```

#### 2. Upload CSV Preview
```bash
POST /api/v1/lastmile/upload-csv
Content-Type: multipart/form-data

# Upload CSV file to preview columns and data
curl -X POST \
  -H "Authorization: Bearer your-api-key" \
  -F "file=@lastmile_requests.csv" \
  http://localhost:8000/api/v1/lastmile/upload-csv
```

#### 3. Process LastMile Requests
```bash
POST /api/v1/lastmile/process
Content-Type: multipart/form-data

curl -X POST \
  -H "Authorization: Bearer your-api-key" \
  -F "file=@lastmile_requests.csv" \
  -F "lat_fe_column=Lat_FE" \
  -F "lon_fe_column=Lon_FE" \
  -F "lat_ne_column=Lat_NE" \
  -F "lon_ne_column=Lon_NE" \
  -F "fe_name_column=Far End (FE)" \
  -F "ne_name_column=Near End (NE)" \
  -F "output_folder=my_output" \
  -F "pulau=Sulawesi" \
  http://localhost:8000/api/v1/lastmile/process
```

### CSV Format Requirements

Your CSV file should contain the following columns (names can be customized):

| Column | Description | Example |
|--------|-------------|---------|
| Far End Name | Identifier for Far End | "FE_001" |
| Near End Name | Identifier for Near End | "NE_001" |
| FE Latitude | Far End latitude | -5.1477 |
| FE Longitude | Far End longitude | 119.4327 |
| NE Latitude | Near End latitude | -5.1520 |
| NE Longitude | Near End longitude | 119.4380 |

### Response Format

Successful processing returns:

```json
{
  "request_id": "uuid-string",
  "status": "completed",
  "message": "Processing completed successfully",
  "output_files": [
    "/path/to/output/file1.parquet",
    "/path/to/output/file2.gpkg",
    "/path/to/output/analysis.json"
  ],
  "analysis_summary": {
    "total_requests": 10,
    "processed_requests": 10,
    "total_distance_m": 15000.0,
    "overlapped_distance_m": 8000.0,
    "new_build_distance_m": 7000.0
  }
}
```

## Data Requirements

### 1. Graph File (GraphML)
- NetworkX-compatible graph file
- Contains road network with geometry data
- Example: `sulawesi_graph.graphml`

### 2. Fiber Optic Shapefile
- Shapefile containing existing fiber optic infrastructure
- Must include geometry and NAME column
- Example: `fo_sulawesi/fo_sulawesi.shp`

### 3. Population CSV
- CSV file with population data points
- Must contain longitude and latitude columns
- Example: `pop.csv`

## Output Files

The API generates several output files:

1. **Main Result** (`.parquet`): Geospatial data with routing results
2. **GeoPackage** (`.gpkg`): Same data in GeoPackage format
3. **Summary CSV** (`.csv`): Summary data without geometry
4. **Analysis JSON** (`.json`): Detailed analysis and statistics

## Monitoring

### Health Checks

- **API Health**: `GET /health`
- **LastMile Health**: `GET /api/v1/lastmile/health`
- **Docker Health**: Built-in Docker health checks

### Logs

Application logs are written to:
- Console (development)
- `/app/logs/` (Docker container)

## Development

### Adding New Features

1. **Models**: Add Pydantic models in `app/models.py`
2. **Routes**: Add new endpoints in `app/routers/`
3. **Business Logic**: Add processing logic in `app/core/`
4. **Utilities**: Add helper functions in `app/utils.py`

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

## Troubleshooting

### Common Issues

1. **ORS Connection Failed**
   - Ensure ORS server is running on specified URL
   - Check firewall settings
   - Verify ORS_BASE_URL configuration

2. **File Upload Errors**
   - Check file size limits (MAX_FILE_SIZE_MB)
   - Ensure CSV file is properly formatted
   - Verify required columns exist

3. **Processing Failures**
   - Check data file paths and existence
   - Verify CSV column mappings
   - Review application logs

### Performance Optimization

- Adjust file size limits based on server capacity
- Monitor memory usage during large file processing
- Consider implementing background processing for large datasets

## License

[Specify your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions:
- Check the troubleshooting section
- Review application logs
- Create an issue in the project repository