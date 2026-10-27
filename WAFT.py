# WAFT: Wind-farm Array Formation Tool
# Owner: CanmetENERGY-Ottawa
# © His Majesty the King in Right of Canada, as represented by the Minister of Natural Resources, 2026. 

# Generate wind turbine layouts based on user defined parameters

import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPolygon, LineString
from shapely.affinity import rotate
from shapely.ops import unary_union


#####################################################################################################################################################################################################################
## User-defined parameters
# Turbine parameters
turbine_name = 'Turbine A' # Wind turbine that turbine_cap and turbine_D correspond to
turbine_cap = 10 # Max capacity of the selected wind turbine in MW
turbine_D = 100 # Rotor diameter of the selected wind turbine in m

# WEA parameters
wind_dir = 200 # The direction the prevailing wind is coming from in degrees (will decide how parcels are cut)
interconnect_dir = 300 # The direction to the interconnection point in degrees (will prioritize turbines that are closer to the interconnection point)
WEA_location = r'Example/WEA Input/Test WEA.shp' # Location of Wind Energy Area (WEA) shapefile
WEA_name = 'Test WEA' # For file naming
WEA_depth = '-30m' # For file naming of offshore wind farms (indicate maximum depth e.g. '-30m' for offshore, or None for onshore)

# Layout parameters
parallel_D = [2, 6]  # Number of turbine diameters each farm row (parallel to prevailing wind direction) will be spaced (can enter multiple in list format [x, y, z, ...])
perpendicular_D = [2, 4] # Number of turbine diameters each farm column (perpendicular to prevailing wind direction) will be spaced
stagger = 'Yes' #Yes to stagger every other row, No to keep a uniform grid

# Farm parameters
farm_max_cap = [2000, 2500, 3000] # Max capacity of each wind farm in MW (will be rounded up to nearest full turbine). The size of this list will decide the number of farms (can enter multiple in list format [x, y, z, ...])
buffer = 5000 # Buffer between wind farms in m

# Output parameters
save_farm_characteristics = 'Yes' # Yes to save calculated wind farm characteristics, No to not save them
farm_characteristics_location = r'Example/Farm Characteristics/' # Location to save farm characteristics (will create if it does not exist)
save_layout_fig = 'Yes' # Yes to save figure, No to not save figure
layout_fig_location = r'Example/Layout Figures/' # Location to save layout figure (will create if it does not exist)
save_turbine_shapefile = 'Yes' # Yes to save turbine layout as shapefile, No to not save turbine layout as shapefile
turbine_shapefile_location = r'Example/Turbine Layout Shapefiles/' # Location to save turbine layout shapefile (will create if it does not exist)

# Optional
flip_starting_corner = 'No' # Yes to flip the starting corner for parcelling will be more prevelent closer to interconnect_dir angles of 45, 135, 225, and 335

