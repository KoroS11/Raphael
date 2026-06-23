"""
Blue Team — Evidence Aggregation Layer.

Collects outputs from already-validated modules (PCAD anomaly
detection, Gaussian Plume physics, Prophet+LSTM forecasting,
weather) into a single structured Evidence Object per observation.

