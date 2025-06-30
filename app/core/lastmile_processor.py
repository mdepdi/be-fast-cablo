"""
Core LastMile Processing Module
Optimized implementation for FastAPI integration
"""

import geopandas as gpd
import requests
import pandas as pd
from shapely.geometry import Point, LineString, MultiLineString
import polyline
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.ops import transform, linemerge
import networkx as nx
from shapely.wkt import loads as wkt_loads
import numpy as np
from scipy.spatial import KDTree
import os
import warnings
import json
from typing import Dict, List, Any, Optional, Tuple
import uuid
from datetime import datetime

# KML support
try:
    import simplekml
    KML_AVAILABLE = True
except ImportError:
    print("Warning: simplekml not available. KML output will be disabled.")
    print("Install with: pip install simplekml")
    KML_AVAILABLE = False

warnings.filterwarnings('ignore')

class LastMileProcessor:
    """Main class for processing lastmile routing requests"""

    def __init__(self):
        self.alternative_routes_combination = [
            {"weight_factor": 1.4, "share_factor": 0.6},
            {"weight_factor": 2.0, "share_factor": 0.3},
            {"weight_factor": 1.1, "share_factor": 0.8},
            {"weight_factor": 1.8, "share_factor": 0.4},
        ]

    # ==== UTILITY FUNCTIONS ====
    def _make_ors_request(self, url, payload):
        """Unified ORS API request handler"""
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Request failed with status code: {response.status_code}")
                print(f"Error message: {response.text}")
                return None
        except requests.exceptions.ConnectionError:
            print("Error: Could not connect to the ORS server")
            return None
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return None

    def snap_to_road(self, coordinates, radius=8000, ors_base_url="http://localhost:6080"):
        """Snap coordinates to nearest road using ORS snap API"""
        snap_url = f"{ors_base_url}/ors/v2/snap/driving-car/geojson"
        snap_payload = {
            "locations": [coordinates],
            "radius": radius
        }

        try:
            response = self._make_ors_request(snap_url, snap_payload)
            if response and response.get('features'):
                return response['features'][0]['geometry']['coordinates']
            else:
                print(f"No road found within {radius}m radius for coordinates {coordinates}")
                return coordinates
        except Exception as e:
            print(f"Error during snapping: {str(e)}")
            return coordinates

    # ==== ALTERNATIVE ROUTES FUNCTIONS ====
    def process_alternative_routes(self, start_coords, end_coords, directions_url):
        """Process alternative routes with different parameters"""
        final_result = gpd.GeoDataFrame()

        for route_option in self.alternative_routes_combination:
            payload = {
                "coordinates": [start_coords, end_coords],
                "alternative_routes": {
                    "target_count": 3,
                    "weight_factor": route_option["weight_factor"],
                    "share_factor": route_option["share_factor"]
                },
                "geometry": True,
                "instructions": False,
                "elevation": False,
            }

            response_data = self._make_ors_request(directions_url, payload)
            if response_data:
                gdf = self._convert_routes_to_gdf(response_data)
                final_result = pd.concat([final_result, gdf], ignore_index=True)

        return final_result

    def _convert_routes_to_gdf(self, routes_data):
        """Convert ORS routes response to GeoDataFrame"""
        features = []
        for i, route in enumerate(routes_data["routes"]):
            coordinates = polyline.decode(route["geometry"])
            line = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[lon, lat] for lat, lon in coordinates]
                },
                "properties": {
                    "summary": route.get("summary", {}),
                    "duration": route.get("summary", {}).get("duration"),
                    "distance": route.get("summary", {}).get("distance"),
                    "route_index": i
                }
            }
            features.append(line)

        try:
            gdf = gpd.GeoDataFrame.from_features(features)
            gdf.set_crs(epsg=4326, inplace=True)
            return gdf
        except Exception as e:
            print(f"Failed to convert routes to GeoDataFrame: {e}")
            return gpd.GeoDataFrame()

    def best_alternative_route(self, alternative_routes, fe_name, ne_name, fo_buffer):
        """Select best alternative route based on overlap with fiber optic infrastructure"""
        alternative_routes = alternative_routes.to_crs('epsg:3857')

        for j, r in alternative_routes.iterrows():
            gdf_row = gpd.GeoDataFrame([r], geometry=[r['geometry']], crs='epsg:3857')
            total_length = gdf_row['geometry'].length.reset_index(drop=True)[0]

            overlapped = gpd.overlay(gdf_row, fo_buffer[['NAME', 'geometry']], how='intersection')
            overlapped_length = overlapped["geometry"].length.reset_index(drop=True)[0] if not overlapped.empty else 0

            alternative_routes.at[j, 'overlapped_length'] = overlapped_length
            alternative_routes.at[j, 'new_length'] = total_length - overlapped_length

        return alternative_routes.sort_values(
            by=['overlapped_length', 'new_length'],
            ascending=[False, True]
        ).head(1)

    # ==== GRAPH AND SPATIAL INDEX FUNCTIONS ====
    def extract_node_coordinates(self, graph):
        """Extract node coordinates from graph edges"""
        node_coords = {}
        for u, v, edge_data in graph.edges(data=True):
            if 'geometry' in edge_data:
                geom = wkt_loads(edge_data['geometry'])
                coords = list(geom.coords)
                node_coords[u] = coords[0]
                node_coords[v] = coords[-1]
        return node_coords

    def build_spatial_index(self, node_coords):
        """Build KDTree spatial index for fast nearest neighbor search"""
        node_ids = list(node_coords.keys())
        coordinates = [node_coords[node_id] for node_id in node_ids]
        tree = KDTree(coordinates)
        return tree, node_ids

    def find_nearest_node(self, input_coords, tree, node_ids, k=1):
        """Find k nearest nodes to input coordinates"""
        distances, indices = tree.query(input_coords, k=k)
        if k == 1:
            return node_ids[indices], distances
        else:
            return [(node_ids[idx], distances[i]) for i, idx in enumerate(indices)]

    def find_nearest_node_simple(self, lon, lat, coordinate_system='4326', spatial_tree=None, node_id_list=None):
        """Simple function to find nearest node from longitude/latitude coordinates"""
        if coordinate_system == '4326':
            transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
            x, y = transformer.transform(lon, lat)
            input_coords = (x, y)
        else:
            input_coords = (lon, lat)

        return self.find_nearest_node(input_coords, spatial_tree, node_id_list, k=1)

    # ==== ROUTING FUNCTIONS ====
    def get_shortest_path_networkx(self, graph, start_node, end_node, weight='weight'):
        """Get shortest path using NetworkX"""
        try:
            path_nodes = nx.shortest_path(graph, start_node, end_node, weight=weight)
            total_distance = nx.shortest_path_length(graph, start_node, end_node, weight=weight)

            geometries = []
            for i in range(len(path_nodes) - 1):
                edge_data = graph[path_nodes[i]][path_nodes[i + 1]]
                if 'geometry' in edge_data:
                    geometries.append(wkt_loads(edge_data['geometry']))

            return {
                'success': True,
                'path_nodes': path_nodes,
                'total_distance': total_distance,
                'geometry': linemerge(geometries) if geometries else None,
                'num_nodes': len(path_nodes),
                'num_edges': len(path_nodes) - 1
            }

        except nx.NetworkXNoPath:
            return {
                'success': False,
                'error': f'No path found between {start_node} and {end_node}',
                'path_nodes': [],
                'total_distance': float('inf'),
                'geometry': None,
                'num_nodes': 0,
                'num_edges': 0
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'NetworkX error: {str(e)}',
                'path_nodes': [],
                'total_distance': float('inf'),
                'geometry': None,
                'num_nodes': 0,
                'num_edges': 0
            }

    def get_shortest_path_ors(self, start_coords, end_coords, ors_base_url="http://localhost:6080"):
        """Get shortest path using ORS"""
        try:
            directions_url = f"{ors_base_url}/ors/v2/directions/driving-car"
            payload = {
                "coordinates": [start_coords, end_coords],
                "geometry": True,
                "instructions": False,
                "elevation": False,
            }

            response = self._make_ors_request(directions_url, payload)
            if not response or not response.get("routes"):
                return {
                    'success': False,
                    'error': 'No routes found by ORS',
                    'total_distance': float('inf'),
                    'geometry': None,
                    'num_nodes': 0,
                    'num_edges': 0
                }

            route = response["routes"][0]
            coordinates = polyline.decode(route["geometry"])
            line_coords = [[lon, lat] for lat, lon in coordinates]
            geometry = LineString(line_coords)

            # Transform to EPSG:3857 for consistent CRS
            transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
            geometry_3857 = transform(lambda x, y, z=None: transformer.transform(x, y), geometry)

            return {
                'success': True,
                'total_distance': route["summary"]["distance"],
                'geometry': geometry_3857,
                'num_nodes': len(coordinates),
                'num_edges': len(coordinates) - 1,
                'ors_duration': route["summary"]["duration"],
                'ors_original_geometry': geometry
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'ORS error: {str(e)}',
                'total_distance': float('inf'),
                'geometry': None,
                'num_nodes': 0,
                'num_edges': 0
            }

    # ==== DATA PREPARATION FUNCTIONS ====
    def load_and_prepare_data(self, input_file_path: str, column_mapping: Dict[str, str]) -> pd.DataFrame:
        """Load and prepare lastmile data"""
        df = pd.read_csv(input_file_path)
        df['request_id'] = range(1, len(df) + 1)

        # Rename columns based on mapping
        df = df.rename(columns={
            column_mapping['fe_name_column']: 'Far End (FE)',
            column_mapping['lat_fe_column']: 'Lat_FE',
            column_mapping['lon_fe_column']: 'Lon_FE',
            column_mapping['ne_name_column']: 'Near End (NE)',
            column_mapping['lat_ne_column']: 'Lat_NE',
            column_mapping['lon_ne_column']: 'Lon_NE'
        })

        required_columns = ['request_id', 'Far End (FE)', 'Lat_FE', 'Lon_FE', 'Near End (NE)', 'Lat_NE', 'Lon_NE']
        return df[required_columns]

    def snap_endpoints_to_road(self, row, ors_base_url="http://localhost:6080",
                              lat_fe_column='Lat_FE', lon_fe_column='Lon_FE',
                              lat_ne_column='Lat_NE', lon_ne_column='Lon_NE'):
        """Snap FE and NE coordinates to nearest road"""
        FE_snapped = self.snap_to_road([row[lon_fe_column], row[lat_fe_column]], ors_base_url=ors_base_url)
        NE_snapped = self.snap_to_road([row[lon_ne_column], row[lat_ne_column]], ors_base_url=ors_base_url)
        return FE_snapped, NE_snapped

    def load_base_data(self, pulau="Sulawesi", fo_base_path=None, pop_path=None):
        """Load base data files"""
        try:
            # Load fiber optic data
            if fo_base_path:
                fo_path = fo_base_path
            else:
                fo_path = f"./data/fo_{pulau.lower()}/fo_{pulau.lower()}.shp"

            print(f"Loading fiber optic data from: {fo_path}")
            fo = gpd.read_file(fo_path)

            # Load population data
            if pop_path is None:
                pop_path = "./data/pop.csv"

            print(f"Loading population data from: {pop_path}")
            pop = pd.read_csv(pop_path, encoding='latin1')
            pop = gpd.GeoDataFrame(pop, geometry=gpd.points_from_xy(pop.longitude, pop.latitude), crs="EPSG:4326")

            # Create fiber optic buffer
            fo_buffer = fo.copy().to_crs('epsg:3857')
            fo_buffer['geometry'] = fo_buffer['geometry'].buffer(30, cap_style="flat")

            return fo, fo_buffer, pop

        except Exception as e:
            print(f"Error loading base data: {str(e)}")
            return None, None, None

    # ==== ROUTE PROCESSING FUNCTIONS ====
    def get_best_route(self, FE_snapped, NE_snapped, fe_name, ne_name, fo_buffer, directions_url):
        """Get the best alternative route between FE and NE"""
        alternative_routes = self.process_alternative_routes(FE_snapped, NE_snapped, directions_url)
        alternative_routes = alternative_routes.to_crs('epsg:3857')
        return self.best_alternative_route(alternative_routes, fe_name, ne_name, fo_buffer)

    def process_overlapped_segments(self, best_route, fo_buffer):
        """Process overlapped segments with fiber optic buffer"""
        overlapped = gpd.overlay(best_route, fo_buffer[['NAME', 'geometry']], how='intersection')

        overlapped_line = overlapped.copy()
        overlapped_line['id'] = 1
        overlapped_line = overlapped_line.dissolve(by='id', as_index=False)
        overlapped_line = overlapped_line.explode(index_parts=True).reset_index(drop=True)
        overlapped_line['lid'] = range(len(overlapped_line))

        return overlapped_line[['lid', 'geometry']]

    def process_non_overlapped_segments(self, best_route, overlapped_line):
        """Process non-overlapped segments"""
        overlapped_buffer = overlapped_line.copy()
        overlapped_buffer['geometry'] = overlapped_buffer['geometry'].buffer(30, cap_style='flat')

        not_overlapped = gpd.overlay(best_route, overlapped_buffer, how='difference')
        not_overlapped_line = not_overlapped.copy()
        not_overlapped_line['id'] = 1
        not_overlapped_line = not_overlapped_line.dissolve(by='id', as_index=False)
        not_overlapped_line = not_overlapped_line.explode(index_parts=True).reset_index(drop=True)
        not_overlapped_line['lid'] = range(len(not_overlapped_line))

        return not_overlapped_line[['lid', 'geometry']]

    def extract_segment_endpoints(self, overlapped_line, not_overlapped_line):
        """Extract start and end points from overlapped and non-overlapped segments"""
        first_last_point = pd.DataFrame()

        # Process non-overlapped segments
        for i, row in not_overlapped_line.iterrows():
            first_point = row['geometry'].coords[0]
            last_point = row['geometry'].coords[-1]
            lid = f"no_{row['lid']}"

            start_lid_point = pd.DataFrame([{
                'lid': lid,
                'geometry': Point(first_point),
                'type': 'start_not_overlapped'
            }])

            end_lid_point = pd.DataFrame([{
                'lid': lid,
                'geometry': Point(last_point),
                'type': 'end_not_overlapped'
            }])

            first_last_point = pd.concat([first_last_point, start_lid_point, end_lid_point], ignore_index=True)

        # Process overlapped segments
        for i, row in overlapped_line.iterrows():
            first_point = row['geometry'].coords[0]
            last_point = row['geometry'].coords[-1]
            lid = f"o_{row['lid']}"

            start_lid_point = pd.DataFrame([{
                'lid': lid,
                'geometry': Point(first_point),
                'type': 'start_overlapped'
            }])

            end_lid_point = pd.DataFrame([{
                'lid': lid,
                'geometry': Point(last_point),
                'type': 'end_overlapped'
            }])

            first_last_point = pd.concat([first_last_point, start_lid_point, end_lid_point], ignore_index=True)

        return first_last_point

    def calculate_distances_and_nodes(self, first_last_point, best_route, spatial_tree, node_id_list):
        """Calculate distances along route and find nearest nodes"""
        first_last_point = first_last_point.set_geometry('geometry', crs='EPSG:3857')
        main_line = best_route['geometry'].iloc[0]

        # Calculate distance along main line
        for i, row in first_last_point.iterrows():
            snap_point = main_line.interpolate(main_line.project(row['geometry']))
            distance_along_line = main_line.project(snap_point)
            first_last_point.at[i, 'distance_to_first'] = distance_along_line

        # Sort by line ID and distance
        first_last_point = first_last_point.sort_values(by=['lid', 'distance_to_first']).reset_index(drop=True)

        # Find nearest nodes AFTER sorting
        for i, row in first_last_point.iterrows():
            loc = row['geometry']
            nearest_id, dist = self.find_nearest_node_simple(loc.x, loc.y, '3857', spatial_tree, node_id_list)
            first_last_point.at[i, 'node_id'] = nearest_id

        return first_last_point


    # ==== PATH GENERATION FUNCTIONS ====
    def generate_segment_paths(self,first_last_point, G, ors_base_url="http://localhost:6080"):
        """Generate paths for each segment using appropriate routing method"""
        first_last_point = first_last_point.to_crs('EPSG:4326')
        final_path = gpd.GeoDataFrame()

        for i, row in first_last_point.iterrows():
            if row['type'] == 'start_not_overlapped':
                # Use ORS for non-overlapped segments
                next_row = first_last_point.loc[i+1]
                ors_path = self.get_shortest_path_ors(
                    [row['geometry'].x, row['geometry'].y],
                    [next_row['geometry'].x, next_row['geometry'].y],
                    ors_base_url=ors_base_url
                )

                if ors_path['success']:
                    ors_dict = {
                        'type': 'ors',
                        'total_distance': ors_path['total_distance'],
                        'geometry': ors_path['geometry']
                    }

                    ors_gdf = gpd.GeoDataFrame([ors_dict], geometry='geometry', crs='EPSG:4326')
                    final_path = pd.concat([final_path, ors_gdf], ignore_index=True)

            elif row['type'] == 'start_overlapped':
                # Use NetworkX for overlapped segments
                next_row = first_last_point.loc[i+1]
                nx_path = self.get_shortest_path_networkx(G, row['node_id'], next_row['node_id'], weight='length')

                if nx_path['success'] and nx_path["geometry"] is not None and not nx_path["geometry"].is_empty:
                    nx_dict = {
                        'type': 'nx',
                        'total_distance': nx_path['total_distance'],
                        'geometry': nx_path['geometry']
                    }

                    nx_gdf = gpd.GeoDataFrame([nx_dict], geometry='geometry', crs='EPSG:4326')
                    final_path = pd.concat([final_path, nx_gdf], ignore_index=True)

        return final_path

