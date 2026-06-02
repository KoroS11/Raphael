# Raphael — Data Sources

## Document Purpose

This is the complete reference for every open data source integrated into Raphael. For each source it specifies the data type, geographic coverage, update frequency, access method, endpoint, authentication requirements, data format, the Raphael layer it populates, and the Prefect flow that handles it. All sources are free and publicly accessible.

---

## 1. Air Quality

### 1.1 OpenAQ v3

| Property | Value |
|---|---|
| Data type | Air quality measurements |
| Parameters | PM2.5, PM10, NO2, O3, CO, SO2 |
| Coverage | 100+ countries, 30,000+ stations |
| Update frequency | Near real-time, typically every 1 hour |
| Historical depth | Full archive from 2016 onwards |
| Base URL | https://api.openaq.org/v3 |
| Authentication | None required. Optional API key raises rate limit from 10 to 60 req/min |
| Data format | JSON |
| Raphael layer | Air Quality (AQ) — primary source |
| Prefect flow | aq_openaq.py |
| Schedule | Every 1 hour |

Key endpoints:
```
GET /locations?bbox={west},{south},{east},{north}&limit=1000
GET /measurements?location_id={id}&parameter=pm25&date_from={iso}&date_to={iso}
```

---

### 1.2 World Air Quality Index (WAQI)

| Property | Value |
|---|---|
| Data type | Real-time AQI and raw pollutant readings |
| Parameters | AQI, PM2.5, PM10, NO2, O3, CO, SO2 |
| Coverage | 12,000+ stations across 1,000+ cities globally |
| Update frequency | Hourly |
| Historical depth | Current day via real-time API |
| Base URL | https://api.waqi.info |
| Authentication | Free API key. Register at aqicn.org/data-platform/token |
| Data format | JSON |
| Raphael layer | Air Quality (AQ) — supplemental |
| Prefect flow | aq_waqi.py |
| Schedule | Every 1 hour |

Key endpoints:
```
GET /map/bounds/?latlng={south},{west},{north},{east}&token={key}
GET /feed/{station_id}/?token={key}
```

---

### 1.3 IQAir AirVisual

| Property | Value |
|---|---|
| Data type | AQ index combined with weather conditions |
| Parameters | AQI (US and CN standards), PM2.5, PM10, temperature, humidity |
| Coverage | Global, strong India coverage |
| Update frequency | Hourly |
| Base URL | https://api.airvisual.com/v2 |
| Authentication | Free API key. Register at iqair.com/dashboard/api |
| Data format | JSON |
| Raphael layer | Air Quality (AQ) — supplemental for India |
| Prefect flow | aq_iqair.py |
| Schedule | Every 1 hour |

Key endpoints:
```
GET /city?city={city}&state={state}&country={country}&key={key}
GET /nearest_city?lat={lat}&lon={lon}&key={key}
```

---

### 1.4 Copernicus Atmosphere Monitoring Service (CAMS)

| Property | Value |
|---|---|
| Data type | Global air quality analysis and forecast |
| Parameters | PM2.5, PM10, NO2, O3, CO, dust, sea salt |
| Coverage | Global, gridded at 0.1 degree resolution |
| Update frequency | Twice daily analysis, 5-day forecast updated daily |
| Base URL | https://ads.atmosphere.copernicus.eu/api/v2 |
| Authentication | Free account required at ads.atmosphere.copernicus.eu |
| Data format | NetCDF, GRIB |
| Raphael layer | Air Quality (AQ) — gridded forecast layer |
| Prefect flow | aq_cams.py |
| Schedule | Every 6 hours |

Notes: CAMS provides a continuous gridded AQ layer covering the entire region rather than point observations. Useful for areas with no monitoring station coverage.

---

### 1.5 Central Pollution Control Board (CPCB) — India

| Property | Value |
|---|---|
| Data type | Official India government air quality data |
| Parameters | PM2.5, PM10, NO2, SO2, CO, NH3, O3 |
| Coverage | India only, approximately 800 stations |
| Update frequency | 15-minute intervals |
| Base URL | https://app.cpcbccr.com/ccr (also mirrored on OpenAQ) |
| Authentication | None for public data |
| Data format | JSON, CSV |
| Raphael layer | Air Quality (AQ) — India primary |
| Prefect flow | aq_openaq.py (CPCB is mirrored in OpenAQ India feed) |

Notes: CPCB data is the authoritative source for India. It is fully accessible through the OpenAQ feed so no separate flow is required. If OpenAQ is unavailable, a direct CPCB fallback can be activated from datasources.toml.

---

## 2. Weather and Climate

### 2.1 Open-Meteo

