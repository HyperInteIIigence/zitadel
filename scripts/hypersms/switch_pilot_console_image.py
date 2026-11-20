#!/usr/bin/env python3
"""Atomically switch only the ZITADEL API image in the existing Compose override.

No other service definitions, static IPs, variables, mounts or authentication
configuration are changed. Does not restart any container.
"""
from pathlib import Path
import os
import shutil
import tempfile

p = Path("/HyperIntelligence/zitadel/zitadel-compose/docker-compose.override.yml")
backup = p.with_name(p.name + ".before-pilot-edit-20261120")
old = "    image: hypersms-zitadel:4.19.5-console-20261120"
new = "    image: hypersms-zitadel:4.19.5-pilot-edit-20261120"
s = p.read_text(encoding="utf-8")
if s.count(old) != 1:
    raise SystemExit("BLOCKED: unexpected original API image in the persistent Compose override")
for expected in ("172.23.0.2", "172.23.0.3", "172.23.0.4", "172.23.0.5"):
    if s.count(expected) != 1:
        raise SystemExit("BLOCKED: static-IP topology mismatch")
if backup.exists():
    raise SystemExit("BLOCKED: pilot backup already exists")
shutil.copy2(p, backup)
st = p.stat()
fd, temp = tempfile.mkstemp(prefix=".hypersms-override-", dir=str(p.parent))
try:
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(s.replace(old, new))
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temp, st.st_mode)
    os.replace(temp, p)
except BaseException:
    Path(temp).unlink(missing_ok=True)
    raise
print("PERSISTENT_API_IMAGE_UPDATED; PREVIOUS_COMPOSE_OVERRIDE_BACKED_UP")
