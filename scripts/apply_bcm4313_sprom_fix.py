#!/usr/bin/env python3
"""
BCM4313 SPROM Fix - Apply to kernel source during OpenWrt build
This script patches sprom.c to detect BCM4313 and use custom fallback SPROM
"""

import os
import sys

def apply_sprom_fix(kernel_sprom_path):
    """Apply BCM4313 SPROM detection fix to sprom.c"""
    
    if not os.path.isfile(kernel_sprom_path):
        print(f"[ERROR] File not found: {kernel_sprom_path}")
        return False
    
    try:
        with open(kernel_sprom_path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"[ERROR] Failed to read file: {e}")
        return False
    
    # Fix 1: Add forward declaration for sprom_extract
    old_if = '#if defined(CONFIG_BCMA_HOST_PCI)\nint bcm63xx_get_fallback_bcma_sprom'
    new_if = '#if defined(CONFIG_BCMA_HOST_PCI)\nstatic int sprom_extract(struct ssb_sprom *out, const u16 *in, u16 size);\n\nint bcm63xx_get_fallback_bcma_sprom'
    
    if old_if in content:
        content = content.replace(old_if, new_if, 1)
        print('[OK] Forward declaration added')
    else:
        print('[WARN] Could not find insertion point for forward declaration')
    
    # Fix 2: Replace memcpy with BCM4313 detection + sprom_extract
    old_memcpy = '\t\tmemcpy(out, &fallback_sprom.sprom, sizeof(struct ssb_sprom));'
    new_code = '''\t\tif (bus->host_pci->device == 0x4313) {
\t\t\tpr_info("bcma_fallback_sprom: BCM4313 LCN v8 SPROM\\n");
\t\t\tsprom_extract(out, bcm4313_sprom,
\t\t\t      ARRAY_SIZE(bcm4313_sprom));
\t\t} else {
\t\t\tmemcpy(out, &fallback_sprom.sprom,
\t\t\t       sizeof(struct ssb_sprom));
\t\t}'''
    
    if old_memcpy in content:
        content = content.replace(old_memcpy, new_code, 1)
        print('[OK] memcpy replaced with BCM4313 detection')
    else:
        print('[WARN] Could not find target memcpy line')
        for line in content.split('\n'):
            if 'memcpy(out,' in line:
                print('  Found: ' + line.strip())
    
    # Write modified content back
    try:
        with open(kernel_sprom_path, 'w') as f:
            f.write(content)
        print('[OK] BCM4313 SPROM fix applied successfully!')
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write file: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: apply_bcm4313_sprom_fix.py <path_to_sprom.c>")
        sys.exit(1)
    
    sprom_path = sys.argv[1]
    success = apply_sprom_fix(sprom_path)
    sys.exit(0 if success else 1)