| Property | Value |
|---|---|
| Data type | Weather forecast and historical climate |
| Parameters | Temperature, precipitation, wind speed and direction, humidity, UV index, cloud cover, surface pressure |
| Coverage | Global, 1 km resolution |
| Update frequency | Forecast updated hourly. Historical updated daily |
| Historical depth | 1940 onwards via ERA5 reanalysis |
| Base URL | https://api.open-meteo.com/v1 |
| Authentication | None required. No rate limit for non-commercial use |
| Data format | JSON |
| Raphael layer | Weather, Precipitation |
| Prefect flow | weather_openmeteo.py |
| Schedule | Every 1 hour |

Key endpoints:
```
GET /forecast?latitude={lat}&longitude={lon}
    &hourly=temperature_2m,precipitation,wind_speed_10m,
    wind_direction_10m,relative_humidity_2m,uv_index
    &forecast_days=7

GET /archive?latitude={lat}&longitude={lon}
    &start_date={date}&end_date={date}
    &hourly=temperature_2m,precipitation
```

---

### 2.2 NOAA Global Forecast System (GFS)

| Property | Value |
|---|---|
| Data type | Global numerical weather prediction model |
| Parameters | Temperature, wind, precipitation, relative humidity, pressure |
| Coverage | Global, 0.25 degree resolution |
| Update frequency | Every 6 hours (00, 06, 12, 18 UTC cycles) |
| Historical depth | Not applicable, forecast model only |
| Base URL | https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl |
| Authentication | None |
| Data format | GRIB2 |
| Raphael layer | Weather (extended forecast, 16 days) |
| Prefect flow | weather_noaa_gfs.py |
| Schedule | Every 6 hours |

Notes: GFS is used for extended 7 to 16 day weather forecasts that go beyond Open-Meteo's 7-day window. GRIB2 files are parsed using the cfgrib Python library before storage.

---

### 2.3 OpenWeatherMap

| Property | Value |
|---|---|
| Data type | Current weather and 5-day forecast |
| Parameters | Temperature, precipitation, wind, humidity, cloud cover, weather condition codes |
| Coverage | Global |
| Update frequency | Hourly |
| Base URL | https://api.openweathermap.org/data/2.5 |
| Authentication | Free API key. Register at openweathermap.org. Free tier: 1,000 calls/day |
| Data format | JSON |
| Raphael layer | Weather — supplemental for current conditions display |
| Prefect flow | weather_openweathermap.py |
| Schedule | Every 1 hour |

---

### 2.4 Copernicus ERA5 (via Climate Data Store)

| Property | Value |
|---|---|
| Data type | Global climate reanalysis |
| Parameters | Complete atmospheric and surface variables, hourly |
| Coverage | Global, 0.25 degree resolution (~25 km) |
| Update frequency | Updated with 5-day lag from present |
| Historical depth | 1940 to present |
| Base URL | https://cds.climate.copernicus.eu/api/v2 |
| Authentication | Free account at cds.climate.copernicus.eu |
| Data format | NetCDF, GRIB |
| Raphael layer | Historical Climate (long-range trend baseline) |
| Prefect flow | weather_era5.py |
| Schedule | Every 24 hours (historical archive, used for baselines) |

Notes: ERA5 is used when users request historical trend analysis beyond 90 days. Open-Meteo's historical endpoint uses ERA5 data under the hood, making direct CDS access optional. Direct access is activated only for bulk historical downloads or when building long-range baselines for a new region.

---

## 3. Satellite and Fire Data

### 3.1 NASA FIRMS — Fire Information for Resource Management System

| Property | Value |
|---|---|
| Data type | Active fire and thermal anomaly detections |
| Parameters | Fire radiative power (FRP), confidence level, brightness temperature |
| Coverage | Global |
| Update frequency | Near real-time, updated every 3 hours |
| Historical depth | 2000 onwards |
| Base URL | https://firms.modaps.eosdis.nasa.gov/api |
| Authentication | Free MAP_KEY. Register at firms.modaps.eosdis.nasa.gov |
| Data format | JSON, CSV |
| Raphael layer | Fire and Heat Anomalies |
| Prefect flow | fire_firms.py |
| Schedule | Every 3 hours |

Key endpoints:
```
GET /area/json/{map_key}/VIIRS_SNPP_NRT/{bbox}/1
GET /area/csv/{map_key}/MODIS_NRT/{bbox}/1
```

---

### 3.2 NASA LANCE — Land, Atmosphere Near Real-Time Capability

| Property | Value |
|---|---|
| Data type | Near real-time satellite products including fire, LST, aerosols |
| Parameters | Fire detections, land surface temperature, aerosol optical depth |
| Coverage | Global |
| Update frequency | Within 3 hours of satellite overpass |
| Base URL | https://lance.modaps.eosdis.nasa.gov |
| Authentication | NASA Earthdata account token |
| Data format | HDF4, GeoTIFF |
| Raphael layer | Fire and Heat Anomalies (LANCE is backup for FIRMS) |
| Prefect flow | fire_lance.py |
| Schedule | Every 3 hours |

