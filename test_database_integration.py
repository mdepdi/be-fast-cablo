#!/usr/bin/env python3
"""
Test Database Integration for LastMile Processing
"""

import sys
import os
import uuid
from datetime import datetime

# Add the app directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_database_integration():
    """Test the complete database integration"""
    print("🧪 Testing LastMile Database Integration")
    print("=" * 50)

    try:
        # Import database modules
        from app.database.config import SessionLocal, engine
        from app.database.utils import (
            create_processing_job,
            save_processing_results,
            get_processing_result_geojson,
            get_processing_result_geodataframe,
            geodataframe_to_geojson
        )
        from app.database.crud import processing_result_crud
        from app.database.schemas import ProcessingStatus
        import geopandas as gpd
        from shapely.geometry import LineString, Point
        import pandas as pd

        print("✅ All imports successful")

        # Test 1: Database Connection
        print("\n🔄 Test 1: Database Connection")
        db = SessionLocal()
        try:
            result = db.execute("SELECT version()")
            version = result.fetchone()[0]
            print(f"✅ Connected to PostgreSQL: {version[:50]}...")
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
        finally:
            db.close()

        # Test 2: Create Processing Job
        print("\n🔄 Test 2: Create Processing Job")
        db = SessionLocal()
        try:
            test_request_id = f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            job = create_processing_job(
                db=db,
                request_id=test_request_id,
                input_filename="test_requests.csv",
                total_requests=5,
                pulau="TestIsland",
                ors_base_url="http://localhost:6080",
                graph_path="./test_graph.graphml",
                created_by="test_user",
                metadata_info={"test": True}
            )

            print(f"✅ Created job: {job.id}")
            print(f"   Request ID: {job.request_id}")
            print(f"   Status: {job.processing_status}")

        except Exception as e:
            print(f"❌ Failed to create processing job: {str(e)}")
            return False
        finally:
            db.close()

        # Test 3: Create Test GeoDataFrame
        print("\n🔄 Test 3: Create Test GeoDataFrame")
        try:
            # Create sample geodataframe
            test_data = {
                'type': ['ors', 'nx', 'ors'],
                'label': ['Route 1', 'Route 2', 'Route 3'],
                'total_distance_m': [1000.5, 2500.3, 1500.7],
                'segment_count': [2, 3, 2],
                'geometry': [
                    LineString([(106.8, -6.2), (106.81, -6.21)]),
                    LineString([(106.82, -6.22), (106.83, -6.23)]),
                    LineString([(106.84, -6.24), (106.85, -6.25)])
                ]
            }

            test_gdf = gpd.GeoDataFrame(test_data, crs='EPSG:4326')
            print(f"✅ Created test GeoDataFrame with {len(test_gdf)} features")

        except Exception as e:
            print(f"❌ Failed to create test GeoDataFrame: {str(e)}")
            return False

        # Test 4: Convert GeoDataFrame to GeoJSON
        print("\n🔄 Test 4: GeoDataFrame to GeoJSON Conversion")
        try:
            geojson_data = geodataframe_to_geojson(test_gdf)

            print(f"✅ Converted to GeoJSON:")
            print(f"   Type: {geojson_data['type']}")
            print(f"   Features: {len(geojson_data['features'])}")
            print(f"   Metadata: {geojson_data.get('metadata', {})}")

        except Exception as e:
            print(f"❌ Failed to convert to GeoJSON: {str(e)}")
            return False

        # Test 5: Save Processing Results
        print("\n🔄 Test 5: Save Processing Results")
        db = SessionLocal()
        try:
            analysis_summary = {
                "total_requests": 5,
                "processed_requests": 3,
                "total_distance_km": 5.0,
                "overlapped_percentage": 40,
                "new_build_percentage": 60,
                "processing_time_minutes": 2.5
            }

            output_files = [
                "test_output_1.geojson",
                "test_output_2.csv",
                "test_summary.json"
            ]

            success = save_processing_results(
                db=db,
                processing_result_id=job.id,
                dissolved_gdf=test_gdf,
                analysis_summary=analysis_summary,
                output_files=output_files
            )

            if success:
                print("✅ Results saved successfully")
            else:
                print("❌ Failed to save results")
                return False

        except Exception as e:
            print(f"❌ Failed to save processing results: {str(e)}")
            return False
        finally:
            db.close()

        # Test 6: Retrieve Results
        print("\n🔄 Test 6: Retrieve Processing Results")
        db = SessionLocal()
        try:
            # Get by ID
            retrieved_job = processing_result_crud.get(db, job.id)
            if retrieved_job:
                print(f"✅ Retrieved job by ID:")
                print(f"   Status: {retrieved_job.processing_status}")
                print(f"   Duration: {retrieved_job.processing_duration_seconds}s")
                print(f"   Has results: {retrieved_job.result_analysis is not None}")
            else:
                print("❌ Failed to retrieve job by ID")
                return False

            # Get GeoJSON
            geojson_result = get_processing_result_geojson(db, job.id)
            if geojson_result:
                print(f"✅ Retrieved GeoJSON with {len(geojson_result['features'])} features")
            else:
                print("❌ Failed to retrieve GeoJSON")
                return False

            # Get as GeoDataFrame
            gdf_result = get_processing_result_geodataframe(db, job.id)
            if gdf_result is not None and not gdf_result.empty:
                print(f"✅ Retrieved GeoDataFrame with {len(gdf_result)} features")
                print(f"   Columns: {list(gdf_result.columns)}")
                print(f"   CRS: {gdf_result.crs}")
            else:
                print("❌ Failed to retrieve GeoDataFrame")
                return False

        except Exception as e:
            print(f"❌ Failed to retrieve results: {str(e)}")
            return False
        finally:
            db.close()

        # Test 7: Query and Statistics
        print("\n🔄 Test 7: Query and Statistics")
        db = SessionLocal()
        try:
            # Get summary stats
            stats = processing_result_crud.get_summary_stats(db)
            print(f"✅ Summary statistics:")
            print(f"   Total jobs: {stats['total_jobs']}")
            print(f"   Completed jobs: {stats['completed_jobs']}")
            print(f"   Total requests processed: {stats['total_requests_processed']}")

            # Get recent results
            recent_results = processing_result_crud.get_multi(db, limit=5)
            print(f"✅ Retrieved {len(recent_results)} recent results")

        except Exception as e:
            print(f"❌ Failed to query statistics: {str(e)}")
            return False
        finally:
            db.close()

        # Test 8: Cleanup (Optional)
        print("\n🔄 Test 8: Cleanup Test Data")
        db = SessionLocal()
        try:
            # Delete test job
            deleted = processing_result_crud.delete(db, job.id)
            if deleted:
                print("✅ Test data cleaned up successfully")
            else:
                print("⚠️ Test data cleanup failed (job may not exist)")

        except Exception as e:
            print(f"⚠️ Cleanup warning: {str(e)}")
        finally:
            db.close()

        print("\n🎉 All tests passed! Database integration is working correctly.")
        return True

    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        print("Make sure you have installed all dependencies:")
        print("pip install -r requirements-database.txt")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False


