#!/usr/bin/env python3
"""Decode Issues with Tissues diagnostics reports ("IWT1.<base64>.<adler32>").

  python decode_report.py IWT1.eyJ...        one report, printed as JSON
  python decode_report.py file.txt ...       every report found in the files
"""
import base64
import json
import re
import sys
import zlib

PATTERN = re.compile(r"IWT1\.([A-Za-z0-9+/=]+)\.([0-9a-f]{8})")


def decode(b64, check):
    raw = base64.b64decode(b64)
    if "%08x" % zlib.adler32(raw) != check:
        raise ValueError("checksum mismatch: the report was cut off or changed")
    return json.loads(raw.decode("utf-8"))


def main(args):
    for arg in args:
        try:
            text = open(arg, encoding="utf-8").read()
        except OSError:
            text = arg
        for m in PATTERN.finditer(re.sub(r"\s+", "", text) if len(text) < 20000 else text):
            print(json.dumps(decode(*m.groups()), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:]) if len(sys.argv) > 1 else sys.exit(__doc__)
