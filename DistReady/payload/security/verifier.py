#!/usr/bin/env python3

import subprocess
import re
import hashlib
import sys

SALT = "your-product-name-v1"
INPUT_FILE = "dlI"

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
        return sorted(re.findall(r"link/ether ([0-9a-f:]{17})", result.stdout))
    except Exception:
        return []

def calculate_hash():
    values = []

    system_uuid = run(["dmidecode", "-s", "system-uuid"])
    baseboard_serial = run(["dmidecode", "-s", "baseboard-serial-number"])
    product_uuid = run(["cat", "/sys/class/dmi/id/product_uuid"])
    macs = get_macs()

    for v in [system_uuid, baseboard_serial, product_uuid]:
        if v:
            values.append(v.strip())

    values.extend(macs)

    raw = "|".join(values)
    return hashlib.sha256((SALT + "|" + raw).encode()).hexdigest()

def read_stored_hash():
    try:
        with open(INPUT_FILE, "r") as f:
            return f.read().strip()
    except Exception:
        return None

def main():
    stored_hash = read_stored_hash()
    if not stored_hash:
        print("False")
        sys.exit(1)

    current_hash = calculate_hash()

    print(current_hash == stored_hash)

if __name__ == "__main__":
    main()
