#!/usr/bin/env python3

import subprocess
import re
import hashlib
import os

# Fixed application salt
SALT = "your-product-name-v1"

OUTPUT_FILE = "/home/hp/dlI"  # Fixed absolute path

def run(cmd):
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception:
        return ""

def get_macs():
    try:
        result = subprocess.run(
            ["ip", "link"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        macs = re.findall(r"link/ether ([0-9a-f:]{17})", result.stdout)
        return sorted(macs)
    except Exception:
        return []

def make_immutable(path):
    subprocess.run(["chattr", "+i", path], check=False)

def main():
    values = []

    system_uuid = run(["dmidecode", "-s", "system-uuid"])
    baseboard_serial = run(["dmidecode", "-s", "baseboard-serial-number"])
    product_uuid = run(["cat", "/sys/class/dmi/id/product_uuid"])
    macs = get_macs()

    for v in [system_uuid, baseboard_serial, product_uuid]:
        if v:
            values.append(v.strip())

    values.extend(macs)

    # Join everything with a delimiter
    fingerprint_raw = "|".join(values)

    # Salt + hash
    hasher = hashlib.sha256()
    hasher.update((SALT + "|" + fingerprint_raw).encode())
    fingerprint_hash = hasher.hexdigest()

    # Write hash to file
    with open(OUTPUT_FILE, "w") as f:
        f.write(fingerprint_hash + "\n")

    # Lock it down
    os.chown(OUTPUT_FILE, 0, 0)      # root:root
    os.chmod(OUTPUT_FILE, 0o644)     # rw-r--r--
    make_immutable(OUTPUT_FILE)

    print("Fingerprint hash written to", OUTPUT_FILE)
    print(fingerprint_hash)



### sudo chattr -i yourfile to delete


if __name__ == "__main__":
    main()
