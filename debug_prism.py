#!/usr/bin/env python3
"""
Debug script to examine the polygonal prism creation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import trimesh
import numpy as np
from shapely.geometry import Polygon as ShapelyPolygon
from trimesh.creation import extrude_polygon

def debug_prism():
    """Debug the polygonal prism creation."""
    print("Debugging polygonal prism creation...")
    
    # Test parameters
    height_mm = 50.0
    polygonal_cutout_radius_mm = 5.0
    
    # Calculate the circumscribed radius from the inscribed radius
    circumscribed_radius = polygonal_cutout_radius_mm / 0.866
    
    # Create the 6-point polygon vertices
    angles = np.linspace(0, 2*np.pi, 6, endpoint=False)
    vertices_2d = []
    for angle in angles:
        x = circumscribed_radius * np.cos(angle)
        y = circumscribed_radius * np.sin(angle)
        vertices_2d.append([x, y])
    
    print(f"Polygon vertices: {vertices_2d}")
    print(f"Circumscribed radius: {circumscribed_radius:.3f}mm")
    
    # Create the polygonal prism by extruding the polygon along the Z-axis
    prism_height = height_mm + 2.0  # Add 1mm on each end
    
    # Create the polygon using shapely
    polygon = ShapelyPolygon(vertices_2d)
    print(f"Polygon bounds: {polygon.bounds}")
    print(f"Polygon area: {polygon.area:.3f}")
    
    # Extrude the polygon to create the prism
    cutout_prism = extrude_polygon(polygon, height=prism_height)
    
    print(f"Prism bounds before positioning: {cutout_prism.bounds}")
    print(f"Prism center: {cutout_prism.center_mass}")
    
    # Position the prism to cut through the center of the cylinder
    cutout_prism.apply_translation([0, 0, -prism_height/2 + height_mm/2])
    
    print(f"Prism bounds after positioning: {cutout_prism.bounds}")
    print(f"Prism center after positioning: {cutout_prism.center_mass}")
    
    # Check that it spans the full cylinder height
    expected_z_min = -height_mm/2 - 1.0  # Should go 1mm below
    expected_z_max = height_mm/2 + 1.0   # Should go 1mm above
    print(f"Expected Z bounds: [{expected_z_min}, {expected_z_max}]")
    
    # Save the prism for inspection
    cutout_prism.export("debug_prism.stl")
    print("Saved prism to debug_prism.stl")
    
    return cutout_prism

if __name__ == "__main__":
    prism = debug_prism()
