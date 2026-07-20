# Flexible Data Format Validation

Tesseract wrapper for validating tabular files against a JSON configuration.
It accepts either:

- one standalone Excel, CSV, TSV or delimited TXT file; or
- one ZIP containing any number and mixture of those formats.

The validation rules are independent of the physical file format. Excel and
delimited files are first read into a pandas `DataFrame`; the same column,
type, completeness, range and format rules are then applied to both.

## Input model

A Tesseract input is one file. This wrapper therefore exposes one generic
`Bin` input named `input-data`:

- upload a single table directly when only one file must be validated;
- upload a ZIP when several files must be validated in one execution.

The `Bin` input may be mounted as `/mnt/inputs/input_data` without its original
extension. The wrapper identifies ZIP, modern Excel, legacy Excel and delimited
text from the file content and creates an internal working copy with the
appropriate extension.

A ZIP may contain folders and a mixture such as:

```text
2025_01_FOREST_ANIONS.xlsx
2025_01_FOREST_CATIONS.csv
laboratory/2025_ALKALINITY_05.xlsm
laboratory/2025_01_FOREST_DOC_TN.tsv
```

Supported table formats:

- `.xlsx`
- `.xlsm`
- `.xls`
- `.csv`
- `.tsv`
- delimited `.txt`

## Component position

```text
[input_data + tables_config.json]
                  |
                  v
    FlexibleDataFormatValidation
          |        |        |
          v        v        v
        TXT      JSON      ZIP
```

## Inputs

| Name | Type | Mounted path | Description |
|---|---|---|---|
| `input-data` | `Bin` | `/mnt/inputs/input_data` | One standalone table or a ZIP containing several tables. |
| `input-config` | `Json` | `/mnt/inputs/tables_config.json` | Reader and validation rules. The legacy `/mnt/inputs/tables_config.txt` name is also recognised by the Python script. |

## Outputs

| Name | Type | Path | Description |
|---|---|---|---|
| `output-log` | `Text` | `/mnt/outputs/level0/validation_log.txt` | Human-readable report. |
| `output-report` | `Json` | `/mnt/outputs/level0/validation_report.json` | Machine-readable summary and per-file results. |
| `output-data` | `Zip` | `/mnt/outputs/level0/validated_data.zip` | Supplied table files, unchanged, with the configured filename prefix. |

The output ZIP means that the files were **inspected**, not necessarily that
they passed. Always use `validation_log.txt` or `validation_report.json` to
check the validation result.

## Parameters

| Parameter | Type | Default | Behaviour |
|---|---|---:|---|
| `stopOnErrors` | Boolean | `TRUE` | Exit with code 1 when critical errors are found. Reports and the output ZIP are still written first. |
| `inputMode` | String | `AUTO` | `AUTO`, `ARCHIVE` or `SINGLE_FILE`. AUTO inspects the file content. |
| `tableType` | String | empty | Force one configured table type for a standalone file. Normally leave empty. |
| `requireAllTableTypes` | Boolean | `FALSE` | Require at least one file for every table type in the configuration. Useful for complete ZIP deliveries; normally false for a standalone file. |
| `unmatchedFiles` | String | `ERROR` | Treat supported files that match no table rule as `ERROR`, `WARNING` or `IGNORE`. |
| `outputPrefix` | String | `validated_` | Prefix added to filenames inside `validated_data.zip`. |

## How a file is assigned to a table rule

The wrapper uses the following order:

1. `tableType`, when explicitly supplied for a standalone file.
2. Filename matching against each table's `patterns`.
3. Schema inference for a standalone file when the filename is not informative.

Schema inference compares the file's columns with all configured schemas and
selects a table only when the best match is unambiguous. If two schemas are
equally plausible, the wrapper reports a critical unmatched-file error instead
of guessing. In that case, set `tableType` explicitly.

## Configuration format

The recommended configuration is JSON version 2:

```json
{
  "version": 2,
  "defaults": {
    "supported_extensions": [
      ".xlsx", ".xlsm", ".xls", ".csv", ".tsv", ".txt"
    ],
    "reader": {
      "excel": {
        "sheet_name": "data"
      },
      "csv": {
        "sep": ";",
        "decimal": ".",
        "encoding": "utf-8-sig",
        "quotechar": "\""
      },
      "tsv": {
        "sep": "\\t",
        "decimal": ".",
        "encoding": "utf-8-sig"
      },
      "txt": {
        "sep": ";",
        "decimal": ".",
        "encoding": "utf-8-sig"
      }
    },
    "na_values": ["", "n.a", "n.a.", "NA", "N/A", "null"],
    "strip_column_names": true,
    "strip_string_values": true,
    "drop_completely_empty_rows": true,
    "drop_unnamed_empty_columns": true,
    "warn_unexpected_columns": true,
    "warn_empty_optional_columns": true,
    "fail_if_no_files": false,
    "max_examples_per_rule": 8
  },
  "tables": [
    {
      "type": "Anions",
      "patterns": ["*_ANIONS*"],
      "columns": {
        "EndDate": {
          "type": "datetime",
          "format": "%d/%m/%Y"
        },
        "SiteCode": {
          "type": "object",
          "required": true,
          "nullable": false
        },
        "SampleID": {
          "type": "object",
          "required": true,
          "nullable": false
        },
        "CL(mg/l)": {
          "type": "float",
          "min": 0
        }
      }
    }
  ]
}
```

### Reader settings

Global reader settings live under `defaults.reader`. A specific table may
override them:

