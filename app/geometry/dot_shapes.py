"""
Dot shape builders for braille elements.

This module contains pure functions that build mesh primitives for different
braille dot styles: cones, frustums, hemispheres, and bowls (spherical caps).
"""

import numpy as np
import trimesh


def create_braille_dot(x, y, z, settings):
    """
    Create a braille dot mesh at the origin, then translate to (x, y, z).
    - Default: cone frustum using emboss parameters
    - Optional: rounded dome (spherical cap) using rounded parameters

    Args:
        x, y, z: Target position for the dot
        settings: CardSettings object with dot parameters

    Returns:
        Trimesh object representing the braille dot
    """
    if getattr(settings, 'use_rounded_dots', 0):
        # Cone frustum base + spherical cap dome (dome diameter equals cone flat-top diameter)
        base_diameter = float(
            getattr(settings, 'rounded_dot_base_diameter', getattr(settings, 'rounded_dot_diameter', 2.0))
        )
        dome_diameter = float(
            getattr(settings, 'rounded_dot_dome_diameter', getattr(settings, 'rounded_dot_base_diameter', 1.5))
        )
        base_radius = max(0.0, base_diameter / 2.0)
        top_radius = max(0.0, dome_diameter / 2.0)
        base_h = float(
            getattr(settings, 'rounded_dot_base_height', getattr(settings, 'rounded_dot_cylinder_height', 0.2))
        )
        dome_h = float(getattr(settings, 'rounded_dot_dome_height', getattr(settings, 'rounded_dot_height', 0.6)))
        if base_radius > 0 and base_h >= 0 and dome_h > 0:
            parts = []
            # Build a conical frustum by scaling the top ring of a cylinder
            if base_h > 0:
                frustum = trimesh.creation.cylinder(radius=base_radius, height=base_h, sections=48)
                # Scale top vertices in XY so top radius equals top_radius
                if base_radius > 0:
                    scale_factor = (top_radius / base_radius) if base_radius > 1e-9 else 1.0
                else:
                    scale_factor = 1.0
                top_z = frustum.vertices[:, 2].max()
                is_top = np.isclose(frustum.vertices[:, 2], top_z)
                frustum.vertices[is_top, :2] *= scale_factor
                parts.append(frustum)

            # Spherical cap dome starting at top of frustum; base radius = top_radius
            # Serverless-friendly: avoid boolean intersection; place sphere so lower portion overlaps cylinder base
            # The overlap is acceptable for STL export and avoids external boolean backends.
            R = (top_radius * top_radius + dome_h * dome_h) / (2.0 * dome_h)
            zc = (base_h / 2.0) + (dome_h - R)  # center so cap base lies near z = base_h/2
            sphere = trimesh.creation.icosphere(
                radius=R, subdivisions=max(2, int(getattr(settings, 'hemisphere_subdivisions', 1)) + 2)
            )
            sphere.apply_translation([0.0, 0.0, zc])
            parts.append(sphere)

            # Combine, recenter by shifting down half of dome height, then translate to (x, y, z)
            dot = trimesh.util.concatenate(parts)
            dot.apply_translation([0.0, 0.0, -dome_h / 2.0])
            dot.apply_translation((x, y, z))
            return dot

    # Default cone frustum path
    cylinder = trimesh.creation.cylinder(
        radius=settings.emboss_dot_base_diameter / 2, height=settings.emboss_dot_height, sections=16
    )

    if settings.emboss_dot_base_diameter > 0:
        scale_factor = settings.emboss_dot_flat_hat / settings.emboss_dot_base_diameter
        top_surface_z = cylinder.vertices[:, 2].max()
        is_top_vertex = np.isclose(cylinder.vertices[:, 2], top_surface_z)
        cylinder.vertices[is_top_vertex, :2] *= scale_factor

    cylinder.apply_translation((x, y, z))
    return cylinder
