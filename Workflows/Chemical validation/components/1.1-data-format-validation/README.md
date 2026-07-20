# Flexible Data Format Validation

Tesseract component for validating tabular data against a JSON configuration.
It accepts either:

- one standalone Excel, CSV, TSV or delimited TXT file; or
- one ZIP containing several files in any mixture of those formats.

The component reads every supported table into a pandas `DataFrame` and then
applies the same column, type, completeness, range and format rules regardless
of the original file format.

## Inputs

| Name | Type | Mounted path | Description |
|---|---|---|---|
| `input-data` | `Bin` | `/mnt/inputs/input_data` | One standalone table or one ZIP containing several tables. |
| `input-config` | `Json` | `/mnt/inputs/tables_config.json` | Reader and validation configuration. |

The uploaded data file may have any original filename. Tesseract mounts it at
`/mnt/inputs/input_data`. When running Docker manually, the input directory may
also contain a normally named `.zip`, `.xlsx`, `.csv`, `.tsv` or `.txt` file.

## Outputs

| Name | Type | Path | Description |
|---|---|---|---|
| `output-log` | `Text` | `/mnt/outputs/validation_log.txt` | Human-readable validation report. |
| `output-report` | `Json` | `/mnt/outputs/validation_report.json` | Machine-readable summary and per-file results. |
| `output-data` | `Zip` | `/mnt/outputs/validated_data.zip` | Inspected input tables with the configured filename prefix. |

The ZIP contains the inspected files unchanged. Its creation does not mean that
all files passed validation; always check the TXT or JSON report.

Files inside `validated_data.zip` are stored below an `input_data/` directory:

```text
validated_data.zip
└── input_data/
    ├── validated_example.xlsx
    └── validated_example.csv
```

## Parameters

| Parameter | Type | Default | Behaviour |
|---|---|---:|---|
| `stopOnErrors` | Boolean | `TRUE` | Returns exit code 1 when critical validation errors are found. Reports and the output ZIP are written first. |
| `inputMode` | String | `AUTO` | `AUTO`, `ARCHIVE` or `SINGLE_FILE`. |
| `unmatchedFiles` | String | `ERROR` | Handles files that cannot be associated with a table rule as `ERROR`, `WARNING` or `IGNORE`. |
| `outputPrefix` | String | `validated_` | Prefix added to each filename inside the output ZIP. |

### Input modes

- `AUTO`: detects ZIP archives and standalone supported tables automatically.
- `ARCHIVE`: requires at least one ZIP input and processes its contents.
- `SINGLE_FILE`: requires exactly one standalone Excel/CSV/TSV/TXT table.

## Automatic table assignment

For each file, the component:

1. checks the filename against each table's `patterns`;
2. if there is no unique filename match, compares the file columns with the
   configured table schemas;
3. assigns the table only when the best schema match is unambiguous.

When two schemas are equally plausible, the file is handled according to
`unmatchedFiles`. Use descriptive patterns and sufficiently different column
schemas to avoid ambiguity.

# How to fill `tables_config.json`

The configuration contains two sections:

```json
{
  "defaults": {
    "...": "options shared by all tables"
  },
  "tables": [
    {
      "type": "TableType",
      "patterns": ["*_PATTERN*"],
      "columns": {
        "ColumnName": {
          "type": "object"
        }
      }
    }
  ]
}
```

- `defaults` contains common reader, cleaning and warning settings.
- `tables` contains one definition for every supported table type.

## Supported extensions

```json
"supported_extensions": [
  ".xlsx",
  ".xlsm",
  ".xls",
  ".csv",
  ".tsv",
  ".txt"
]
```

Excel macros are not executed.

## Reader settings

### Excel

```json
"excel": {
  "sheet_name": "data"
}
```

The worksheet name must match exactly. To read the first worksheet, use:

```json
"sheet_name": 0
```

### CSV

```json
"csv": {
  "sep": ";",
  "decimal": ".",
  "encoding": "utf-8-sig",
  "quotechar": "\""
}
```

