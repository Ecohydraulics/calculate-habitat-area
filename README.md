# Habitat‑Suitability Calculator

Compute habitat suitability index GeoTIFF rasters and quantify usable habitat area for ecohydraulic analysis. This code uses a threshold to distinguish between *poor* and *good* habitat quality, as opposed to weighting functions. The result refers to "Usable Habitat Area" as discussed on [https://hydro-informatics.com/exercises/ex-geco.html](https://hydro-informatics.com/exercises/ex-geco.html) and [https://ecohydraulics.org/weighted-usable-habitat-area-in-the-past-and-today/](https://ecohydraulics.org/weighted-usable-habitat-area-in-the-past-and-today/).

---

## Workflow and background

1. **Reads** a CSV file containing water depth and velocity suitability curves.  
2. **Interpolates** (and extrapolates) Suitability-Index (SI) values for every pixel in the two input GeoTIFF rasters (method: linear piecewise interpolation/extrapolation):
   - `SI-h.tif` - suitability based on water-depth,  
   - `SI-v.tif` - suitability based on flow-velocity.  
3. **Combines** them to a composite habitat-suitability raster  
   \[
     \texttt{cHSI.tif} = \sqrt{\text{SI-h} \times \text{SI-v}}
   \]
4. **Counts** all cHSI pixels that exceed a user-defined threshold (default = 0.6) and reports both the pixel count and the corresponding area in m².  
5. **Writes** every output into a sub-folder `./habitat-calculation`.

| Step | Resulting file (in `./habitat-calculation`) | Notes                                                                   |
|------|---------------------------------------------|-------------------------------------------------------------------------|
| 1    | `SI_depth.tif`                              | Suitability index from **depth**                                        |
| 2    | `SI_velocity.tif`                           | Suitability index from **velocity**                                     |
| 3    | `cHSI.tif`                                  | \(\sqrt{\text{SI-h × SI-v}}\)                                           |
| 4    | -                                           | Prints the count of pixels with `cHSI > threshold` and their total area |
| 5    | `./habitat-calculation/*.tif`               | Writes GeoTIFFs to output folder                              |


---

## Requirements&Installation

### System requirements

- Python≥3.8 (tested on 3.8-3.12)
- A C/C++ tool‑chain **or** pre‑built wheels for Rasterio/GDAL.

### Python packages

```bash
pip install numpy pandas rasterio
```

Or install from the provided *requirements.txt*:

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> **Note**: Rasterio wheels embed GDAL. If `pip` falls back to building from source make sure GDAL≥3.4 is available system‑wide. For more information about installing GDAL, visit [https://hydro-informatics.com/python-basics/pyinstall.html](https://hydro-informatics.com/python-basics/pyinstall.html).

### Repository setup

```bash
git clone https://github.com/Ecohydraulics/calculate-habitat-area.git
cd habitat-hsi
```

---

## Prepare the input data

To run `calculate_uha.py` **three** files are needed (see examples in the `example-data` folder):

1. **`water-depth.tif`** - cell‑by‑cell water depth in meters (m)  
2. **`velocity.tif`** - cell‑by‑cell flow velocity in meters per second (m/s)  
3. **`curve.csv`** - four‑column CSV containing suitability‑index curves for the **target fish species and lifestage** (see `habitat‑suitability-grayling-spawn.csv` for an example).

**How to create and inspect GeoTIFF rasters?**

* **Numerical modelling:**Run a 2d hydrodynamic model such as **Telemac2d** to simulate water depth and velocity. A step‑by‑step tutorial is available here:  
  <https://hydro-informatics.com/numerics/telemac/telemac2d.html>
* **Visual inspection:**Open the resulting GeoTIFFs in **QGIS** (<https://qgis.org/>) to verify they share the **same extent, resolution and CRS**. New to QGIS? Follow the quick‑start guide:  
  <https://hydro-informatics.com/geopy/use-qgis.html>

> **Tip:** Any software that exports GeoTIFF rasters on a common grid will work -- Telemac and QGIS are simply well‑documented, open‑source choices.

---

## Usage

The CLI expects two co‑registered GeoTIFF rasters:

- **water-depth.tif**-water depth in m
- **velocity.tif**-flow velocity in m/s

> **Note**: The example usages below assume that all files, `calculate_uha.py`, `water-depth.tif`, `velocity.tif`, and `habitat-suitability-grayling-spawn.csv`, are located in the same folder (directory).

Below are typical invocations (run from project root):

```bash
# minimal run (default threshold0.6, output ./habitat-calculation)
python calculate_uha.py water-depth.tif velocity.tif
```

```bash
# use a custom csv file with suitability index data
python calculate_uha.py water-depth.tif velocity.tif -c habitat-suitability-grayling-spawn.csv
```

```bash
# change the suitability threshold
python calculate_uha.py water-depth.tif velocity.tif -t 0.75
```

```bash
# use custom suitability curves and output folder
python calculate_uha.py water-depth.tif velocity.tif \
        -c brown-trout-curves.csv \
        -o trout_2025_apr
```

```bash
# display help
python calculate_uha.py -h
```

When the run finishes the folder **/habitat-calculation** (or the path supplied with `-o`) will contain:

| File              | Description                             |
| ----------------- | --------------------------------------- |
| `SI_depth.tif`    | Depth‑based suitability index raster    |
| `SI_velocity.tif` | Velocity‑based suitability index raster |
| `cHSI.tif`        | Combined habitat‑suitability raster     |

The script also prints the count of `cHSI` pixels that exceed the threshold and the corresponding area in square metres.

---

## FunctionDocs

| Function          | Purpose                                                                                               |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| ``                | Vectorised piece‑wise linear interpolation *with* extrapolation.                                      |
| ``                | Reads a four‑column CSV and returns sorted numpy arrays `(h, si_h, v, si_v)`.                         |
| ``                | Core routine: reads rasters, computes **SI‑h**, **SI‑v**, **cHSI**, writes GeoTIFFs & prints summary. |
| *CLI entry‑point* | Parses command‑line arguments and calls `calculate_habitat(...)`.                                     |

Docstrings in the code provide full parameter and return‑value details.

---

## Development notes

- Interpolation/extrapolation leverages `numpy.interp`; masked arrays keep NoDatapixels intact.
- The velocity raster is automatically resampled (`Resampling.bilinear`) when its grid differs from the depth raster.

---

## License

Released under the BSD 3-Clause License - see `LICENSE` for details.