def test_api_integration():
    """Test API integration with database"""
    print("\n🌐 Testing API Integration")
    print("=" * 30)

    try:
        import requests
        import json

        # Test health endpoint
        print("🔄 Testing health endpoint...")
        response = requests.get("http://localhost:8000/api/v1/lastmile/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ API Health: {health_data['status']}")
            print(f"   Database: {health_data['dependencies'].get('database', 'unknown')}")
            print(f"   ORS: {health_data['dependencies'].get('ors_server', 'unknown')}")
        else:
            print(f"⚠️ API health check failed: {response.status_code}")

        # Test stats endpoint (requires API key)
        print("\n🔄 Testing stats endpoint...")
        print("⚠️ Note: This requires a valid API key")

    except requests.exceptions.ConnectionError:
        print("⚠️ API server not running on http://localhost:8000")
        print("Start the API server first: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"⚠️ API test error: {str(e)}")


if __name__ == "__main__":
    print("🚀 LastMile Database Integration Test")
    print("=" * 50)

    # Test database integration
    db_success = test_database_integration()

    # Test API integration
    test_api_integration()

    if db_success:
        print("\n✨ Database integration is ready!")
        print("\n📝 Next steps:")
        print("1. Start your API server: uvicorn app.main:app --reload")
        print("2. Test the /process endpoint with save_to_database=True")
        print("3. Check results with /results endpoints")
        print("4. Monitor with /stats endpoint")
    else:
        print("\n❌ Database integration has issues. Please check the errors above.")

    sys.exit(0 if db_success else 1)