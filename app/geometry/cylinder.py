"""
Cylinder geometry generation.

This module handles generation of cylindrical braille surfaces, including
shell creation, dot mapping, and recess operations.
"""

import numpy as np


def _compute_cylinder_frame(x_arc: float, cylinder_diameter_mm: float, seam_offset_deg: float = 0.0):
    """
    Compute local orthonormal frame and geometry parameters for a point on a
    cylinder given arc-length position and seam offset.
    Returns (r_hat, t_hat, z_hat, radius, circumference, theta).
    """
    radius = cylinder_diameter_mm / 2.0
    circumference = np.pi * cylinder_diameter_mm
    theta = (x_arc / circumference) * 2.0 * np.pi + np.radians(seam_offset_deg)
    r_hat = np.array([np.cos(theta), np.sin(theta), 0.0])
    t_hat = np.array([-np.sin(theta), np.cos(theta), 0.0])
    z_hat = np.array([0.0, 0.0, 1.0])
    return r_hat, t_hat, z_hat, radius, circumference, theta


def cylindrical_transform(x, y, z, cylinder_diameter_mm, seam_offset_deg=0):
    """
    Transform planar coordinates to cylindrical coordinates.
    x -> theta (angle around cylinder)
    y -> z (height on cylinder)
    z -> radial offset from cylinder surface
    """
    radius = cylinder_diameter_mm / 2
    circumference = np.pi * cylinder_diameter_mm

    # Convert x position to angle
    theta = (x / circumference) * 2 * np.pi + np.radians(seam_offset_deg)

    # Calculate cylindrical coordinates
    cyl_x = radius * np.cos(theta)
    cyl_y = radius * np.sin(theta)
    cyl_z = y

    # Apply radial offset (for dot height)
    cyl_x += z * np.cos(theta)
    cyl_y += z * np.sin(theta)

    return cyl_x, cyl_y, cyl_z
