#!/usr/bin/env python3
"""
Test script for hemispherical counter plate generation.
This script tests the build_counter_plate_hemispheres function independently.
"""

import sys
import os

# Add the current directory to the path so we can import from vercel_backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vercel_backend import CardSettings, build_counter_plate_hemispheres
import trimesh
import numpy as np

def test_hemispherical_counter_plate():
    """Test the hemispherical counter plate generation"""
    print("Testing hemispherical counter plate generation...")
    
    # Create test settings
    settings = CardSettings(
        card_width=90,
        card_height=52,
        card_thickness=2.0,
        grid_columns=13,
        grid_rows=4,
        cell_spacing=7.0,
        line_spacing=10.0,
        dot_spacing=2.5,
        dot_base_diameter=1.8,
        emboss_dot_base_diameter_mm=1.8,
        plate_thickness_mm=2.0,
        epsilon_mm=0.001
    )
    
    print(f"Settings:")
    print(f"  Grid: {settings.grid_columns}x{settings.grid_rows}")
    print(f"  Hemisphere radius: {settings.hemisphere_radius:.3f}mm")
    print(f"  Plate thickness: {settings.plate_thickness:.3f}mm")
    print(f"  Expected recesses: {settings.grid_columns * settings.grid_rows * 6}")
    
    try:
        # Generate the hemispherical counter plate
        print("\nGenerating hemispherical counter plate...")
        mesh = build_counter_plate_hemispheres(settings)
        
        print(f"\nMesh generated successfully!")
        print(f"  Bounds: {mesh.bounds}")
        print(f"  Volume: {mesh.volume:.4f}")
        print(f"  Is watertight: {mesh.is_watertight}")
        print(f"  Vertices: {len(mesh.vertices)}")
        print(f"  Faces: {len(mesh.faces)}")
        
        # Calculate expected volume removed
        expected_recesses = settings.grid_columns * settings.grid_rows * 6
        hemisphere_volume = (4/3 * np.pi * settings.hemisphere_radius**3) / 2  # Half sphere
        expected_volume_removed = expected_recesses * hemisphere_volume
        
        print(f"\nExpected properties:")
        print(f"  Total recesses: {expected_recesses}")
        print(f"  Hemisphere volume: {hemisphere_volume:.6f}")
        print(f"  Expected volume removed: {expected_volume_removed:.4f}")
        
        # Export to STL for inspection
        output_file = "test_hemispherical_counter_plate.stl"
        mesh.export(output_file)
        print(f"\nMesh exported to: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_hemispherical_counter_plate()
    if success:
        print("\n✓ Test completed successfully!")
    else:
        print("\n✗ Test failed!")
        sys.exit(1)
