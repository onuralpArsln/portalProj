#!/usr/bin/env python3

import subprocess
import re

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
    except Exception as e:
        return f"ERROR: {e}"

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
        return macs
    except Exception:
        return []

def main():
    print("=== system_uuid (dmidecode) ===")
    print(run(["dmidecode", "-s", "system-uuid"]))

    print("\n=== baseboard_serial (dmidecode) ===")
    print(run(["dmidecode", "-s", "baseboard-serial-number"]))

    print("\n=== product_uuid (sysfs) ===")
    print(run(["cat", "/sys/class/dmi/id/product_uuid"]))

    print("\n=== mac_addresses ===")
    macs = get_macs()
    if macs:
        for mac in macs:
            print(mac)
    else:
        print("(none found)")

if __name__ == "__main__":
    main()
