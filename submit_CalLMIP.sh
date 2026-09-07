#!/usr/bin/env bash
set -uo pipefail

INPUT_FILE="./config_files/CalLMIP_Phase1b_Valunc.cfg"      # ascii file to edit
PY_SCRIPT="elm_olmt.py"       # python script to run

#sites=(DE-Gri DE-Hai DE-Tha DK-Sor FI-Hyy FR-Pue IT-Lav IT-MBo IT-Noe NL-Loo RU-Fyo US-MMS US-NR1 US-SRG US-SRM US-Ton US-Var US-Whs US-Wkg AU-ASM AU-How AU-Stp)
# AU-ASM AU-Stp AU-Tum AU-How CH-Cha US-FPe US-GLE US-Ha1
sites=(US-Me2 US-UMB)
#sites=(US-SRG US-Wkg)   # edit this list as needed
for site in "${sites[@]}"; do
    sed -i -E "s|^[[:space:]]*sites[[:space:]]*=.*$|sites = ${site}|" "$INPUT_FILE"

    sed -i -E \
        "s|(Phase1b_Val/[0-9]{8}_)[^_/]+(_ICB1850CNRDCTCBC_ad_spinup_Val/bld)|\1${site}\2|" \
        "$INPUT_FILE"

    python "$PY_SCRIPT" --config "$INPUT_FILE"
    status=$?

    if [ "$status" -ne 0 ]; then
        echo "Python script failed for ${site} (exit code ${status}). Stopping."
        exit "$status"
    fi
done
