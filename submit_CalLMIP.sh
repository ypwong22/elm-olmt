#!/usr/bin/env bash
set -uo pipefail

INPUT_FILE="./config_files/CalLMIP_Phase1b_ens.cfg"      # ascii file to edit
PY_SCRIPT="elm_olmt.py"       # python script to run

#sites=(DE-Gri DE-Hai DE-Tha DK-Sor FI-Hyy FR-Pue IT-Lav IT-MBo IT-Noe NL-Loo RU-Fyo US-MMS US-NR1 US-SRG US-SRM US-Ton US-Var US-Whs US-Wkg AU-ASM AU-How AU-Stp)
#sites=(AU-ASM AU-How AU-Stp)
#sites=(AU-Tum CH-Cha US-FPe US-GLE US-Ha1 US-Me2 US-UMB)   # edit this list as needed
#sites=(US-NR1 US-GLE)
sites=(FR-Pue)
for site in "${sites[@]}"; do
    sed -i "14s/.*/sites = ${site}/" "$INPUT_FILE"

    python "$PY_SCRIPT" --config "$INPUT_FILE"
    status=$?

    if [ "$status" -ne 0 ]; then
        echo "Python script failed for ${site} (exit code ${status}). Stopping."
        exit "$status"
    fi
done
