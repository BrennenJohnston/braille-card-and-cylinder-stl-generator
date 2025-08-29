#!/usr/bin/env python3
"""
Debug script to understand the polygonal cutout positioning.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend import create_cylinder_shell
import trimesh
import numpy as np

def debug_cutout():
    """Debug the cutout positioning."""
    print("Debugging polygonal cutout positioning...")
    
    # Test parameters
    diameter = 30.0  # mm
    height = 50.0    # mm
    cutout_radius = 5.0  # mm
    
    print(f"Creating cylinder: diameter={diameter}mm, height={height}mm, cutout_radius={cutout_radius}mm")
    
    # Create cylinder with cutout
    cylinder_mesh = create_cylinder_shell(diameter, height, cutout_radius)
    
    print(f"Cylinder bounds: {cylinder_mesh.bounds}")
    print(f"Cylinder center: {cylinder_mesh.center_mass}")
    print(f"Expected Z bounds: [{-height/2}, {height/2}]")
    
    # Check if the cutout goes through the entire height
    vertices = cylinder_mesh.vertices
    z_min = vertices[:, 2].min()
    z_max = vertices[:, 2].max()
    
    print(f"Actual Z bounds: [{z_min:.3f}, {z_max:.3f}]")
    print(f"Cutout extent: {z_max - z_min:.3f}mm (should be ~{height}mm)")
    
    # Check if there are vertices at the cutout center
    center_vertices = vertices[np.abs(vertices[:, 0]) < 1.0]  # Vertices near X=0
    center_vertices = center_vertices[np.abs(center_vertices[:, 1]) < 1.0]  # Vertices near Y=0
    
    print(f"Vertices near center (X,Y ≈ 0): {len(center_vertices)}")
    if len(center_vertices) > 0:
        print(f"Center vertices Z range: [{center_vertices[:, 2].min():.3f}, {center_vertices[:, 2].max():.3f}]")
    
    return cylinder_mesh

if __name__ == "__main__":
    mesh = debug_cutout()
    print(f"\nSaving test mesh to debug_cylinder.stl...")
    mesh.export("debug_cylinder.stl")
    print("Done!")
