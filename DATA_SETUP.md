# Data Setup Guide

## Required Data Structure

Untuk menjalankan FastAPI LastMile dengan full processing, Anda memerlukan struktur folder berikut:

```
fast-last-mile/
├── data/
│   ├── sulawesi_graph.graphml     # NetworkX graph file (79MB)
│   ├── pop.csv                    # Population data (4.4KB)
│   └── fo_sulawesi/
│       ├── fo_sulawesi.shp        # Fiber Optic shapefile
│       ├── fo_sulawesi.cpg        # Shapefile encoding
│       └── fo_sulawesi.prj        # Shapefile projection
├── uploads/                       # Temporary CSV uploads
├── outputs/                       # Processing results
└── .env                          # Environment configuration
```

## Data Files Description

### 1. Graph File
- **File**: `data/sulawesi_graph.graphml`
- **Type**: NetworkX graph in GraphML format
- **Size**: ~79MB
- **Purpose**: Road network graph for NetworkX routing
- **Format**: XML-based GraphML with geometry data

### 2. Fiber Optic Shapefile
- **File**: `data/fo_sulawesi/fo_sulawesi.shp` (+ supporting files)
- **Type**: ESRI Shapefile
- **Purpose**: Existing fiber optic infrastructure for overlap analysis
- **Required columns**: `NAME`, `geometry`

### 3. Population Data
- **File**: `data/pop.csv`
- **Type**: CSV with coordinate data
- **Purpose**: Population points for analysis
- **Required columns**: `longitude`, `latitude`

## Default Configuration

Environment variables in `.env`:

```env
# Default data paths
DEFAULT_GRAPH_PATH=./data/sulawesi_graph.graphml
DEFAULT_FO_PATH=./data/fo_sulawesi/fo_sulawesi.shp
DEFAULT_POP_PATH=./data/pop.csv
```

## Data Copy Commands

Jika data ada di direktori `../input/`, copy dengan:

```bash
# Create data structure
mkdir -p data/fo_sulawesi

# Copy files
cp ../input/sulawesi_graph.graphml data/
cp ../input/pop.csv data/
cp -r ../input/fo_sulawesi/* data/fo_sulawesi/
```

## Verification

Test file keberadaan:

```bash
python -c "
import os
print('Graph exists:', os.path.exists('./data/sulawesi_graph.graphml'))
print('FO exists:', os.path.exists('./data/fo_sulawesi/fo_sulawesi.shp'))
print('Pop exists:', os.path.exists('./data/pop.csv'))
"
```

## Fallback Behavior

Jika data files tidak ditemukan, sistem akan:
- **Graph**: Error - required untuk NetworkX routing
- **Fiber Optic**: Use dummy data (no overlap analysis)
- **Population**: Use dummy data (no population analysis)

## File Size Considerations

- **Graph file**: 79MB - Loading membutuhkan 5-10 detik
- **Shapefile**: Bervariasi tergantung coverage area
- **CSV files**: Relatif kecil, loading cepat

## Testing Data Paths

```python
from app.config import settings
print("Graph path:", settings.DEFAULT_GRAPH_PATH)
print("FO path:", settings.DEFAULT_FO_PATH)
print("Pop path:", settings.DEFAULT_POP_PATH)
```