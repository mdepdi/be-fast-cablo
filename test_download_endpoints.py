#!/usr/bin/env python3
"""
Test Download Endpoints for LastMile API
"""

import requests
import json
import os
import tempfile

def test_process_and_download():
    """Test the complete flow: process -> get download links -> download files"""
    print("🧪 Testing Complete Process and Download Flow")
    print("=" * 60)

    # Create a simple test CSV
    test_csv_content = """Far End (FE),Near End (NE),Lat_FE,Lon_FE,Lat_NE,Lon_NE
FE001,NE001,-6.2,106.8,-6.21,106.81
FE002,NE002,-6.22,106.82,-6.23,106.83"""

    # Save to temporary file
    test_csv_path = "test_download_requests.csv"
    with open(test_csv_path, 'w') as f:
        f.write(test_csv_content)

    try:
        # Step 1: Process the request
        print("\n🔄 Step 1: Processing request...")
        url = "http://localhost:8000/api/v1/lastmile/process"

        files = {
            'file': ('test_download_requests.csv', open(test_csv_path, 'rb'), 'text/csv')
        }

        data = {
            'lat_fe_column': 'Lat_FE',
            'lon_fe_column': 'Lon_FE',
            'lat_ne_column': 'Lat_NE',
            'lon_ne_column': 'Lon_NE',
            'fe_name_column': 'Far End (FE)',
            'ne_name_column': 'Near End (NE)',
            'output_folder': 'test_download_output',
            'pulau': 'Sulawesi',
            'save_to_database': 'false',  # Disable database for this test
            'api_key': 'test-api-key-12345'
        }

        response = requests.post(url, files=files, data=data)
        files['file'][1].close()

        if response.status_code != 200:
            print(f"❌ Processing failed: {response.status_code}")
            print(response.text)
            return

        result = response.json()
        print(f"✅ Processing successful!")
        print(f"Request ID: {result['request_id']}")

        # Check if download_links are present
        if 'download_links' in result and result['download_links']:
            print(f"✅ Download links found: {len(result['download_links'])} files")

            # Step 2: Test each download link
            print(f"\n🔄 Step 2: Testing download links...")

            for file_type, download_url in result['download_links'].items():
                print(f"\n📥 Testing download: {file_type}")
                print(f"URL: {download_url}")

                # Download URL already includes full base URL, no API key needed
                download_url_full = download_url

                try:
                    download_response = requests.get(download_url_full)

                    if download_response.status_code == 200:
                        print(f"✅ Download successful: {len(download_response.content)} bytes")

                        # Save to temporary file to verify
                        filename = download_url.split('/')[-1]
                        temp_path = f"temp_{filename}"
                        with open(temp_path, 'wb') as f:
                            f.write(download_response.content)

                        file_size = os.path.getsize(temp_path)
                        print(f"   Saved as: {temp_path} ({file_size} bytes)")

                        # Clean up temp file
                        os.remove(temp_path)

                    else:
                        print(f"❌ Download failed: {download_response.status_code}")
                        print(f"   Error: {download_response.text}")

                except Exception as e:
                    print(f"❌ Download error: {str(e)}")

            # Step 3: Test list files endpoint
            print(f"\n🔄 Step 3: Testing list files endpoint...")
            request_id = result['request_id']
            list_url = f"http://localhost:8000/api/v1/lastmile/download/{request_id}"

            try:
                list_response = requests.get(list_url)

                if list_response.status_code == 200:
                    list_data = list_response.json()
                    print(f"✅ File listing successful: {list_data['total_files']} files found")

                    for file_info in list_data['files']:
                        print(f"   📄 {file_info['filename']} ({file_info['size_bytes']} bytes)")
                        print(f"      Type: {file_info['file_type']}")
                        print(f"      URL: {file_info['download_url']}")
                else:
                    print(f"❌ File listing failed: {list_response.status_code}")
                    print(list_response.text)

            except Exception as e:
                print(f"❌ File listing error: {str(e)}")

        else:
            print("⚠️ No download links found in response")
            print("Response keys:", list(result.keys()))

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server. Make sure it's running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
    finally:
        # Clean up test file
        if os.path.exists(test_csv_path):
            os.remove(test_csv_path)

def test_download_with_existing_request():
    """Test download with an existing request ID (if you have one)"""
    print("\n🔄 Testing Download with Existing Request ID")
    print("=" * 50)

    # You can replace this with an actual request ID from a previous run
    request_id = "719b7ef8-5fc9-4758-8a58-d9bf6a34988c"  # Example from your message

    try:
        # Test list files endpoint
        list_url = f"http://localhost:8000/api/v1/lastmile/download/{request_id}"

        print(f"Testing with request ID: {request_id}")
        print(f"URL: {list_url}")

        response = requests.get(list_url)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total_files']} files for request {request_id}")

            for file_info in data['files']:
                print(f"\n📄 {file_info['filename']}")
                print(f"   Size: {file_info['size_bytes']} bytes")
                print(f"   Type: {file_info['file_type']}")
                print(f"   Download URL: {file_info['download_url']}")

                # Test downloading the first file
                if file_info == data['files'][0]:  # Only test first file
                    print(f"   🔄 Testing download...")
                    download_url = file_info['download_url']  # Already includes full URL

                    try:
                        download_response = requests.get(download_url)
                        if download_response.status_code == 200:
                            print(f"   ✅ Download successful: {len(download_response.content)} bytes")
                        else:
                            print(f"   ❌ Download failed: {download_response.status_code}")
                    except Exception as e:
                        print(f"   ❌ Download error: {str(e)}")

        elif response.status_code == 404:
            print(f"⚠️ No files found for request ID: {request_id}")
            print("This is expected if the request ID doesn't exist or files were cleaned up")
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server. Make sure it's running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def test_download_error_cases():
    """Test error cases for download endpoints"""
    print("\n🔄 Testing Download Error Cases")
    print("=" * 40)

    base_url = "http://localhost:8000/api/v1/lastmile/download"
    api_key = "test-api-key-12345"

    test_cases = [
        {
            "name": "Non-existent request ID",
            "url": f"{base_url}/non-existent-request-id",
            "expected_status": 404
        },
        {
            "name": "Non-existent file",
            "url": f"{base_url}/some-request-id/non-existent-file.txt",
            "expected_status": 404
        }
    ]

    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        try:
            response = requests.get(test_case['url'])

            if response.status_code == test_case['expected_status']:
                print(f"✅ Expected status {test_case['expected_status']}: {response.status_code}")
            else:
                print(f"⚠️ Unexpected status. Expected: {test_case['expected_status']}, Got: {response.status_code}")

        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("🧪 Testing LastMile Download Endpoints")
    print("=" * 60)

    # Test complete flow
    test_process_and_download()

    # Test with existing request (if available)
    test_download_with_existing_request()

    # Test error cases
    test_download_error_cases()

    print("\n✨ Download endpoint testing completed!")
    print("\nEndpoints tested:")
    print("1. POST /api/v1/lastmile/process (with download_links)")
    print("2. GET /api/v1/lastmile/download/{request_id} (list files)")
    print("3. GET /api/v1/lastmile/download/{request_id}/{filename} (download file)")
    print("\nIf you see errors, check:")
    print("1. API server is running: uvicorn app.main:app --reload")
    print("2. Output directory permissions")
    print("3. File paths in settings.py")