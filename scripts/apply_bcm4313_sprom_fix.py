#!/usr/bin/env python3
"""
Patch OpenWrt kernel sprom.c to inject BCM4313 v8 fallback SPROM data.

Usage:
    python3 apply_bcm4313_sprom_fix.py <path_to_sprom.c>

This script applies three fixes to the kernel source:
  1. Adds a forward declaration for sprom_extract() before the BCMA function.
  2. In bcm63xx_get_fallback_bcma_sprom() ONLY, replaces the generic
     memcpy fallback with BCM4313-specific detection that injects the
     correct LCN v8 SPROM via sprom_extract().
     (The SSB function bcm63xx_get_fallback_sprom is deliberately
     left untouched — it has no 'bus' variable in scope.)
  3. After sprom_extract(), writes a valid locally-administered MAC
     into il0macaddr / et0macaddr / et1macaddr because the bcm4313_sprom
     template has all-zero MAC fields, which brcmsmac rejects with
     "bad macaddr" (code 22).

All fixes use regex-based matching to tolerate whitespace variations
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

# The memcpy pattern appears in TWO functions:
#   bcm63xx_get_fallback_sprom        (SSB, ~line 390) — NO bus, DO NOT modify
#   bcm63xx_get_fallback_bcma_sprom   (BCMA, ~line 425) — HAS bus, MUST modify
# Anchor to the BCMA function declaration to target the correct one.
FIX_2_PATTERN = re.compile(
    r'(int\s+bcm63xx_get_fallback_bcma_sprom\s*\([^)]*\)\s*\{.*?)'
    r'(\t*memcpy\s*\(\s*out\s*,\s*&fallback_sprom\.sprom\s*,'
    r'\s*sizeof\s*\(\s*struct\s+ssb_sprom\s*\)\s*\)\s*;)',
    re.DOTALL
)

def _fix2_replacement(match):
    """Target only the BCMA function, preserving all code before memcpy."""
    before = match.group(1)  # function start → just before memcpy
    return before + (
        '\t\tif (bus->host_pci->device == 0x4313) {\n'
        '\t\t\tpr_info("bcma_fallback_sprom: BCM4313 LCN v8 SPROM\\n");\n'
        '\t\t\tsprom_extract(out, bcm4313_sprom,\n'
        '\t\t\t      ARRAY_SIZE(bcm4313_sprom));\n'
        '\t\t\t/* bcm4313_sprom[] has zero MAC — brcmsmac\n'
        '\t\t\t * rejects all-zero MAC (bad macaddr).\n'
        '\t\t\t * Assign locally-administered unicast MAC. */\n'
        '\t\t\tout->il0macaddr[0] = 0x02;\n'
        '\t\t\tout->il0macaddr[1] = 0x00;\n'
        '\t\t\tout->il0macaddr[2] = 0x0c;\n'
        '\t\t\tout->il0macaddr[3] = 0xe3;\n'
        '\t\t\tout->il0macaddr[4] = 0x43;\n'
        '\t\t\tout->il0macaddr[5] = 0x13;\n'
        '\t\t\tmemcpy(out->et0macaddr, out->il0macaddr, 6);\n'
        '\t\t\tmemcpy(out->et1macaddr, out->il0macaddr, 6);\n'
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

    with open(path, 'r', encoding='utf-8') as f:
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
        print('[OK] memcpy replaced with BCM4313 detection + MAC fix')
        content = new_content
        applied = True
    else:
        print('[WARN] Could not find target memcpy line')
        for line in content.split('\n'):
            if 'memcpy(out,' in line:
                print('  Found: ' + line.strip())

    if applied:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print('[OK] BCM4313 SPROM fix applied successfully!')
    else:
        print('[ERROR] No fixes were applied — sprom.c unchanged')
        sys.exit(1)


if __name__ == '__main__':
    main()