| Property | Meaning | Examples |
|---|---|---|
| `sep` | Column separator | `;`, `,`, `|`, `auto` |
| `decimal` | Decimal separator | `.` or `,` |
| `encoding` | Text encoding | `utf-8-sig`, `utf-8`, `latin-1` |
| `quotechar` | Character enclosing text values | `"` |

A common European CSV configuration is:

```json
"sep": ";",
"decimal": ","
```

Use an explicit separator when it is known. `"sep": "auto"` requests
automatic delimiter detection.

### TSV and TXT

```json
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
```

A table may override the general reader settings:

```json
{
  "type": "Anions",
  "patterns": ["*_ANIONS*"],
  "reader": {
    "excel": {
      "sheet_name": "Anion results"
    },
    "csv": {
      "sep": ",",
      "decimal": "."
    }
  },
  "columns": {}
}
```

## Missing values and cleaning

```json
"na_values": [
  "",
  "n.a",
  "n.a.",
  "NA",
  "N/A",
  "NaN",
  "null",
  "NULL"
]
```

All listed values are treated as missing.

| Option | Recommended | Behaviour |
|---|---:|---|
| `strip_column_names` | `true` | Removes surrounding spaces from headers. |
| `strip_string_values` | `true` | Removes surrounding spaces from text cells. |
| `drop_completely_empty_rows` | `true` | Removes rows where every cell is empty. |
| `drop_unnamed_empty_columns` | `true` | Removes empty columns such as `Unnamed: 12`. |
| `warn_unexpected_columns` | `true` | Warns about columns not defined in the schema. |
| `warn_empty_optional_columns` | `true` | Warns when an optional column exists but is entirely empty. |
| `fail_if_no_files` | `false` | Controls whether a missing table type is a critical error. |
| `max_examples_per_rule` | `8` | Limits the invalid examples shown per rule. |

`fail_if_no_files` can be defined globally or overridden per table:

```json
"defaults": {
  "fail_if_no_files": false
}
```

```json
{
  "type": "Anions",
  "fail_if_no_files": true,
  "patterns": ["*_ANIONS*"],
  "columns": {}
}
```

In this example, `Anions` is required but other table types may be absent.

## Defining a table

```json
{
  "type": "Anions",
  "patterns": [
    "*_ANIONS*",
    "*_ANION_RESULTS*"
  ],
  "columns": {
    "...": {}
  }
}
```

- `type` is a unique internal name shown in the reports.
- `patterns` contains one or more filename patterns. `*` represents any
  sequence of characters.

The pattern `*_ANIONS*` matches names such as:

```text
ES02_ANIONS.xlsx
2026_ES02_ANIONS.csv
validated_ES02_ANIONS_results.xlsx
```

A filename that does not match may still be assigned by its columns.

## Defining columns

```json
"SampleID": {
  "type": "object",
  "required": true,
  "nullable": false
}
```

The configured name must match the input header after surrounding spaces have
been removed.

### Supported types

| Type | Use |
|---|---|
| `object` or `string` | Identifiers, names, categories and comments |
| `float` or `number` | Integer or decimal measurements |
| `integer` or `int` | Whole numbers only |
| `datetime` or `date` | Dates and date-times |
| `boolean` or `bool` | Boolean or binary values |

### Required columns and empty cells

`required` and `nullable` control different conditions:

| Configuration | Meaning |
|---|---|
| `required: true`, `nullable: false` | Column must exist and every row must contain a value. |
| `required: true`, `nullable: true` | Column must exist but empty cells are allowed. |
| `required: false`, `nullable: false` | Column may be absent, but if present it cannot contain empty cells. |
| Neither property | Column is optional and empty cells are allowed. |

### Numeric limits

Strict limits produce critical errors:

```json
"month": {
  "type": "integer",
  "required": true,
  "nullable": false,
  "min": 1,
  "max": 12
}
```

An expected range produces a warning:

```json
"pH": {
  "type": "float",
  "min": 0,
  "expected_range": [0, 14]
}
```

