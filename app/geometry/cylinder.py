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
