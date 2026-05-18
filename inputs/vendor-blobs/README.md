# Vendor Blob Inputs

Place the Shield Tablet K1 vendor blob archive here before running `make preflight`.

Expected initial file:

- `vendor-nvidia-shieldtablet-lineage15.tar.zst`

Generate it with `make sync-sources`, then `make extract-blobs SERIAL=<serial>` while the stock Lineage 15.1 tablet is attached with adb enabled. The archive extracts into the Android source tree as `vendor/nvidia/...`, and the command pins the SHA-256 in the active profile. Do not commit proprietary blobs.
