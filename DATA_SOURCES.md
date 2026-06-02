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
