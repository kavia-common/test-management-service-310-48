# Import the fully featured app for BNG efficiency APIs
from ...app.main import app  # re-export the new app as the ASGI entrypoint

# This file exists to keep compatibility with the original template structure.
# The following no-op ensures the imported `app` symbol is referenced so linters don't mark it unused.
assert app is not None
