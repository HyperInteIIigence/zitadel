#!/usr/bin/env python3
"""Select the version-matched ZITADEL Console with Twilio-style HyperSMS controls.

Only alters the existing zitadel-api image override; preserves every static IP,
network, volume, environment variable, authentication configuration and dependent
container. Does not restart services.
"""
from pathlib import Path
import os
import shutil
import tempfile

path = Path("/HyperIntelligence/zitadel/zitadel-compose/docker-compose.override.yml")
backup = path.with_name(path.name + ".pre-sms-controls-20261120")
old = "    image: hypersms-zitadel:4.19.5-pilot-edit-20261120"
new = "    image: hypersms-zitadel:4.19.5-sms-controls-20261120"
source = path.read_text(encoding="utf-8")
if source.count(old) != 1:
    raise SystemExit("BLOCKED: unexpected ZITADEL API image, refusing overwrite")
for addr in ("172.23.0.2", "172.23.0.3", "172.23.0.4", "172.23.0.5"):
    if source.count(addr) != 1:
        raise SystemExit("BLOCKED: missing or duplicate Gatekeeper static IP " + addr)
if backup.exists():
    raise SystemExit("BLOCKED: backup already exists")
shutil.copy2(path, backup)
st = path.stat()
fd, name = tempfile.mkstemp(prefix=".hypersms-controls-", dir=str(path.parent))
try:
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        out.write(source.replace(old, new))
        out.flush()
        os.fsync(out.fileno())
    os.chmod(name, st.st_mode)
    os.replace(name, path)
except BaseException:
    Path(name).unlink(missing_ok=True)
    raise
print("HYPERSMS_CONSOLE_IMAGE_SELECTED; BACKUP_PRESERVED")