# ==== CONNECTION FUNCTIONS ====
    def connect_path_segments(self, final_path, exclude_first=True, threshold=0.1):
        """Connect disconnected path segments"""
        final_path = final_path[final_path['total_distance'] > 0].reset_index(drop=True)
        final_path = final_path.set_geometry('geometry', crs='EPSG:3857')

        # Extract endpoints
        endpoints = []
        for idx, row in final_path.iterrows():
            geom = row['geometry']
            if geom is not None and isinstance(geom, LineString):
                start = Point(geom.coords[0])
                end = Point(geom.coords[-1])
                endpoints.append((idx, 'start', start, row['type']))
                endpoints.append((idx, 'end', end, row['type']))

        endpoints_gdf = gpd.GeoDataFrame(endpoints, columns=["line_id", "pos", "geometry", "type"],
                                        geometry="geometry", crs=final_path.crs)
        coords = np.array([[pt.x, pt.y] for pt in endpoints_gdf.geometry])
        tree = cKDTree(coords)

        # Find excluded indices
        excluded_index = []
        if exclude_first:
            mask = (endpoints_gdf['line_id'] == 0) & (endpoints_gdf['pos'] == 'start')
            excluded_index = endpoints_gdf[mask].index.tolist()

        # Find connection pairs
        pairs = []
        visited = set()
        for i, point in enumerate(coords):
            if i in visited or i in excluded_index:
                continue
            dist, j = tree.query(point, k=2)
            if j[1] in visited or j[1] in excluded_index:
                continue
            if dist[1] < 1e-6:
                continue

            pt1 = endpoints_gdf.geometry.iloc[i]
            pt2 = endpoints_gdf.geometry.iloc[j[1]]
            if pt1.distance(pt2) > threshold:
                pairs.append((i, j[1]))
                visited.add(i)
                visited.add(j[1])

        # Create connections
        connection_records = []
        for i, j in pairs:
            pt1 = endpoints_gdf.geometry.iloc[i]
            pt2 = endpoints_gdf.geometry.iloc[j]
            line = LineString([pt1, pt2])
            connection_records.append({
                'type': endpoints_gdf.iloc[i]['type'],
                'total_distance': line.length,
                'geometry': line,
            })

        connections_gdf = gpd.GeoDataFrame(connection_records, geometry='geometry', crs=final_path.crs)

        # Merge connections with final path
        merged_gdf = pd.concat([final_path, connections_gdf], ignore_index=True)
        merged_gdf['total_distance'] = merged_gdf['geometry'].length

        return merged_gdf


    def dissolve_by_type_with_labels(self, gdf):
        """Dissolve linestring geodataframe by type while preserving Far End and Near End information"""
        dissolved_results = []

        # Determine FE and NE column names dynamically
        fe_col = None
        ne_col = None
        for col in gdf.columns:
            if ('Far End' in col or ('FE' in col and 'Lat_' not in col and 'Lon_' not in col)):
                fe_col = col
            elif ('Near End' in col or ('NE' in col and 'Lat_' not in col and 'Lon_' not in col)):
                ne_col = col

        # Fallback to default names if not found
        if fe_col is None:
            fe_col = 'Far End (FE)'
        if ne_col is None:
            ne_col = 'Near End (NE)'

        # Group by type, Far End, and Near End
        if fe_col in gdf.columns and ne_col in gdf.columns:
            group_cols = ['type', fe_col, ne_col]
        else:
            print("Warning: FE/NE columns not found, grouping by type only")
            group_cols = ['type']

        grouped = gdf.groupby(group_cols)

        for group_key, group_gdf in grouped:
            # Collect all geometries in this group
            geoms = group_gdf['geometry'].tolist()

            # Merge lines where possible
            if len(geoms) > 1:
                try:
                    dissolved_geom = linemerge(geoms)
                except:
                    dissolved_geom = MultiLineString(geoms)
            else:
                dissolved_geom = geoms[0]

            # Extract group information
            if len(group_cols) == 3:  # type, FE, NE
                type_value, fe_value, ne_value = group_key
            else:  # type only
                type_value = group_key
                fe_value = group_gdf[fe_col].iloc[0] if fe_col in group_gdf.columns else "N/A"
                ne_value = group_gdf[ne_col].iloc[0] if ne_col in group_gdf.columns else "N/A"

            # Add label based on type
            label = 'new-build' if type_value == 'ors' else 'overlapped'

            # Calculate total distance in meters using EPSG:3857
            if gdf.crs.to_string() != 'EPSG:3857':
                temp_gdf = gpd.GeoDataFrame([{'geometry': dissolved_geom}], geometry='geometry', crs=gdf.crs)
                dissolved_geom_3857 = temp_gdf.to_crs('EPSG:3857').geometry.iloc[0]
            else:
                dissolved_geom_3857 = dissolved_geom

            total_distance_m = dissolved_geom_3857.length if hasattr(dissolved_geom_3857, 'length') else sum([geom.length for geom in dissolved_geom_3857.geoms])

            # Create dissolved record
            dissolved_record = {
                'type': type_value,
                'label': label,
                fe_col: fe_value,
                ne_col: ne_value,
                'total_distance_m': total_distance_m,
                'geometry': dissolved_geom,
                'segment_count': len(group_gdf),
                'request_id': group_gdf['request_id'].iloc[0] if 'request_id' in group_gdf.columns else None
            }

            # Add coordinate columns if they exist
            coord_cols = [col for col in group_gdf.columns if any(x in col for x in ['Lat_', 'Lon_', 'lat_', 'lon_'])]
            for coord_col in coord_cols:
                if coord_col not in dissolved_record:
                    dissolved_record[coord_col] = group_gdf[coord_col].iloc[0]

            dissolved_results.append(dissolved_record)

        return gpd.GeoDataFrame(dissolved_results, geometry='geometry', crs=gdf.crs)

    # ==== KML OUTPUT FUNCTIONS ====
    def create_kml_output(self, dissolved_gdf, output_folder, request_id, input_data=None,
                         fe_name_column='Far End (FE)', ne_name_column='Near End (NE)',
                         lat_fe_column='Lat_FE', lon_fe_column='Lon_FE',
                         lat_ne_column='Lat_NE', lon_ne_column='Lon_NE'):
        """Create KML output file from dissolved geodataframe"""
        if not KML_AVAILABLE:
            print("KML output skipped - simplekml not available")
            return []

        try:
            import simplekml
            kml_files = []

            # Create combined KML
            kml = simplekml.Kml()
            kml.document.name = "Last Mile Routes"

            # Add extended data to document
            kml.document.extendeddata.newdata(name="description", value="Last mile routing results with overlapped and new-build segments")
            kml.document.extendeddata.newdata(name="created_by", value="LastMile Processor")
            kml.document.extendeddata.newdata(name="request_id", value=str(request_id))

            # Add all routes to KML
            for idx, row in dissolved_gdf.iterrows():
                fe_name = str(row.get(fe_name_column, f"FE_{idx}")).replace(' ', '_').replace('(', '').replace(')', '')
                ne_name = str(row.get(ne_name_column, f"NE_{idx}")).replace(' ', '_').replace('(', '').replace(')', '')
                label_type = row['label']
                path_name = f"{label_type}_{fe_name}_{ne_name}"

                # Convert geometry to WGS84 if needed
                geom = row['geometry']
                if dissolved_gdf.crs.to_string() != 'EPSG:4326':
                    temp_gdf = gpd.GeoDataFrame([row], geometry='geometry', crs=dissolved_gdf.crs)
                    geom = temp_gdf.to_crs('EPSG:4326').geometry.iloc[0]

                # Add linestring to KML
                if geom.geom_type == 'LineString':
                    coords = [(coord[0], coord[1]) for coord in geom.coords]
                    linestring = kml.newlinestring(name=path_name)
                    linestring.coords = coords
                    self._add_extended_data_to_linestring(linestring, row)

                    # Add geometry information
                    linestring.extendeddata.newdata(name="geometry_type", value="LineString")
                    linestring.extendeddata.newdata(name="coordinate_count", value=str(len(coords)))
                elif geom.geom_type == 'MultiLineString':
                    for i, line in enumerate(geom.geoms):
                        coords = [(coord[0], coord[1]) for coord in line.coords]
                        linestring = kml.newlinestring(name=f"{path_name}_part_{i+1}")
                        linestring.coords = coords
                        self._add_extended_data_to_linestring(linestring, row, f"Part {i+1} of {len(geom.geoms)}")

                        # Add geometry information for multi-part
                        linestring.extendeddata.newdata(name="geometry_type", value="MultiLineString")
                        linestring.extendeddata.newdata(name="part_number", value=str(i+1))
                        linestring.extendeddata.newdata(name="total_parts", value=str(len(geom.geoms)))
                        linestring.extendeddata.newdata(name="coordinate_count", value=str(len(coords)))

                        # Apply styling per part
                        if label_type == 'overlapped':
                            linestring.style.linestyle.color = '10B981FF'  # GREEN
                            linestring.style.linestyle.width = 4
                        else:  # new-build
                            linestring.style.linestyle.color = '3B82F6FF'  # BLUE
                            linestring.style.linestyle.width = 4
                    continue


                # Apply styling based on label type
                if label_type == 'overlapped':
                    linestring.style.linestyle.color = '10B981FF'  # GREEN
                    linestring.style.linestyle.width = 4
                else:  # new-build
                    linestring.style.linestyle.color = '3B82F6FF'  # BLUE
                    linestring.style.linestyle.width = 4



            # Add FE and NE points from original input data
            if input_data is not None:
                self._add_fe_ne_points_from_input(kml, input_data,
                                                fe_name_column, ne_name_column,
                                                lat_fe_column, lon_fe_column,
                                                lat_ne_column, lon_ne_column)

            # Save KML file
            kml_filename = f"lastmile_routes_{request_id}.kml"
            kml_filepath = os.path.join(output_folder, kml_filename)
            kml.save(kml_filepath)
            kml_files.append(kml_filepath)

            print(f"Created KML file: {kml_filename}")
            return kml_files

        except Exception as e:
            print(f"Warning: KML creation failed: {str(e)}")
            return []

    def _add_extended_data_to_linestring(self, linestring, row, additional_info=""):
        """Add extended data to KML linestring"""
        fe_name = "N/A"
        ne_name = "N/A"
        for col in row.index:
            if 'Far End' in col and 'Lat_' not in col and 'Lon_' not in col:
                fe_name = row[col]
            elif 'Near End' in col and 'Lat_' not in col and 'Lon_' not in col:
                ne_name = row[col]

        # Add extended data fields
        linestring.extendeddata.newdata(name="fe_name", value=str(fe_name))
        linestring.extendeddata.newdata(name="ne_name", value=str(ne_name))
        linestring.extendeddata.newdata(name="route", value=f"{fe_name} → {ne_name}")
        linestring.extendeddata.newdata(name="type", value=str(row['label'].title()))
        linestring.extendeddata.newdata(name="distance_m", value=f"{row['total_distance_m']:.2f}")
        linestring.extendeddata.newdata(name="segment_count", value=str(row['segment_count']))

        if additional_info:
            linestring.extendeddata.newdata(name="note", value=str(additional_info))

        # Add request_id if available
        if 'request_id' in row.index:
            linestring.extendeddata.newdata(name="request_id", value=str(row['request_id']))

        # Add coordinate information if available
        coord_cols = [col for col in row.index if any(x in col for x in ['Lat_', 'Lon_', 'lat_', 'lon_'])]
        for coord_col in coord_cols:
            if coord_col in row.index:
                linestring.extendeddata.newdata(name=coord_col.lower(), value=str(row[coord_col]))

    def _add_fe_ne_points_from_input(self, kml, input_data, fe_name_column='Far End (FE)', ne_name_column='Near End (NE)',
                                   lat_fe_column='Lat_FE', lon_fe_column='Lon_FE',
                                   lat_ne_column='Lat_NE', lon_ne_column='Lon_NE'):
        """Add all FE and NE endpoint points to KML from original input data"""
        try:
            # Track added points to avoid duplicates
            added_fe_points = set()
            added_ne_points = set()

            for _, row in input_data.iterrows():
                # Add FE point
                if lat_fe_column in row.index and lon_fe_column in row.index:
                    fe_name = str(row[fe_name_column])
                    fe_key = (fe_name, float(row[lon_fe_column]), float(row[lat_fe_column]))

                    if fe_key not in added_fe_points:
                        fe_coords = (float(row[lon_fe_column]), float(row[lat_fe_column]))
                        fe_point = kml.newpoint(name=f"FE: {fe_name}")
                        fe_point.coords = [fe_coords]

                        # Add extended data for FE point
                        fe_point.extendeddata.newdata(name="name", value=str(fe_name))
                        fe_point.extendeddata.newdata(name="longitude", value=str(row[lon_fe_column]))
                        fe_point.extendeddata.newdata(name="latitude", value=str(row[lat_fe_column]))
                        fe_point.extendeddata.newdata(name="type", value="Far End")
                        fe_point.extendeddata.newdata(name="point_type", value="FE")

                        # Green circle for FE
                        fe_point.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/grn-circle.png'
                        fe_point.style.iconstyle.scale = 0.8
                        added_fe_points.add(fe_key)

                # Add NE point
                if lat_ne_column in row.index and lon_ne_column in row.index:
                    ne_name = str(row[ne_name_column])
                    ne_key = (ne_name, float(row[lon_ne_column]), float(row[lat_ne_column]))

                    if ne_key not in added_ne_points:
                        ne_coords = (float(row[lon_ne_column]), float(row[lat_ne_column]))
                        ne_point = kml.newpoint(name=f"NE: {ne_name}")
                        ne_point.coords = [ne_coords]

                        # Add extended data for NE point
                        ne_point.extendeddata.newdata(name="name", value=str(ne_name))
                        ne_point.extendeddata.newdata(name="longitude", value=str(row[lon_ne_column]))
                        ne_point.extendeddata.newdata(name="latitude", value=str(row[lat_ne_column]))
                        ne_point.extendeddata.newdata(name="type", value="Near End")
                        ne_point.extendeddata.newdata(name="point_type", value="NE")

                        # Red circle for NE
                        ne_point.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/red-circle.png'
                        ne_point.style.iconstyle.scale = 0.8
                        added_ne_points.add(ne_key)

            print(f"Added {len(added_fe_points)} unique FE points and {len(added_ne_points)} unique NE points to KML")

        except Exception as e:
            print(f"Warning: Failed to add FE/NE points to KML: {str(e)}")
            pass

    # ==== HYBRID ROUTING OPTIMIZATION FUNCTIONS ====
    def find_progressive_hybrid_route(self, fe_coords, ne_coords, G, spatial_tree, node_id_list, ors_base_url="http://localhost:6080"):
        """Find hybrid route using progressive approach - start from FE, extend via NetworkX as far as possible towards NE"""

        transformer_to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        transformer_to_4326 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

        fe_3857 = transformer_to_3857.transform(fe_coords[0], fe_coords[1])
        ne_3857 = transformer_to_3857.transform(ne_coords[0], ne_coords[1])

        # Find nearest nodes from FE
        fe_candidates = self.find_nearest_node(fe_3857, spatial_tree, node_id_list, k=15)

        best_progressive_route = None
        min_new_build_distance = float('inf')
        node_coords = self.extract_node_coordinates(G)

        print(f"  Trying progressive approach from {len(fe_candidates)} FE candidates...")

        for fe_node_id, fe_dist in fe_candidates:
            if fe_dist > 5000:  # Skip too distant
                continue

            try:
                # Get all reachable nodes from this FE node
                reachable_nodes = {}
                distances = nx.single_source_dijkstra_path_length(G, fe_node_id, weight='length', cutoff=50000)  # 50km limit

                # Find the reachable node that is closest to NE
                best_end_node = None
                min_distance_to_ne = float('inf')

                for reachable_node_id, nx_distance in distances.items():
                    if reachable_node_id == fe_node_id:
                        continue

                    reachable_coords_3857 = node_coords[reachable_node_id]
                    distance_to_ne = ((reachable_coords_3857[0] - ne_3857[0])**2 + (reachable_coords_3857[1] - ne_3857[1])**2)**0.5

                    if distance_to_ne < min_distance_to_ne:
                        min_distance_to_ne = distance_to_ne
                        best_end_node = (reachable_node_id, nx_distance, distance_to_ne)

                if best_end_node is None:
                    continue

                end_node_id, nx_distance, remaining_distance = best_end_node

                # Calculate the actual path distances
                fe_node_coords_4326 = transformer_to_4326.transform(node_coords[fe_node_id][0], node_coords[fe_node_id][1])
                end_node_coords_4326 = transformer_to_4326.transform(node_coords[end_node_id][0], node_coords[end_node_id][1])

                # ORS from FE to start of NetworkX
                ors_fe_to_nx = self.get_shortest_path_ors(fe_coords, fe_node_coords_4326, ors_base_url)
                if not ors_fe_to_nx['success']:
                    continue

                # ORS from end of NetworkX to NE
                ors_nx_to_ne = self.get_shortest_path_ors(end_node_coords_4326, ne_coords, ors_base_url)
                if not ors_nx_to_ne['success']:
                    continue

                # Total new-build distance
                total_new_build = ors_fe_to_nx['total_distance'] + ors_nx_to_ne['total_distance']

                if total_new_build < min_new_build_distance:
                    # Get the actual NetworkX path
                    nx_path = self.get_shortest_path_networkx(G, fe_node_id, end_node_id, weight='length')

                    if nx_path['success']:
                        min_new_build_distance = total_new_build
                        best_progressive_route = {
                            'fe_to_nx_ors': ors_fe_to_nx,
                            'nx_path': nx_path,
                            'nx_to_ne_ors': ors_nx_to_ne,
                            'total_new_build_distance': total_new_build,
                            'total_nx_distance': nx_path['total_distance'],
                            'fe_node_id': fe_node_id,
                            'ne_node_id': end_node_id,
                            'approach': 'progressive'
                        }

                        print(f"    Progressive route: {total_new_build:.0f}m new-build, {nx_path['total_distance']:.0f}m existing fiber")

            except Exception as e:
                continue

        return best_progressive_route
    def find_optimal_hybrid_route(self, fe_coords, ne_coords, G, spatial_tree, node_id_list, fo_buffer, ors_base_url="http://localhost:6080"):
        """Find optimal hybrid route that minimizes new-build distance"""

        # Convert coordinates to EPSG:3857 for consistent distance calculations
        transformer_to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        transformer_to_4326 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

        fe_3857 = transformer_to_3857.transform(fe_coords[0], fe_coords[1])
        ne_3857 = transformer_to_3857.transform(ne_coords[0], ne_coords[1])

        # Calculate direct ORS distance first for comparison
        direct_ors = self.get_shortest_path_ors(fe_coords, ne_coords, ors_base_url)
        direct_distance = direct_ors['total_distance'] if direct_ors['success'] else float('inf')

        print(f"  Direct ORS distance: {direct_distance:.0f}m")

        # Find multiple nearest nodes with larger search radius
        fe_candidates = self.find_nearest_node(fe_3857, spatial_tree, node_id_list, k=25)
        ne_candidates = self.find_nearest_node(ne_3857, spatial_tree, node_id_list, k=25)

        best_route = None
        min_new_build_distance = float('inf')
        valid_combinations = 0

        print(f"  Evaluating up to {len(fe_candidates)} x {len(ne_candidates)} node combinations...")

        # Get node coordinates once
        node_coords = self.extract_node_coordinates(G)

        # Try different combinations of FE and NE candidate nodes
        for i, (fe_node_id, fe_dist) in enumerate(fe_candidates):
            # Skip very distant FE candidates (more than 5km)
            if fe_dist > 5000:
                continue

            for j, (ne_node_id, ne_dist) in enumerate(ne_candidates):
                # Skip very distant NE candidates (more than 5km)
                if ne_dist > 5000:
                    continue

                # Skip if same node
                if fe_node_id == ne_node_id:
                    continue

                try:
                    # Check if there's a NetworkX path between candidates
                    nx_path = self.get_shortest_path_networkx(G, fe_node_id, ne_node_id, weight='length')

                    if not nx_path['success']:
                        continue

                    valid_combinations += 1

                    # Get node coordinates
                    fe_node_coords_3857 = node_coords[fe_node_id]
                    ne_node_coords_3857 = node_coords[ne_node_id]

                    # Convert back to 4326 for ORS
                    fe_node_coords_4326 = transformer_to_4326.transform(fe_node_coords_3857[0], fe_node_coords_3857[1])
                    ne_node_coords_4326 = transformer_to_4326.transform(ne_node_coords_3857[0], ne_node_coords_3857[1])

                    # Calculate ORS distances (new-build segments)
                    # FE to first NetworkX node
                    ors_fe_to_nx = self.get_shortest_path_ors(fe_coords, fe_node_coords_4326, ors_base_url)
                    if not ors_fe_to_nx['success']:
                        continue

                    # Last NetworkX node to NE
                    ors_nx_to_ne = self.get_shortest_path_ors(ne_node_coords_4326, ne_coords, ors_base_url)
                    if not ors_nx_to_ne['success']:
                        continue

                    # Calculate total new-build distance
                    total_new_build = ors_fe_to_nx['total_distance'] + ors_nx_to_ne['total_distance']

                    # Only consider if significantly better than direct route
                    improvement_threshold = 0.95  # Must be at least 5% better
                    if total_new_build < min_new_build_distance and total_new_build < (direct_distance * improvement_threshold):
                        min_new_build_distance = total_new_build
                        improvement_pct = ((direct_distance - total_new_build) / direct_distance) * 100

                        best_route = {
                            'fe_to_nx_ors': ors_fe_to_nx,
                            'nx_path': nx_path,
                            'nx_to_ne_ors': ors_nx_to_ne,
                            'total_new_build_distance': total_new_build,
                            'total_nx_distance': nx_path['total_distance'],
                            'fe_node_id': fe_node_id,
                            'ne_node_id': ne_node_id,
                            'improvement_pct': improvement_pct,
                            'direct_comparison': direct_distance
                        }

                        print(f"    Found better hybrid route: {total_new_build:.0f}m vs {direct_distance:.0f}m ({improvement_pct:.1f}% improvement)")

                except Exception as e:
                    continue

        print(f"  Evaluated {valid_combinations} valid NetworkX connections")

        # Use best hybrid route if found and significantly better, otherwise use direct ORS
        if best_route is not None:
            print(f"  Selected hybrid route with {best_route['improvement_pct']:.1f}% improvement")
            return best_route
        else:
            print("  No significant improvement found with hybrid routing, using direct ORS")
            if direct_ors['success']:
                return {
                    'direct_ors': direct_ors,
                    'total_new_build_distance': direct_ors['total_distance'],
                    'total_nx_distance': 0,
                    'is_direct': True
                }
            else:
                return None

    def create_hybrid_route_gdf(self, hybrid_route, row):
        """Create GeoDataFrame from hybrid route result"""
        segments = []

        if hybrid_route.get('is_direct', False):
            # Direct ORS route
            segment = {
                'type': 'ors',
                'total_distance': hybrid_route['direct_ors']['total_distance'],
                'geometry': hybrid_route['direct_ors']['ors_original_geometry'],
                'request_id': row.get('request_id', 0),
                'segment_id': 0
            }
            segments.append(segment)
        else:
            # Hybrid route with multiple segments
            segment_id = 0

            # FE to NetworkX segment (ORS)
            if hybrid_route['fe_to_nx_ors']['success']:
                segment = {
                    'type': 'ors',
                    'total_distance': hybrid_route['fe_to_nx_ors']['total_distance'],
                    'geometry': hybrid_route['fe_to_nx_ors']['ors_original_geometry'],
                    'request_id': row.get('request_id', 0),
                    'segment_id': segment_id
                }
                segments.append(segment)
                segment_id += 1

            # NetworkX segment (existing fiber)
            if hybrid_route['nx_path']['success'] and hybrid_route['nx_path']['geometry'] is not None:
                # Convert NetworkX geometry to EPSG:4326
                transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
                nx_geom = transform(lambda x, y, z=None: transformer.transform(x, y), hybrid_route['nx_path']['geometry'])

                segment = {
                    'type': 'nx',
                    'total_distance': hybrid_route['nx_path']['total_distance'],
                    'geometry': nx_geom,
                    'request_id': row.get('request_id', 0),
                    'segment_id': segment_id
                }
                segments.append(segment)
                segment_id += 1

            # NetworkX to NE segment (ORS)
            if hybrid_route['nx_to_ne_ors']['success']:
                segment = {
                    'type': 'ors',
                    'total_distance': hybrid_route['nx_to_ne_ors']['total_distance'],
                    'geometry': hybrid_route['nx_to_ne_ors']['ors_original_geometry'],
                    'request_id': row.get('request_id', 0),
                    'segment_id': segment_id
                }
                segments.append(segment)

        # Create GeoDataFrame
        if segments:
            gdf = gpd.GeoDataFrame(segments, geometry='geometry', crs='EPSG:4326')

            # Add request information
            for col in ['Far End (FE)', 'Near End (NE)', 'Lat_FE', 'Lon_FE', 'Lat_NE', 'Lon_NE']:
                if col in row.index:
                    gdf[col] = row[col]

            return gdf

        return gpd.GeoDataFrame()

    # ==== MAIN PROCESSING FUNCTIONS (UPDATED) ====
    def process_single_request(self, row, index, G, fo_buffer, pop, spatial_tree, node_id_list, ors_base_url="http://localhost:6080", directions_url=None,
                              fe_name_column='Far End (FE)', ne_name_column='Near End (NE)',
                              lat_fe_column='Lat_FE', lon_fe_column='Lon_FE',
                              lat_ne_column='Lat_NE', lon_ne_column='Lon_NE'):
        """Process a single lastmile request with optimized hybrid routing approach"""
        print(f"Processing request {index + 1}: {row[fe_name_column]} -> {row[ne_name_column]}")

        try:
            # Step 1: Snap endpoints to road
            FE_snapped, NE_snapped = self.snap_endpoints_to_road(row, ors_base_url=ors_base_url,
                                                               lat_fe_column=lat_fe_column, lon_fe_column=lon_fe_column,
                                                               lat_ne_column=lat_ne_column, lon_ne_column=lon_ne_column)

            # Step 2: Find optimal hybrid route using multiple approaches
            print("  Trying standard hybrid approach...")
            hybrid_route_standard = self.find_optimal_hybrid_route(FE_snapped, NE_snapped, G, spatial_tree, node_id_list, fo_buffer, ors_base_url)

            print("  Trying progressive hybrid approach...")
            hybrid_route_progressive = self.find_progressive_hybrid_route(FE_snapped, NE_snapped, G, spatial_tree, node_id_list, ors_base_url)

            # Select the best route from both approaches
            hybrid_route = None
            if hybrid_route_standard and hybrid_route_progressive:
                if hybrid_route_standard['total_new_build_distance'] <= hybrid_route_progressive['total_new_build_distance']:
                    hybrid_route = hybrid_route_standard
                    print(f"  Selected standard approach: {hybrid_route_standard['total_new_build_distance']:.0f}m vs {hybrid_route_progressive['total_new_build_distance']:.0f}m")
                else:
                    hybrid_route = hybrid_route_progressive
                    print(f"  Selected progressive approach: {hybrid_route_progressive['total_new_build_distance']:.0f}m vs {hybrid_route_standard['total_new_build_distance']:.0f}m")
            elif hybrid_route_standard:
                hybrid_route = hybrid_route_standard
                print("  Using standard approach (progressive failed)")
            elif hybrid_route_progressive:
                hybrid_route = hybrid_route_progressive
                print("  Using progressive approach (standard failed)")

            if hybrid_route is None:
                print(f"  -> No route found for request {index + 1}")
                return None

            # Step 3: Create GeoDataFrame from hybrid route
            result_gdf = self.create_hybrid_route_gdf(hybrid_route, row)

            if result_gdf.empty:
                print(f"  -> Failed to create route GDF for request {index + 1}")
                return None

            # Step 4: Print optimization results
            if hybrid_route.get('is_direct', False):
                print(f"  -> Direct route: {hybrid_route['total_new_build_distance']:.0f}m new-build")
            else:
                approach_type = hybrid_route.get('approach', 'standard')
                if 'improvement_pct' in hybrid_route:
                    print(f"  -> {approach_type.title()} hybrid route: {hybrid_route['total_new_build_distance']:.0f}m new-build ({hybrid_route['improvement_pct']:.1f}% improvement), {hybrid_route['total_nx_distance']:.0f}m existing fiber")
                else:
                    print(f"  -> {approach_type.title()} hybrid route: {hybrid_route['total_new_build_distance']:.0f}m new-build, {hybrid_route['total_nx_distance']:.0f}m existing fiber")

            print(f"  -> Request {index + 1} completed successfully")
            return result_gdf

        except Exception as e:
            print(f"  -> Error processing request: {str(e)}")
            return None

    def process_csv_data(self,
                        input_file_path: str,
                        column_mapping: Dict[str, str] = None,
                        output_folder: str = "output",
                        lat_fe_column: str = 'Lat_FE',
                        lon_fe_column: str = 'Lon_FE',
                        lat_ne_column: str = 'Lat_NE',
                        lon_ne_column: str = 'Lon_NE',
                        fe_name_column: str = 'Far End (FE)',
                        ne_name_column: str = 'Near End (NE)',
                        pulau: str = "Sulawesi",
                        graph_path: str = "./data/sulawesi_graph.graphml",
                        fo_base_path: Optional[str] = None,
                        pop_path: Optional[str] = None,
                        ors_base_url: str = "http://localhost:6080") -> Dict[str, Any]:
        """Main processing function with full lastmile pipeline"""

        try:
            print("Starting full lastmile processing...")
            request_id = str(uuid.uuid4())
            os.makedirs(output_folder, exist_ok=True)

            # Create default column mapping if not provided
            if column_mapping is None:
                column_mapping = {
                    'lat_fe': lat_fe_column,
                    'lon_fe': lon_fe_column,
                    'lat_ne': lat_ne_column,
                    'lon_ne': lon_ne_column,
                    'fe_name': fe_name_column,
                    'ne_name': ne_name_column
                }

            # Load and prepare data
            print("Loading and preparing data...")
            lm = self.load_and_prepare_data(input_file_path, column_mapping)

            # Load base data
            fo, fo_buffer, pop = self.load_base_data(pulau, fo_base_path, pop_path)
            if fo is None:
                raise Exception("Failed to load base data")

            # Load graph
            G = nx.read_graphml(graph_path)

            # Build spatial index
            print("Building spatial index...")
            node_coordinates = self.extract_node_coordinates(G)
            spatial_tree, node_id_list = self.build_spatial_index(node_coordinates)

            print(f"Loaded {len(lm)} requests and graph with {G.number_of_nodes()} nodes")

            # Set up directions URL
            directions_url = f"{ors_base_url}/ors/v2/directions/driving-car"

            # Process each request
            results = []
            for index, row in lm.iterrows():
                try:
                    result = self.process_single_request(row, index, G, fo_buffer, pop, spatial_tree, node_id_list,
                                              ors_base_url=ors_base_url, directions_url=directions_url,
                                              fe_name_column=fe_name_column, ne_name_column=ne_name_column,
                                              lat_fe_column=lat_fe_column, lon_fe_column=lon_fe_column,
                                              lat_ne_column=lat_ne_column, lon_ne_column=lon_ne_column)
                    if result is not None and not result.empty:
                        results.append(result)
                        print(f"✓ Request {index + 1} completed successfully")
                    else:
                        print(f"✗ Request {index + 1} failed or returned empty result")
                except Exception as e:
                    print(f"✗ Request {index + 1} failed: {str(e)}")
                    continue

            print(f"Processing completed. {len(results)} out of {len(lm)} requests processed successfully.")

            if not results:
                raise Exception("No requests processed successfully")

            # Combine results
            print("Combining results...")
            combined_gdf = pd.concat(results, ignore_index=True)
            combined_gdf = combined_gdf.set_geometry('geometry')
            combined_gdf = combined_gdf.to_crs('EPSG:4326')

            # Dissolve by type and add labels
            print("Dissolving linestrings by type...")
            dissolved_gdf = self.dissolve_by_type_with_labels(combined_gdf)

            # Generate output files
            output_files = []

            # Save detailed result as parquet
            detailed_output_path = os.path.join(output_folder, f"lastmile_detailed_{request_id}.parquet")
            combined_gdf.to_parquet(detailed_output_path)
            output_files.append(detailed_output_path)

            # Save dissolved result
            dissolved_output_path = os.path.join(output_folder, f"lastmile_dissolved_{request_id}.parquet")
            dissolved_gdf.to_parquet(dissolved_output_path)
            output_files.append(dissolved_output_path)

            dissolved_gpkg_output_path = os.path.join(output_folder, f"lastmile_dissolved_{request_id}.gpkg")
            dissolved_gdf.to_file(dissolved_gpkg_output_path, driver='GPKG')
            output_files.append(dissolved_gpkg_output_path)

            # Save summary CSV
            dissolved_csv_output_path = os.path.join(output_folder, f"lastmile_dissolved_summary_{request_id}.csv")
            dissolved_summary_df = dissolved_gdf.drop(columns=['geometry'])
            dissolved_summary_df.to_csv(dissolved_csv_output_path, index=False)
            output_files.append(dissolved_csv_output_path)

            # Create KML outputs
            print("Creating KML outputs...")
            try:
                kml_files = self.create_kml_output(dissolved_gdf, output_folder, request_id, lm,
                                                 fe_name_column, ne_name_column,
                                                 lat_fe_column, lon_fe_column,
                                                 lat_ne_column, lon_ne_column)
                output_files.extend(kml_files)
            except Exception as e:
                print(f"Warning: KML creation failed: {str(e)}")

            # Calculate analysis summary
            total_distance = dissolved_gdf['total_distance_m'].sum()
            overlapped_distance = dissolved_gdf[dissolved_gdf['type'] == 'nx']['total_distance_m'].sum()
            new_build_distance = dissolved_gdf[dissolved_gdf['type'] == 'ors']['total_distance_m'].sum()

            analysis_summary = {
                "request_id": request_id,
                "processing_timestamp": datetime.now().isoformat(),
                "total_requests": len(lm),
                "processed_requests": len(results),
                "total_segments_before_dissolve": len(combined_gdf),
                "total_groups_after_dissolve": len(dissolved_gdf),
                "total_distance_m": round(total_distance, 2),
                "overlapped_distance_m": round(overlapped_distance, 2),
                "new_build_distance_m": round(new_build_distance, 2),
                "overlapped_percentage": round((overlapped_distance / total_distance * 100) if total_distance > 0 else 0, 2),
                "new_build_percentage": round((new_build_distance / total_distance * 100) if total_distance > 0 else 0, 2),
                "dissolved_groups": [
                    {
                        "label": row['label'],
                        "type": row['type'],
                        "fe_name": row.get(fe_name_column, "N/A"),
                        "ne_name": row.get(ne_name_column, "N/A"),
                        "total_distance_m": round(row['total_distance_m'], 2),
                        "segment_count": row['segment_count']
                    }
                    for _, row in dissolved_gdf.iterrows()
                ],
            }

            # Save analysis summary
            analysis_path = os.path.join(output_folder, f"analysis_summary_{request_id}.json")
            with open(analysis_path, 'w') as f:
                json.dump(analysis_summary, f, indent=2)
            output_files.append(analysis_path)

            print(f"Processing completed successfully. Output files: {len(output_files)}")

            return {
                "success": True,
                "request_id": request_id,
                "message": "Processing completed successfully",
                "analysis_summary": analysis_summary,
                "_output_files": output_files  # Keep for internal use only
            }

        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            print(error_msg)
            return {
                "success": False,
                "request_id": request_id if 'request_id' in locals() else "unknown",
                "message": error_msg,
                "analysis_summary": None,
                "_output_files": []  # Keep for internal use only
            }


# Create global processor instance
processor = LastMileProcessor()

def process_lastmile_data(input_file_path: str,
                         output_folder: str = "output",
                         lat_fe_column: str = 'Lat_FE',
                         lon_fe_column: str = 'Lon_FE',
                         lat_ne_column: str = 'Lat_NE',
                         lon_ne_column: str = 'Lon_NE',
                         fe_name_column: str = 'Far End (FE)',
                         ne_name_column: str = 'Near End (NE)',
                         pulau: str = "Sulawesi",
                         ors_base_url: str = "http://localhost:6080") -> Dict[str, Any]:
    """Convenience function to process lastmile data with default parameters"""
    return processor.process_csv_data(
        input_file_path=input_file_path,
        output_folder=output_folder,
        lat_fe_column=lat_fe_column,
        lon_fe_column=lon_fe_column,
        lat_ne_column=lat_ne_column,
        lon_ne_column=lon_ne_column,
        fe_name_column=fe_name_column,
        ne_name_column=ne_name_column,
        pulau=pulau,
        ors_base_url=ors_base_url
    )