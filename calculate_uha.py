#!/usr/bin/env python3
"""
Habitat-suitability calculator
—————————————
Creates SI-h, SI-v and cHSI GeoTIFFs and totals the usable-habitat area.

Dependencies
------------
pip install numpy pandas rasterio

Usage
-----
python habitat_hsi.py depth.tif velocity.tif \
       -c habitat-suitability-grayling-spawn.csv \
       -t 0.6 \
       -o habitat-calculation
"""

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling


# Helper: piece-wise linear interpolation *with* linear extrapolation
# ---------------------------------------------------------------------------
def piecewise_linear(values, x_pts, y_pts):
    """
    values  : numpy array (may contain NaNs)
    x_pts   : 1-D array of break-point x-values (ascending, unique)
    y_pts   : 1-D array of y-values (same length as x_pts)

    Returns : numpy array – SI values, same shape as `values`
    """
    x_pts = np.asarray(x_pts, dtype=float)
    y_pts = np.asarray(y_pts, dtype=float)
    arr = np.asarray(values, dtype=float)

    # Interpolate where in range
    si = np.interp(arr, x_pts, y_pts)

    # Extrapolate on the left side
    left = arr < x_pts[0]
    if np.any(left):
        slope_left = (y_pts[1] - y_pts[0]) / (x_pts[1] - x_pts[0])
        si[left] = y_pts[0] + slope_left * (arr[left] - x_pts[0])

    # Extrapolate on the right side
    right = arr > x_pts[-1]
    if np.any(right):
        slope_right = (y_pts[-1] - y_pts[-2]) / (x_pts[-1] - x_pts[-2])
        si[right] = y_pts[-1] + slope_right * (arr[right] - x_pts[-1])

    return si


# Helper: read the CSV and return *sorted* arrays for depth & velocity curves
# ---------------------------------------------------------------------------
def read_suitability_csv(csv_path):
    raw = pd.read_csv(
        csv_path,
        skiprows=1,                 # drop header row: "Water depth (m), SI-h, ..."
        header=None,
        names=["h", "si_h", "v", "si_v"],
    )

    # Two separate data-frames because the depth column is NaN for the last row
    depth_df = raw[["h", "si_h"]].dropna().astype(float)
    vel_df   = raw[["v", "si_v"]].dropna().astype(float)

    # Sort (important for interpolation)
    depth_df = depth_df.sort_values("h")
    vel_df   = vel_df.sort_values("v")

    return (
        depth_df["h"].to_numpy(),
        depth_df["si_h"].to_numpy(),
        vel_df["v"].to_numpy(),
        vel_df["si_v"].to_numpy(),
    )


# Core routine
# ---------------------------------------------------------------------------
def calculate_habitat(depth_tif, velocity_tif, csv_path, threshold, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- 1.  Suitability curves --------------------------------------------
    h_pts, si_h_pts, v_pts, si_v_pts = read_suitability_csv(csv_path)

    # --- 2.  Open rasters ---------------------------------------------------
    with rasterio.open(depth_tif) as dep_src, rasterio.open(velocity_tif) as vel_src:
        depth = dep_src.read(1, masked=True).astype(float)

        # Resample velocity if the grids differ
        if (
            vel_src.width     != dep_src.width
            or vel_src.height != dep_src.height
            or vel_src.transform != dep_src.transform
        ):
            vel_data = vel_src.read(
                out_shape=(1, dep_src.height, dep_src.width),
                resampling=Resampling.bilinear,
            )[0]
        else:
            vel_data = vel_src.read(1, masked=True).astype(float)

        velocity = np.ma.masked_invalid(vel_data)

        # --- 3.  Calculate SI rasters -------------------------------------
        si_h = piecewise_linear(depth.filled(np.nan), h_pts, si_h_pts)
        si_v = piecewise_linear(velocity.filled(np.nan), v_pts, si_v_pts)

        # --- 4.  Combined HSI ---------------------------------------------
        chsi = np.sqrt(si_h * si_v)

        # ------------------------------------------------------------------ #
        # Write GeoTIFFs
        profile = dep_src.profile.copy()
        profile.update(dtype=rasterio.float32, count=1, compress="lzw", nodata=-9999)

        def _write(name, arr):
            path = out_dir / name
            with rasterio.open(path, "w", **profile) as dst:
                dst.write(np.nan_to_num(arr, nan=-9999).astype(rasterio.float32), 1)

        _write("SI_depth.tif",    si_h)
        _write("SI_velocity.tif", si_v)
        _write("cHSI.tif",        chsi)

    # --- 5.  Usable-habitat statistics -------------------------------------
    usable   = chsi > threshold
    n_pixels = np.count_nonzero(usable)

    # pixel size (m²).  transform[0] = pixel width; transform[4] is negative height
    pixel_area_m2 = abs(profile["transform"][0] * profile["transform"][4])
    total_area_m2 = n_pixels * pixel_area_m2

    print(f"Usable pixels (cHSI > {threshold:.2f}): {n_pixels}")
    print(f"Total usable habitat area          : {total_area_m2:,.2f} m²")


# CLI wrapper
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate SI-h, SI-v, cHSI rasters and area summary."
    )
    parser.add_argument("depth_raster",   help="Water-depth GeoTIFF")
    parser.add_argument("velocity_raster", help="Flow-velocity GeoTIFF")
    parser.add_argument(
        "-c", "--csv",
        default="habitat-suitability-grayling-spawn.csv",
        help="CSV with suitability curves (default: same folder as script)",
    )
    parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=0.6,
        help="cHSI threshold for ‘usable habitat’ (default: 0.6)",
    )
    parser.add_argument(
        "-o", "--out_dir",
        default="habitat-calculation",
        help="Output directory (default: ./habitat-calculation)",
    )
    args = parser.parse_args()

    calculate_habitat(
        args.depth_raster,
        args.velocity_raster,
        args.csv,
        args.threshold,
        args.out_dir,
    )