- `pH = -1` is a critical error because it violates `min`.
- `pH = 15` is a warning because it is outside `expected_range`.

### Allowed values

```json
"Saturated(Y/N)": {
  "type": "object",
  "allowed_values": ["Y", "N"],
  "case_sensitive": false
}
```

With `case_sensitive: false`, `Y`, `N`, `y` and `n` are accepted.

Numeric categories should use a numeric type:

```json
"measure": {
  "type": "integer",
  "allowed_values": [10, 20, 30]
}
```

### Dates

```json
"StartDate": {
  "type": "datetime",
  "format": "%d/%m/%Y",
  "required": true,
  "nullable": false
}
```

Several formats can be accepted:

```json
"StartDate": {
  "type": "datetime",
  "formats": [
    "%d/%m/%Y",
    "%Y-%m-%d"
  ]
}
```

Common codes are `%d` for day, `%m` for numeric month, `%Y` for four-digit
year, `%H` for hour, `%M` for minute and `%S` for second.

### Regular expressions

```json
"SiteCode": {
  "type": "object",
  "required": true,
  "nullable": false,
  "regex": "^[A-Z]{2}[0-9]{2}$"
}
```

This accepts `ES02` and `FR15`, but rejects `ES2`, `es02` and `SITE02`.

## Complete configuration example

```json
{
  "defaults": {
    "supported_extensions": [
      ".xlsx",
      ".csv"
    ],
    "reader": {
      "excel": {
        "sheet_name": "Hoja1"
      },
      "csv": {
        "sep": ";",
        "decimal": ".",
        "encoding": "utf-8-sig",
        "quotechar": "\""
      }
    },
    "na_values": ["", "NA", "N/A", "null"],
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
      "type": "example",
      "patterns": ["*_EXAMPLE*"],
      "columns": {
        "date": {
          "type": "datetime",
          "format": "%d/%m/%Y",
          "required": true,
          "nullable": false
        },
        "location": {
          "type": "object",
          "required": true,
          "nullable": false
        },
        "height": {
          "type": "float",
          "required": true,
          "nullable": false,
          "min": 0
        },
        "status": {
          "type": "object",
          "allowed_values": ["Y", "N", "Maybe"],
          "case_sensitive": false
        },
        "measure": {
          "type": "integer",
          "allowed_values": [10, 20, 30]
        },
        "pH": {
          "type": "float",
          "min": 0,
          "expected_range": [0, 14]
        },
        "SiteCode": {
          "type": "object",
          "regex": "^[A-Z]{2}[0-9]{2}$"
        },
        "Comments": {
          "type": "object"
        }
      }
    }
  ]
}
```

## Column-rule quick reference

| Rule | Meaning | Result when violated |
|---|---|---|
| `type` | Expected data type | Critical error |
| `required: true` | Column must exist | Critical error |
| `nullable: false` | Empty cells are not allowed | Critical error |
| `min`, `max` | Strict numeric limits | Critical error |
| `expected_range` | Expected non-strict interval | Warning |
| `allowed_values` | Closed set of accepted values | Critical error |
| `case_sensitive` | Controls case for allowed text values | Applied during comparison |
| `regex` | Required text structure | Critical error |
| `format`, `formats` | Accepted date format or formats | Critical error |

## Validation report

`validation_report.json` contains a summary and one entry for every inspected
file. Invalid-value messages include row numbers and a limited number of
examples, controlled by `max_examples_per_rule`.

## Example resources

```text
resources/example/
├── data/                 # CSV + Excel standalone files
├── data-1-template/      # one standalone Excel file
└── data-zip-file/        # ZIP containing several Excel files
```

Each example contains:

```text
inputs/
execution-parameters.json
outputs/
```

## Exit codes

- `0`: execution completed and no blocking condition remains, or critical
  validation errors were allowed with `stopOnErrors=FALSE`;
- `1`: critical validation errors were found with `stopOnErrors=TRUE`, or the
  component could not execute.

The component attempts to write the TXT report, JSON report and output ZIP even
when it returns exit code 1.