```json
{
  "type": "Anions",
  "patterns": ["*_ANIONS*"],
  "reader": {
    "excel": {
      "sheet_name": "Anions data"
    },
    "csv": {
      "sep": ",",
      "decimal": ".",
      "encoding": "utf-8-sig"
    }
  },
  "columns": {}
}
```

This allows one ZIP to contain, for example, semicolon-delimited European CSV
files, comma-delimited CSV files and Excel workbooks with different sheet names.

Supported delimited-reader properties include:

- `sep`: explicit delimiter such as `;`, `,`, `|` or `"auto"`;
- `decimal`: `.` or `,`;
- `encoding`: for example `utf-8-sig`, `utf-8`, `latin-1`;
- `quotechar`;
- `skiprows`;
- `header`.

An explicit separator is preferable when it is known. `"sep": "auto"` uses
pandas' Python parser to infer the delimiter.

### Column rules

Each column may define:

| Rule | Meaning |
|---|---|
| `type` | `object`, `string`, `float`, `integer`, `boolean` or `datetime`. |
| `required` | The column itself must exist. |
| `nullable` | Whether empty cells are accepted. `false` rejects them. |
| `format` | Exact datetime format, such as `%d/%m/%Y`. |
| `min`, `max` | Strict numeric limits. Violations are critical errors. |
| `expected_range` | Advisory `[minimum, maximum]`; violations are warnings. |
| `allowed_values` | Closed set of accepted values. |
| `case_sensitive` | Controls case handling for `allowed_values` and regex rules. |
| `regex` | Regular expression that non-empty values must satisfy. |

Examples:

```json
{
  "month": {
    "type": "integer",
    "required": true,
    "nullable": false,
    "min": 1,
    "max": 12
  },
  "pH": {
    "type": "float",
    "min": 0,
    "expected_range": [0, 14]
  },
  "Saturated(Y/N)": {
    "type": "object",
    "allowed_values": ["Y", "N"],
    "case_sensitive": false
  }
}
```

`required` and `nullable` intentionally mean different things:

- `required: true, nullable: true`: the column must exist but may contain empty cells;
- `required: false, nullable: false`: the column may be absent, but if present it may not contain empty cells;
- `required: true, nullable: false`: the column must exist and every row must be filled.

## Legacy configuration compatibility

A legacy JSON list using these properties remains accepted:

- `schema`
- `critical_columns`
- `optional_columns`
- `no_empty`
- `no_negatives`
- `formats`
- `expected_ranges`

The wrapper converts that structure internally to version 2. New components
should use the version 2 format because it keeps all rules for one column in one
place and avoids contradictory lists.

## Validation report

The JSON report contains a global summary and one entry per table:

```json
{
  "summary": {
    "files_checked": 1,
    "files_without_critical_errors": 1,
    "critical_errors": 0,
    "warnings": 4
  },
  "files": [
    {
      "file": "standalone/input_data.xlsx",
      "table_type": "Anions",
      "assignment_method": "schema inference ...",
      "reader": {
        "kind": "excel",
        "sheet_name": "data"
      },
      "rows": 50,
      "columns": 12,
      "errors": [],
      "warnings": [],
      "valid": true
    }
  ]
}
```

For invalid values, messages include row numbers and a bounded number of example
values. The limit is controlled by `max_examples_per_rule`.

## Example resources

Two executions are included:

```text
resources/example/data/
  inputs/input_data              # the supplied multi-file ZIP, mounted as Bin
  inputs/tables_config.json
  execution-parameters.json

resources/example/single-file/
  inputs/input_data              # one supplied ANIONS workbook, mounted as Bin
  inputs/tables_config.json
  execution-parameters.json
```

The ZIP example intentionally contains some critical validation findings in the
pH files because `StartDate` and `EndDate` are configured as non-nullable while
those input columns are empty. This demonstrates `stopOnErrors`; it is not a
reader or archive error.

## Local execution

### Build

```bash
docker build -t lw-flexible-data-format-validation:1.0.0 .
```

### ZIP example

```bash
mkdir -p local-output

docker run --rm \
  -v "$PWD/resources/example/data/inputs:/mnt/inputs:ro" \
  -v "$PWD/local-output:/mnt/outputs" \
  lw-flexible-data-format-validation:1.0.0 \
  --stopOnErrors FALSE \
  --inputMode AUTO \
  --requireAllTableTypes TRUE \
  --unmatchedFiles ERROR \
  --outputPrefix validated_
```

`stopOnErrors` is set to `FALSE` in this manual command so that the known
critical findings in the supplied pH test files do not make Docker return a
failure status.

### Standalone-file example

```bash
rm -rf local-output && mkdir -p local-output

docker run --rm \
  -v "$PWD/resources/example/single-file/inputs:/mnt/inputs:ro" \
  -v "$PWD/local-output:/mnt/outputs" \
  lw-flexible-data-format-validation:1.0.0 \
  --stopOnErrors TRUE \
  --inputMode SINGLE_FILE \
  --requireAllTableTypes FALSE \
  --unmatchedFiles ERROR \
  --outputPrefix validated_
```

## Exit codes

- `0`: execution completed and either no critical errors were found or
  `stopOnErrors=FALSE` was used;
- `1`: critical validation errors were found with `stopOnErrors=TRUE`, or the
  wrapper could not execute.

Even on exit code 1, the wrapper attempts to write the TXT report, JSON report
and output ZIP before exiting.

## Project files

```text
annotation.json
Dockerfile
requirements.txt
data_format_validation.py
validationUnitTest.sh
README.md
resources/example/data/
resources/example/single-file/
```