---

### 3.3 NASA Earthdata — MODIS Land Surface Temperature (MOD11A1)

| Property | Value |
|---|---|
| Data type | Land surface temperature derived from thermal infrared |
| Parameters | Daytime LST, nighttime LST, QC flags |
| Coverage | Global |
| Resolution | 1 km |
| Update frequency | Daily |
| Historical depth | 2000 onwards |
| Base URL | https://cmr.earthdata.nasa.gov/search |
| Authentication | Free NASA Earthdata account at urs.earthdata.nasa.gov |
| Data format | HDF4, GeoTIFF (via AppEEARS or direct download) |
| Raphael layer | Land Surface Temperature |
| Prefect flow | lst_modis.py |
| Schedule | Daily |

Processing steps after download:
```
1. Rasterio reads HDF4 LST_Day_1km band
2. Apply scale factor: LST_celsius = (raw * 0.02) - 273.15
3. Reproject to EPSG:4326 using pyproj
4. Clip to region bounding box
5. Apply plasma colormap via matplotlib
6. Export as PNG tile
7. Write tile metadata to raster_tiles table
```

---

### 3.4 NASA Earthdata — MODIS NDVI (MOD13A2)

| Property | Value |
|---|---|
| Data type | Normalized Difference Vegetation Index |
| Parameters | NDVI, EVI (Enhanced Vegetation Index) |
| Coverage | Global |
| Resolution | 1 km (MOD13A2), 250 m (MOD13Q1) |
| Update frequency | 16-day composite (minimizes cloud contamination) |
| Historical depth | 2000 onwards |
| Authentication | Same NASA Earthdata account |
| Data format | HDF4, GeoTIFF |
| Raphael layer | NDVI Green Cover (standard resolution) |
| Prefect flow | ndvi_modis.py |
| Schedule | Every 16 days |

---

### 3.5 Copernicus Sentinel-2 (NDVI)

| Property | Value |
|---|---|
| Data type | Multispectral satellite imagery at 10 m resolution |
| Parameters | Band 4 (Red), Band 8 (NIR) for NDVI; Band 11, 12 for built-up index |
| Coverage | Global |
| Resolution | 10 meters |
| Update frequency | Every 5 days |
| Historical depth | 2015 onwards |
| Base URL | https://services.sentinel-hub.com |
| Authentication | Free account + OAuth2 client credentials at sentinelhub.com |
| Data format | GeoTIFF |
| Raphael layer | NDVI Green Cover (high resolution) |
| Prefect flow | ndvi_sentinel.py |
| Schedule | Every 5 days |

NDVI formula: `NDVI = (B08 - B04) / (B08 + B04)`
Value range: -1 (water, bare soil) to +1 (dense vegetation). Urban: 0.0–0.2, Parks: 0.4–0.8.

---

### 3.6 USGS Earth Explorer — Landsat Archive

| Property | Value |
|---|---|
| Data type | Multispectral satellite imagery, historical archive |
| Parameters | All Landsat 5/7/8/9 bands; LST, NDVI derivable |
| Coverage | Global |
| Resolution | 30 meters |
| Update frequency | 16-day repeat cycle |
| Historical depth | 1972 onwards — the longest continuous satellite record |
| Base URL | https://m2m.cr.usgs.gov/api/api/json/stable |
| Authentication | Free USGS account at earthexplorer.usgs.gov |
| Data format | GeoTIFF |
| Raphael layer | NDVI and LST historical (deep archive, on-demand) |
| Prefect flow | imagery_usgs.py |
| Schedule | On demand for historical analysis requests |

Notes: Landsat is the primary source for historical trend analysis going back beyond 2000. Used when users request multi-decade environmental comparisons or when the Historical Trend view queries data older than what MODIS covers.

---

### 3.7 Google Earth Engine

| Property | Value |
|---|---|
| Data type | Planetary-scale geospatial analysis platform |
| Parameters | Access to entire Landsat + Sentinel + MODIS archive with server-side compute |
| Coverage | Global |
| Base URL | https://earthengine.googleapis.com |
| Authentication | Free account for research. Register at earthengine.google.com |
| Data format | GeoTIFF export, Map tiles |
| Raphael layer | On-demand analysis layer for custom queries |
| Prefect flow | imagery_gee.py (optional, activated from settings) |

Notes: Google Earth Engine is optional and used for advanced on-demand analysis. It allows server-side computation over the full satellite archive without downloading raw files. Useful for generating custom historical composites when a user defines a specific analysis period and area.

