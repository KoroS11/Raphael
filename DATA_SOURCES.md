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

