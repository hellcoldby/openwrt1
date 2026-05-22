#!/usr/bin/env python3
"""
Patch OpenWrt kernel sprom.c to inject BCM4313 v8 fallback SPROM data.

Usage:
    python3 apply_bcm4313_sprom_fix.py <path_to_sprom.c>

This script applies two fixes to the kernel source:
  1. Adds a forward declaration for sprom_extract().
  2. Replaces the generic memcpy fallback with BCM4313-specific detection
     that injects the correct LCN v8 SPROM via sprom_extract().

Both fixes use regex-based matching to tolerate whitespace variations
across OpenWrt kernel versions.
"""

import re
import sys


FIX_1_PATTERN = re.compile(
    r'(#if\s+defined\s*\(\s*CONFIG_BCMA_HOST_PCI\s*\)\s*\n)'
    r'(\s*int\s+bcm63xx_get_fallback_bcma_sprom\b)',
)

FIX_1_REPLACEMENT = (
    r'\1'
    r'static int sprom_extract(struct ssb_sprom *out, '
    r'const u16 *in, u16 size);\n\n'
    r'\2'
)

FIX_2_PATTERN = re.compile(
    r'\t*memcpy\s*\(\s*out\s*,\s*&fallback_sprom\.sprom\s*,'
    r'\s*sizeof\s*\(\s*struct\s+ssb_sprom\s*\)\s*\)\s*;'
)

def _fix2_replacement(match):
    """Return replacement code for BCM4313 SPROM injection.

    Uses a callable (lambda-equivalent) to avoid re.sub's backslash
    processing in string replacements, which would turn \\n into a
    literal newline and break the C string literal.
    """
    return (
        '\t\tif (bus->host_pci->device == 0x4313) {\n'
        '\t\t\tpr_info("bcma_fallback_sprom: BCM4313 LCN v8 SPROM\\n");\n'
        '\t\t\tsprom_extract(out, bcm4313_sprom,\n'
        '\t\t\t      ARRAY_SIZE(bcm4313_sprom));\n'
        '\t\t} else {\n'
        '\t\t\tmemcpy(out, &fallback_sprom.sprom,\n'
        '\t\t\t       sizeof(struct ssb_sprom));\n'
        '\t\t}'
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 apply_bcm4313_sprom_fix.py <path_to_sprom.c>")
        sys.exit(1)

    path = sys.argv[1]

    with open(path, 'r') as f:
        content = f.read()

    applied = False

    # ---------------------------------------------------------------
    # Fix 1: Add forward declaration for sprom_extract
    # ---------------------------------------------------------------
    new_content, count = FIX_1_PATTERN.subn(FIX_1_REPLACEMENT, content, count=1)
    if count > 0:
        print('[OK] Forward declaration added')
        content = new_content
        applied = True
    else:
        print('[WARN] Could not find insertion point for forward declaration')

    # ---------------------------------------------------------------
    # Fix 2: Replace memcpy with BCM4313 detection + sprom_extract
    # ---------------------------------------------------------------
    new_content, count = FIX_2_PATTERN.subn(_fix2_replacement, content, count=1)
    if count > 0:
        print('[OK] memcpy replaced with BCM4313 detection')
        content = new_content
        applied = True
    else:
        print('[WARN] Could not find target memcpy line')
        for line in content.split('\n'):
            if 'memcpy(out,' in line:
                print('  Found: ' + line.strip())

    if applied:
        with open(path, 'w') as f:
            f.write(content)
        print('[OK] BCM4313 SPROM fix applied successfully!')
    else:
        print('[ERROR] No fixes were applied — sprom.c unchanged')
        sys.exit(1)


if __name__ == '__main__':
    main()