#############################################################################################################################################
## Main code
def NRCan_WAFT(
    turbine_name: str,
    turbine_cap: float,
    turbine_D: float,
    wind_dir: float,
    interconnect_dir: float,
    parallel_D: list[float],
    perpendicular_D: list[float],
    stagger: str,
    farm_max_cap: list[float],
    buffer: float,
    WEA_location: str,
    WEA_name: str,
    save_layout_fig: str,
    layout_fig_location: str,
    save_turbine_shapefile: str,
    turbine_shapefile_location: str,
    flip_starting_corner: str,
    save_farm_characteristics: str,
    farm_characteristics_location: str,
    WEA_depth: str | None = None,
):
    
    # Create depth suffix for use in filenames and titles
    depth_suffix = f"_{WEA_depth}" if WEA_depth else ""
    depth_title = f" at {WEA_depth}" if WEA_depth else ""
    
    ## Import and convert WEA Bounds from shapefile to xy coordinates
    # Read shapefile
    gdf = gpd.read_file(WEA_location)
    gdf = gdf[gdf.geometry.notnull()]
    
    # Merge all geometries (handles holes & multipolygons automatically)
    WEA_coords = unary_union(gdf.geometry.values)

    # Lat/lon bounds for projection reference
    WEA_minlon, WEA_minlat, WEA_maxlon, WEA_maxlat = WEA_coords.bounds
    coord_mins = np.array([WEA_minlon, WEA_minlat])

    # Convert each polygon to x/y and store as shapely Polygon
    projected_polygons = []

    def project_polygon(poly):
        # Exterior
        ext = np.array(poly.exterior.coords)
        ext_temp = ext - coord_mins
    
        ext_xy = np.zeros_like(ext_temp)
        ext_xy[:, 0] = ext_temp[:, 0] * 111111 * np.cos(np.radians(ext[:, 1]))
        ext_xy[:, 1] = ext_temp[:, 1] * 111111
    
        # Holes
        hole_xy_list = []
        for hole in poly.interiors:
            hole_arr = np.array(hole.coords)
            hole_temp = hole_arr - coord_mins
    
            hole_xy = np.zeros_like(hole_temp)
            hole_xy[:, 0] = hole_temp[:, 0] * 111111 * np.cos(np.radians(hole_arr[:, 1]))
            hole_xy[:, 1] = hole_temp[:, 1] * 111111
    
            hole_xy_list.append(hole_xy)
    
        return Polygon(ext_xy, holes=hole_xy_list if hole_xy_list else None)
    
    if isinstance(WEA_coords, Polygon):
        projected_polygons.append(project_polygon(WEA_coords))
    
    elif isinstance(WEA_coords, MultiPolygon):
        for poly in WEA_coords.geoms:
            projected_polygons.append(project_polygon(poly))

    # Merge xy polygons if needed
    if len(projected_polygons) == 1:
        WEA_xy = projected_polygons[0]
    else:
        WEA_xy = unary_union(projected_polygons)
    WEA_minx, WEA_miny, WEA_maxx, WEA_maxy = WEA_xy.bounds
    
    # Calculate WEA area
    WEA_area = WEA_xy.area / 1e6
    
    # Define a larger set of bounds (external to WEA area) where each boundary edge is pushed back by half the largest edge to edge length of the WEA area (this ensures turbines points cover the entire WEA area after rotation)
    boundx_diff = WEA_maxx - WEA_minx
    boundy_diff = WEA_maxy - WEA_miny
    bound_diff = max(boundx_diff, boundy_diff)
    
    # Redefine boundary variables
    WEA_minx2 = WEA_minx - (bound_diff /2)
    WEA_miny2 = WEA_miny - (bound_diff /2)
    WEA_maxx2 = WEA_maxx + (bound_diff /2)
    WEA_maxy2 = WEA_maxy + (bound_diff /2)
    
    ############################################################################################################################
    
    ## Generate wind farm layouts
    # Initialize list to store farm characteristics for each scenario
    farm_characteristics_data = []
    
    # Develop initial lateral grid
    for spacing in range(0, len(perpendicular_D)):
        print('Generating wind farm layout ', spacing + 1, ' of ', len(perpendicular_D), '...')
    
        perpendicular_spacing = perpendicular_D[spacing] * turbine_D # x spacing in m
        parallel_spacing = parallel_D[spacing] * turbine_D # y spacing in m
        WEA_x = np.arange(WEA_minx2, WEA_maxx2, parallel_spacing)
        WEA_y = np.arange(WEA_miny2, WEA_maxy2, perpendicular_spacing)
        
        if stagger == 'Yes': # Shift every other column by half the perpendicular spacing
            grid_points = []
            for j, x in enumerate(WEA_x):
                y_offset = perpendicular_spacing / 2 if j % 2 else 0
                for y in WEA_y:
                    grid_points.append(Point(x, y + y_offset))
        else:
            grid_points = [Point(x, y) for x in WEA_x for y in WEA_y]
        
        # Rotate initial grid based on wind direction
        center = WEA_xy.centroid
        rotated_points = [rotate(pt, (90-wind_dir), origin=center) for pt in grid_points]
        
        # Remove points outside boundary
        if isinstance(WEA_xy, MultiPolygon):
            inside_points = [pt for pt in rotated_points if any(poly.contains(pt) or poly.touches(pt) for poly in WEA_xy.geoms)]
        else:
            inside_points = [pt for pt in rotated_points if WEA_xy.contains(pt) or WEA_xy.touches(pt)]
        
        ############################################################################################################################
        
        ## Parcel out WEA
        # Initialize parcel lists and define parameters
        accepted_parcels = []
        accepted_turbine_counts = []
        accepted_cut_lines = []
        accepted_turbines_in_parcel = []
        cut_lines=[]
        parcel_area = []
        buffer_areas = []
        previous_cut_line = None
        current_point = 0

        # Calculate number of turbines needed per farm to meet desired farm capacity
        N = []
        N = [int(np.ceil(farm_cap / turbine_cap)) for farm_cap in farm_max_cap]
        num_farms = len(farm_max_cap)
        
        # Determine which corner to start from
        NE_corner = Point(WEA_maxx, WEA_maxy)
        NW_corner = Point(WEA_minx, WEA_maxy)
        SW_corner = Point(WEA_minx, WEA_miny)
        SE_corner = Point(WEA_maxx, WEA_miny)
        cut_dir = 1
        
        if  0 <= wind_dir < 90:
            if 45 <= interconnect_dir < 225:
                current_point = SE_corner
                opposite_corner = NW_corner
                cut_dir = -1
            else:
                current_point = NW_corner
                opposite_corner = SE_corner
        
        elif 90 <= wind_dir < 180:
            if 135 <= interconnect_dir < 315:
                current_point = SW_corner
                opposite_corner = NE_corner
                cut_dir = -1
            else:
                current_point = NE_corner
                opposite_corner = SW_corner
        
        elif 180 <= wind_dir < 270:
            if 45 <= interconnect_dir < 225:
                current_point = SE_corner
                opposite_corner = NW_corner
            else:
                current_point = NW_corner
                opposite_corner = SE_corner
                cut_dir = -1
        
        elif 270 <= wind_dir < 360:
            if 135 <= interconnect_dir < 315:
                current_point = SW_corner
                opposite_corner = NE_corner
        
            else:
                current_point = NE_corner
                opposite_corner = SW_corner
                cut_dir = -1
        
        if flip_starting_corner == 'Yes':
            current_point = opposite_corner
            cut_dir = cut_dir * -1
        
        # Create perpendicular axis
        line_length = np.sqrt(((WEA_maxx2-WEA_minx2)**2)+(WEA_maxy2-WEA_miny2)**2) / 2  # meters
        cut_spacing = perpendicular_spacing / 2
        wind_dir_perp_rad = np.radians(-wind_dir)
        cutaxis_x = line_length * np.cos(wind_dir_perp_rad)
        cutaxis_y = line_length * np.sin(wind_dir_perp_rad)
        axis_vector = np.array([cutaxis_x, cutaxis_y])
        axis_unit = axis_vector / np.linalg.norm(axis_vector)
        perp_vector = np.array([-axis_unit[1], axis_unit[0]])
        
        # Generate cutting lines
        max_iterations = int(np.linalg.norm([WEA_maxx - WEA_minx, WEA_maxy - WEA_miny]) // cut_spacing)
        dx = perp_vector[0] * line_length
        dy = perp_vector[1] * line_length
        start = Point(current_point.x - dx, current_point.y - dy)
        end = Point(current_point.x + dx, current_point.y + dy)
        previous_cut_line = LineString([start, end])
        current_point = Point(
            current_point.x + axis_unit[0] * cut_spacing * cut_dir,
            current_point.y + axis_unit[1] * cut_spacing * cut_dir
        )
        
        # Move cutting line until enough turbines exist within cut parcel        
        farm_count = 0
        
        for i in range(max_iterations):
            if len(accepted_parcels) == num_farms:
                break
        
            start = Point(current_point.x - dx, current_point.y - dy)
            end = Point(current_point.x + dx, current_point.y + dy)
            current_cut_line = LineString([start, end])
            cut_lines.append(current_cut_line)
        
            if previous_cut_line:
                strip_coords = [
                    previous_cut_line.coords[0], previous_cut_line.coords[1],
                    current_cut_line.coords[1], current_cut_line.coords[0],
                    previous_cut_line.coords[0]
                ]
                strip_polygon = Polygon(strip_coords)
                parcel = strip_polygon.intersection(WEA_xy)
                turbines_in_parcel = [pt for pt in inside_points if parcel.contains(pt) or parcel.touches(pt)]
        
                if len(turbines_in_parcel) >= N[farm_count]:
        
                    # Save parcel
                    accepted_parcels.append(parcel)
                    accepted_turbine_counts.append(len(turbines_in_parcel))
                    accepted_cut_lines.append(current_cut_line)
                    accepted_turbines_in_parcel.append(turbines_in_parcel)
        
                    # Calculate area
                    parcel_area.append(parcel.area / 1e6)
        
                    # Apply buffer
                    current_point = Point(
                        current_point.x + axis_unit[0] * buffer * cut_dir,
                        current_point.y + axis_unit[1] * buffer * cut_dir
                    )
                    start = Point(current_point.x - dx, current_point.y - dy)
                    end = Point(current_point.x + dx, current_point.y + dy)
                    current_cut_line = LineString([start, end])

                    # Build buffer strip between last parcel cut and buffered cut
                    last_cut = accepted_cut_lines[-1]
                    buffer_cut = current_cut_line
                    
                    buffer_coords = [
                        last_cut.coords[0], last_cut.coords[1],
                        buffer_cut.coords[1], buffer_cut.coords[0],
                        last_cut.coords[0]
                    ]
                    
                    buffer_strip = Polygon(buffer_coords)
                    
                    # Clip to WEA
                    buffer_strip = buffer_strip.intersection(WEA_xy)
                    
                    # Store buffer area if it's not empty
                    if not buffer_strip.is_empty:
                        buffer_areas.append(buffer_strip.area / 1e6)

                    previous_cut_line = current_cut_line
                    farm_count = farm_count + 1
                    
                    continue
            
            current_point = Point(
                current_point.x + axis_unit[0] * cut_spacing * cut_dir,
                current_point.y + axis_unit[1] * cut_spacing * cut_dir
            )
        
        if len(accepted_parcels) is not num_farms:
            print('Not enough space for desired number of wind farms. Some farms may be missing for some scenarios.')
        
        # Remove turbines in excess of farm max capacity prioritizing the direction to interconnection point
        wind_farms = {}  # Dictionary to store selected points for each farm
        farm_count = 0
        
        for turbines in accepted_turbines_in_parcel:
            
            # Create array for sorting
            turbine_array = np.array([[pt.x, pt.y] for pt in turbines])
        
            # Select turbines based on their projection along the specified interconnect_dir and prioritize those closer to the interconnection point (removes turbines further away to meet defined wind farm capacity)
            interconnect_dir_rad = np.deg2rad(90-interconnect_dir)
            interconnect_vector = np.array([np.cos(interconnect_dir_rad), np.sin(interconnect_dir_rad)])
            interconnect_proj = turbine_array @ interconnect_vector
            sorted_indices = np.argsort(-interconnect_proj)
            sorted_points = [turbines[i] for i in sorted_indices]
            selected_points = sorted_points[:N[farm_count]]
        
            # Store selected points with a farm label
            farm_label = f'Farm {farm_count + 1}'
            wind_farms[farm_label] = selected_points
            farm_count = farm_count + 1

        #############################################################################################################################
        
        # Create shapefiles of turbine points
        if save_turbine_shapefile == 'Yes':
            if not os.path.exists(turbine_shapefile_location):
                os.makedirs(turbine_shapefile_location, exist_ok=True)

            t_lonlat_rows = []  # List of dict rows: Farm, Turbine, Lon, Lat
            
            for farm_label, turbines in wind_farms.items():
                turbine_idx = 1  # Restart counter for each farm
                for pt in turbines:
                    # Converting back from xy to lon/lat
                    t_lat = coord_mins[1] + (np.array(pt.y) / 111111.0)
                    t_lon = coord_mins[0] + (np.array(pt.x) / (111111.0 * np.cos(t_lat * np.pi / 180.0)))
                    # -------------------------------------------
            
                    t_lonlat_rows.append({
                        "Farm": str(farm_label),
                        "Turbine": turbine_idx,
                        "Lon": float(t_lon),
                        "Lat": float(t_lat),
                    })
                    turbine_idx += 1
            
            # Build DataFrame with desired column order
            out = pd.DataFrame(t_lonlat_rows, columns=["Farm", "Turbine", "Lon", "Lat"])
            
            # Convert to GeoDataFrame with Point geometries
            geometry = [Point(xy) for xy in zip(out['Lon'], out['Lat'])]
            gdf = gpd.GeoDataFrame(out, geometry=geometry, crs="EPSG:4326")
            
            # Save as shapefile
            shapename = (
                f"{WEA_name}{depth_suffix}_parr-{parallel_D[spacing]}_perp-{perpendicular_D[spacing]}"
                f"_wd-{wind_dir}_sd-{interconnect_dir}_buff-{buffer}_{turbine_name}_turbines.gpkg"
            )
        
            shape_file = os.path.join(turbine_shapefile_location, shapename)      
            gdf.to_file(shape_file, driver='GPKG')

        ##########################################################################################################################            
        
        ## Calculate wind farm characteristics
        farm_capacity = np.array(N) * turbine_cap
        energy_density =  np.round(15 / ((parallel_spacing /1000) * (perpendicular_spacing / 1000)), decimals=1)
        WEA_capacity = np.round(((np.sum(parcel_area)) + (np.sum(buffer_areas))) / WEA_area * 100, decimals=1)
        
        # Store scenario characteristics
        scenario_data = {
            'Parallel_Spacing_D': parallel_D[spacing],
            'Perpendicular_Spacing_D': perpendicular_D[spacing],
            'Parallel_Spacing_m': parallel_spacing,
            'Perpendicular_Spacing_m': perpendicular_spacing,
            'Wind_Direction': wind_dir,
            'interconnect_Direction': interconnect_dir,
            'Buffer_m': buffer,
            'Stagger': stagger,
            'Turbine_Name': turbine_name,
            'Turbine_Capacity_MW': turbine_cap,
            'Turbine_Diameter_m': turbine_D,
            'WEA_Name': WEA_name,
            'WEA_Depth_m': WEA_depth if WEA_depth else 'N/A',
        }
        
        # Add farm-specific data for each farm
        for farm_idx, farm_label in enumerate(wind_farms.keys()):
            scenario_data[f'Farm_{farm_idx + 1}_Turbines'] = N[farm_idx]
            scenario_data[f'Farm_{farm_idx + 1}_Capacity_MW'] = farm_capacity[farm_idx]
            scenario_data[f'Farm_{farm_idx + 1}_Area_km2'] = parcel_area[farm_idx]
        
        scenario_data['Energy_Density_MW_km2'] = energy_density
        scenario_data['WEA_Utilization_Percent'] = WEA_capacity
        scenario_data['Total_Farms'] = len(wind_farms)
        scenario_data['Total_Turbines'] = np.sum(N)
        scenario_data['Total_Capacity_MW'] = np.sum(farm_capacity)
        scenario_data['Total_Area_km2'] = np.sum(parcel_area)
        
        farm_characteristics_data.append(scenario_data)
        
        ############################################################################################################################
        
        ## Visualization
        # Define wind and interconnection direction arrows
        arrx_start, arry_start = WEA_minx, WEA_miny
        
        # Arrow length
        warrxy_len = 5000 
        sarrxy_len = 3000 
        
        # Compute end point
        wind_dir_rad =  wind_dir_perp_rad + (np.pi/2)
        warrx_end = arrx_start + warrxy_len * np.cos(wind_dir_rad)
        warry_end = arry_start + warrxy_len * np.sin(wind_dir_rad)
        sarrx_end = arrx_start + sarrxy_len * np.cos(interconnect_dir_rad)
        sarry_end = arry_start + sarrxy_len * np.sin(interconnect_dir_rad)
        
        # Plot wind farm and turbines in meters
        plt.figure(figsize=(10, 10))
        fig = plt.gcf()
        if WEA_xy.geom_type == 'Polygon':
            # Single polygon
            x, y = WEA_xy.exterior.xy
            plt.plot(x, y, color='black', label='WEA Boundary')
            # Plot holes if any
            for interior in WEA_xy.interiors:
                ix, iy = interior.xy
                plt.plot(ix, iy, color='black')
        else:
            # MultiPolygon
            for i, poly in enumerate(WEA_xy.geoms):
                x, y = poly.exterior.xy
                label = 'WEA Boundary' if i == 0 else None
                plt.plot(x, y, color='black', label=label)
                # Plot holes
                for interior in poly.interiors:
                    ix, iy = interior.xy
                    plt.plot(ix, iy, color='black')
        
        for parcel in accepted_parcels:
            if isinstance(parcel, Polygon):
                x, y = parcel.exterior.xy
                plt.plot(x, y, color='green')
        
            elif isinstance(parcel, MultiPolygon):
                for poly in parcel.geoms:
                    x, y = poly.exterior.xy
                    plt.plot(x, y, color='green')
        
        for farm_name, points in wind_farms.items():
            x = [pt.x for pt in points]
            y = [pt.y for pt in points]
            plt.scatter(x, y, label=farm_name)
        
        plt.arrow(arrx_start, arry_start, warrx_end - arrx_start, warry_end - arry_start,
                head_width=1000, head_length=1000, fc='blue', ec='blue')
        plt.plot([], [], color='blue', label='Wind Direction')  # Invisible line for legend
        
        plt.arrow(arrx_start, arry_start, sarrx_end - arrx_start, sarry_end - arry_start,
                head_width=1000, head_length=1000, fc='red', ec='red')
        plt.plot([], [], color='red', label='Interconnection Direction')  # Invisible line for legend
        plt.axis('equal')
        plt.title(f'Wind farm layout for {WEA_name}{depth_title}')
        plt.xlabel('x (m)')
        plt.ylabel('y (m)')
        plt.legend()

        # Text annotations for wind farm layout
        # plt.text(0.66, 0.84, 'Wind Direction: ' + str(wind_dir) + '°', transform=fig.transFigure, fontsize=9,)
        # plt.text(0.66, 0.82, 'Interconnection Direction: ' + str(interconnect_dir) + '°', transform=fig.transFigure, fontsize=9,)
        # plt.text(0.66, 0.80, 'Parallel Spacing: ' + str(parallel_D[spacing]) + 'D', transform=fig.transFigure, fontsize=9,)
        # plt.text(0.66, 0.78, 'Perpendicular Spacing: ' + str(perpendicular_D[spacing]) + 'D', transform=fig.transFigure, fontsize=9,)
        # plt.text(0.66, 0.76, 'Farm 1: ' + str(N[0]) + ' turbines (' + str(farm_capacity[0]) + ' MW)', transform=fig.transFigure, fontsize=9,)
        # plt.text(0.66, 0.74, 'Farm 1 energy density: ' + str(energy_density) + ' MW/km\N{SUPERSCRIPT TWO}', transform=fig.transFigure, fontsize=9,)
        # plt.text(0.66, 0.72, 'Farm 2: ' + str(N[1]) + ' turbines (' + str(farm_capacity[1]) + ' MW)', transform=fig.transFigure, fontsize=9,)
        # plt.text(0.66, 0.70, 'Farm 2 energy density: ' + str(energy_density) + ' MW/km\N{SUPERSCRIPT TWO}', transform=fig.transFigure, fontsize=9,)
        # plt.text(0.66, 0.68, 'Farm(s) take up ' + str(WEA_capacity) + '% of WEA area', transform=fig.transFigure, fontsize=9,)
        
        if farm_count > 1:
            fig_name = (f"{WEA_name}{depth_suffix}_parr-{parallel_D[spacing]}_perp-{perpendicular_D[spacing]}_wd-{wind_dir}"
            f"_buffer-{buffer}.png")
        else:
            fig_name = f"{WEA_name}{depth_suffix}_parr-{parallel_D[spacing]}_perp-{perpendicular_D[spacing]}_wd-{wind_dir}.png"
                
        if save_layout_fig == 'Yes':
            if not os.path.exists(layout_fig_location):
                os.makedirs(layout_fig_location, exist_ok=True)
            fig_file = os.path.join(layout_fig_location, fig_name)
            plt.savefig(fig_file, bbox_inches='tight')
    
    ## Save farm characteristics to CSV if requested
    if save_farm_characteristics == 'Yes' and farm_characteristics_data:
        if not os.path.exists(farm_characteristics_location):
            os.makedirs(farm_characteristics_location, exist_ok=True)
        
        # Create DataFrame from collected data
        df_characteristics = pd.DataFrame(farm_characteristics_data)
        
        # Generate filename
        csv_filename = f"{WEA_name}_farm_characteristics.csv"
        csv_file = os.path.join(farm_characteristics_location, csv_filename)
        
        # Check if file already exists
        if os.path.exists(csv_file):
            print(f"\nFile '{csv_filename}' already exists in {farm_characteristics_location}")
            user_choice = input("Do you want to (1) overwrite the file or (2) merge with existing data? Enter 1 or 2: ").strip()
            
            if user_choice == '2':
                # Merge with existing file
                existing_df = pd.read_csv(csv_file)
                df_characteristics = pd.concat([existing_df, df_characteristics], ignore_index=True)
                print("New results merged with existing data.")
            elif user_choice == '1':
                print("Existing file will be overwritten.")
            else:
                print("Invalid choice. File not saved.")
                return
        
        # Save to CSV
        df_characteristics.to_csv(csv_file, index=False)

    # Indicate where files are saved to if the corresponding save options are enabled
    if save_layout_fig == 'Yes':
        print(f"Layout figures saved to: {layout_fig_location}")
    if save_turbine_shapefile == 'Yes':
        print(f"Turbine shapefiles saved to: {turbine_shapefile_location}")
    if save_farm_characteristics == 'Yes':
        print(f"Farm characteristics saved to: {farm_characteristics_location}")

NRCan_WAFT(turbine_name, turbine_cap, turbine_D, wind_dir, interconnect_dir, parallel_D, perpendicular_D, stagger, farm_max_cap, buffer, WEA_location, 
           WEA_name, save_layout_fig, layout_fig_location, save_turbine_shapefile, turbine_shapefile_location, flip_starting_corner, save_farm_characteristics, farm_characteristics_location, WEA_depth)
