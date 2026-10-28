"""Business and infrastructure services, independent of the HTTP layer.

Route handlers stay thin here; the record-access interface, session store,
image validation, OCR adapter and identification logic live in this package so
later phases can reuse them without the API.
"""
