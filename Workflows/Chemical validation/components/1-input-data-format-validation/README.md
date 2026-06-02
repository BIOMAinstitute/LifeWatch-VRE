# 1 — Input Data Format Validation

Validates multiple Excel templates contained in a ZIP against a JSON
configuration file. Produces a plain-text validation log and a ZIP
with the same files renamed with a `validated_` prefix.

## Workflow position

```
[Excel templates ZIP]  →  InputDataFormatValidation  →  WaterChemicalDataTransformation
```

## Inputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| input-data | Zip | `/mnt/inputs/allData.zip` | ZIP of Excel workbooks (.xlsx). Each must have a sheet named `data`. |
| input-config | Text | `/mnt/inputs/config_tables.txt` | JSON file defining validation rules per table type (schema, critical/optional columns, ranges, regex). |

## Outputs

| Name | Type | Path | Description |
|------|------|------|-------------|
| output-log | Text | `/mnt/outputs/validation_log.txt` | Plain-text report: ❌ critical errors, ⚠️ warnings, ✅ ok per file. |
| output-data | Zip | `/mnt/outputs/allData_templates_format_validated.zip` | Same Excel files renamed with `validated_` prefix. |

## Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| stopOnErrors | String | `TRUE` | When `TRUE`, exits with code 1 if any critical error is found, halting the workflow. Set to `FALSE` to always continue. |

## Local execution

```bash
# Place files in data/inputs/
cp allData.zip           data/inputs/allData.zip
cp config_tables.txt     data/inputs/config_tables.txt

# Edit data/execution-parameters.json if needed
./bin/build-image
./bin/execute
# Results appear in data/outputs/
```

## data/execution-parameters.json

```json
{
  "parameters": [
    { "name": "stopOnErrors", "defaultValue": "TRUE", "value": "TRUE" }
  ]
}
```

## Notes

- Validation rules are defined in `config_tables.txt` (JSON array). Each entry
  specifies `path` (glob pattern), `schema`, `critical_columns`,
  `optional_columns`, `no_negatives`, `expected_ranges` and `formats`.
- The `path` patterns in the config are relative to the ZIP extraction directory.
- If `stopOnErrors = FALSE` the log is still written but the wrapper exits 0
  even when errors are found.
