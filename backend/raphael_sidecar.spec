# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['sidecar_entry.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Include mod_spatialite for SpatiaLite support
        # Find the actual path in the conda env
        ('C:/Users/harsh/anaconda3/envs/raphael-env/Library/bin/mod_spatialite.dll', '.'),
        ('C:/Users/harsh/anaconda3/envs/raphael-env/Library/bin/spatialite.dll', '.'),
        # Include client assets and shell file
        ('C:/Users/harsh/Raphael/raphael-frontend/dist/client', 'frontend_dist'),
        # Include prophet version file (loaded dynamically at runtime by prophet package)
        ('C:/Users/harsh/anaconda3/envs/raphael-env/Lib/site-packages/prophet/__version__.py', 'prophet'),
        # Include alembic.ini configuration file
        ('alembic.ini', '.'),
        # Include alembic database migrations scripts
        ('db/migrations', 'db/migrations'),
        # Include reports HTML templates
        ('reports/templates', 'reports/templates'),
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'sqlalchemy.dialects.sqlite',
        'pydantic',
        'api.main',
        'api.routes.zones',
        'api.routes.regions',
        'api.routes.layers',
        'api.routes.geocode',
        'api.routes.system',
        'api.routes.anomalies',
        'api.routes.risk',
        'api.routes.alerts',
        'api.routes.reports',
        'api.routes.imports',
        'api.routes.users',
        'api.routes.ws',
        'db.connection',
        'db.models',
        'ml.runner',
        'ml.anomaly',
        'ml.clustering',
        'ml.forecast',
        'ml.risk_score',
        'ml.plume',
        'ml.attribution',
        'ml.explainer',
        'ml.alerts_evaluator',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['mlflow', 'prefect', 'mage_ai', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='raphael-sidecar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # keep True for debugging; set False for production
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='raphael-sidecar',
)
