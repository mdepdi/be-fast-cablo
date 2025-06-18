#!/usr/bin/env python3
"""
Test API Endpoint for LastMile Processing
"""

import requests
import json
import os

def test_health_endpoint():
    """Test the health endpoint"""
    print("🔄 Testing health endpoint...")
    try:
        response = requests.get("http://localhost:8000/api/v1/lastmile/health")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Health check successful:")
            print(json.dumps(data, indent=2))
        else:
            print(f"❌ Health check failed:")
            print(f"Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server. Make sure it's running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def test_process_endpoint():
    """Test the process endpoint with a simple CSV"""
    print("\n🔄 Testing process endpoint...")

    # Create a simple test CSV
    test_csv_content = """Far End (FE),Near End (NE),Lat_FE,Lon_FE,Lat_NE,Lon_NE
FE001,NE001,-6.2,106.8,-6.21,106.81
FE002,NE002,-6.22,106.82,-6.23,106.83"""

    # Save to temporary file
    test_csv_path = "test_requests.csv"
    with open(test_csv_path, 'w') as f:
        f.write(test_csv_content)

    try:
        # Prepare the request
        url = "http://localhost:8000/api/v1/lastmile/process"

        # Files
        files = {
            'file': ('test_requests.csv', open(test_csv_path, 'rb'), 'text/csv')
        }

        # Form data
        data = {
            'lat_fe_column': 'Lat_FE',
            'lon_fe_column': 'Lon_FE',
            'lat_ne_column': 'Lat_NE',
            'lon_ne_column': 'Lon_NE',
            'fe_name_column': 'Far End (FE)',
            'ne_name_column': 'Near End (NE)',
            'output_folder': 'test_output',
            'pulau': 'Sulawesi',
            'save_to_database': 'false',  # Disable database for initial test
            'api_key': 'test-api-key-12345'  # Use test API key
        }

        print("Sending request...")
        response = requests.post(url, files=files, data=data)

        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")

        if response.status_code == 200:
            print("✅ Process request successful:")
            result = response.json()
            print(json.dumps(result, indent=2))
        else:
            print(f"❌ Process request failed:")
            print(f"Response: {response.text}")

            # Try to parse as JSON for better error display
            try:
                error_data = response.json()
                print("Error details:")
                print(json.dumps(error_data, indent=2))
            except:
                pass

        # Close file
        files['file'][1].close()

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server. Make sure it's running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        # Clean up test file
        if os.path.exists(test_csv_path):
            os.remove(test_csv_path)

def test_process_with_database():
    """Test the process endpoint with database enabled"""
    print("\n🔄 Testing process endpoint with database...")

    # Create a simple test CSV
    test_csv_content = """Far End (FE),Near End (NE),Lat_FE,Lon_FE,Lat_NE,Lon_NE
FE001,NE001,-6.2,106.8,-6.21,106.81"""

    # Save to temporary file
    test_csv_path = "test_requests_db.csv"
    with open(test_csv_path, 'w') as f:
        f.write(test_csv_content)

    try:
        # Prepare the request
        url = "http://localhost:8000/api/v1/lastmile/process"

        # Files
        files = {
            'file': ('test_requests_db.csv', open(test_csv_path, 'rb'), 'text/csv')
        }

        # Form data
        data = {
            'lat_fe_column': 'Lat_FE',
            'lon_fe_column': 'Lon_FE',
            'lat_ne_column': 'Lat_NE',
            'lon_ne_column': 'Lon_NE',
            'fe_name_column': 'Far End (FE)',
            'ne_name_column': 'Near End (NE)',
            'output_folder': 'test_output_db',
            'pulau': 'Sulawesi',
            'save_to_database': 'true',  # Enable database
            'api_key': 'test-api-key-12345'  # Use test API key
        }

        print("Sending request with database enabled...")
        response = requests.post(url, files=files, data=data)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print("✅ Process request with database successful:")
            result = response.json()
            print(json.dumps(result, indent=2))

            # If we got a database_id, try to retrieve the result
            if result.get('database_id'):
                print(f"\n🔄 Testing result retrieval...")
                db_id = result['database_id']

                # Test get result endpoint
                result_url = f"http://localhost:8000/api/v1/lastmile/results/{db_id}?api_key=test-api-key-12345"
                result_response = requests.get(result_url)

                if result_response.status_code == 200:
                    print("✅ Result retrieval successful")
                    result_data = result_response.json()
                    print(f"Database ID: {result_data.get('database_id')}")
                    print(f"Status: {result_data.get('status')}")
                    print(f"Has GeoJSON: {result_data.get('result_analysis') is not None}")
                else:
                    print(f"❌ Result retrieval failed: {result_response.status_code}")
                    print(result_response.text)
        else:
            print(f"❌ Process request failed:")
            print(f"Response: {response.text}")

        # Close file
        files['file'][1].close()

    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        # Clean up test file
        if os.path.exists(test_csv_path):
            os.remove(test_csv_path)

if __name__ == "__main__":
    print("🧪 Testing LastMile API Endpoints")
    print("=" * 50)

    # Test health first
    test_health_endpoint()

    # Test process without database
    test_process_endpoint()

    # Test process with database
    test_process_with_database()

    print("\n✨ Testing completed!")
    print("\nIf you see errors, check:")
    print("1. API server is running: uvicorn app.main:app --reload")
    print("2. Database is set up: python setup_database.py --init")
    print("3. Dependencies are installed: pip install -r requirements-database.txt")