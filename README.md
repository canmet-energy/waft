# WAFT (Wind-farm Array Formation Tool)
This tool was developed to rapidly generate realistic wind farm layouts based on user-defined spacing parameters and project-specific constraints, including geospatial boundaries, prevailing wind direction, interconnection point location, and other configurable factors. The resulting layouts can be used as inputs for a variety of technical, environmental, and feasibility studies, supporting early-stage research prior to the definition of wind lease areas. Its flexible, geospatially driven approach enables application in any region worldwide. 

## Prerequisites
This code requires the following libraries:
- python (3.12 recommended)
- numpy
- matplotlib
- pandas
- geopandas
- shapely

## Code Logic
The core of this code is heavily geometry-based and operates in the following manner:
1. Imports the Wind Energy Area (WEA) boundary from the selected WEA shapefile
2. Creates a larger rectangular shaped boundary where each edge is pushed back by half of the longest edge to edge distance of WEA
    - This ensures turbine points can cover the entire WEA after any rotations based on prevailing wind direction
3. Generate a lateral grid of turbine points filling the entire larger boundary
4. Stagger every other column by half of the perpendicular spacing (if the stagger option is enabled)
5. Rotate array of turbine points to line up the parallel spacing with the prevailing wind direction
6. Remove all points outside of the WEA
7. Determine which corner to start at for slicing through the entire area based on the direction to the interconnection point
    - The slicing process will be parallel to the prevailing wind direction and move along a cutting axis (perpendicular to the prevailing wind)
    - The slicing point will move along the cutting axis (creating larger areas each time) until the target wind farm capacity has been meet or exceeded or there is not enough space
8. If more than one farm is being generated, a defined buffer distance will be applied and the slicing will start again from that new point and continue until the next farm is created or there is not enough space
9. Any farms with an excess number of turbines will have turbines removed based on the direction to the interconnection point
    - Turbines farthest away will be removed so that turbines closer to the interconnection point will be prioritized

## Usage	
This code was designed to be easily run within an Integrated Development Environment (IDE). User inputs are located at the top of the code, just under the library import section. The inputs are as follows:

### Turbine parameters
- **turbine_name:** Name of the wind turbine that turbine_cap and turbine_D correspond to
- **turbine_cap:** Max capacity of the selected wind turbine in MW
- **turbine_D:** Rotor diameter of the selected wind turbine in m

### WEA parameters
- **wind_dir:** The direction the prevailing wind is coming from in degrees (will decide how parcels are cut)
- **interconnect_dir:** The direction to the interconnection point in degrees (will prioritize turbines that are closer to this direction if the layout exceeds the target)
- **WEA_location:** Location of Wind Energy Area (WEA) shapefile
- **WEA_name:** Used for file naming
- **WEA_depth:** Indicates the maximum depth within the input WEA and is used for file naming and scenario categorizing. Used for only for offshore wind farm layouts. Setting as None will remove it from file naming.

### Layout parameters
- **parallel_D:** Number of turbine diameters each farm row (parallel to prevailing wind direction) will be spaced (can enter multiple in list format [x, y, z, ...])
- **perpendicular_D:** Number of turbine diameters each farm column (perpendicular to prevailing wind direction) will be spaced (can enter multiple in list format [x, y, z, ...])
- **stagger:** Toggle to stagger every other row (staggering will be equal to half the perpendicular spacing)

### Farm parameters
- **farm_max_cap:** Max capacity of each wind farm in MW (will be rounded up to nearest full turbine). The size of this list will decide the number of farms (can enter multiple in list format [x, y, z, ...])
- **buffer:** Buffer distance between wind farms in m

### Output parameters
- **save_farm_characteristics:** Toggle to save calculated wind farm characteristics
- **farm_characteristics_location:** Location to save farm characteristics (will create if it does not exist)
- **save_layout_fig:** Toggle to save figure
- **layout_fig_location:** Location to save layout figure (will create if it does not exist)
- **save_turbine_shapefile:** Toggle to save turbine layout as a shapefile
- **turbine_shapefile_location:** Location to save turbine layout shapefile (will create if it does not exist)

### Optional
- **flip_starting_corner:** Toggle to flip the starting corner for the parcelling process (will be more prevelent closer to shore angles of 45, 135, 225, and 335)

### Plot annotations
Prewritten plot annotations of some additional information can be found starting at line 509 and are by default commented out. If you wish to use these, you will likely need to update the positioning values.

## Example
An Example folder is included that has been created using the default user inputs. This folder contains one input folder:
- **WEA Input:** Folder containing the example WEA shapefiles for input into the code

And three output folders:
- **Farm Characteristics:** Folder containing csv outputs of two example scenarios
- **Layout Figures:** Folder containing .png wind farm layout figures of the two example scenarios
- **Turbine Layout Shapefiles:** Folder containing a geopackage output of the two example scenarios

## Copyright and License
Copyright 2026 CanmetENERGY-Ottawa

The software contained in this repository is distributed under the terms of the BSD 3-Clause License. Refer to the LICENSE file for complete details.

© His Majesty the King in Right of Canada, as represented by the Minister of Natural Resources, 2026. 
