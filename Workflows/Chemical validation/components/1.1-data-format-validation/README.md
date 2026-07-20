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
| `output-log` | `Text` | `/mnt/outputs/validation_log.txt` | Human-readable report. |
| `output-report` | `Json` | `/mnt/outputs/validation_report.json` | Machine-readable summary and per-file results. |
| `output-data` | `Zip` | `/mnt/outputs/validated_data.zip` | Supplied table files, unchanged, with the configured filename prefix. |

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

## How to fill `tables_config.json`

The configuration file describes:

1. how Excel and delimited files must be read;
2. how each table type is identified; and
3. which validation rules must be applied to each column.

The recommended structure is:

```json
{
  "version": 2,
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

### 1. General structure

| Property | Purpose |
|---|---|
| `version` | Configuration format version. Use `2`. |
| `defaults` | Reader, cleaning and warning options shared by all tables. |
| `tables` | List of the table types that can be validated. |

---

### 2. Supported input formats

Use `supported_extensions` to specify which tabular files are accepted:

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

- `.xlsx`, `.xlsm` and `.xls` are read as Excel workbooks.
- `.csv`, `.tsv` and `.txt` are read as delimited text tables.
- Excel macros are not executed.

---

### 3. Reader settings

Reader settings are defined under `defaults.reader`.

#### Excel

```json
"excel": {
  "sheet_name": "data"
}
```

`sheet_name` is the worksheet to read. For example:

```json
"sheet_name": "Hoja1"
```

requires a worksheet called exactly `Hoja1`.

To always read the first worksheet:

```json
"sheet_name": 0
```

#### CSV

```json
"csv": {
  "sep": ";",
  "decimal": ".",
  "encoding": "utf-8-sig",
  "quotechar": "\""
}
```

| Property | Meaning | Common values |
|---|---|---|
| `sep` | Column separator | `";"`, `","`, `"auto"` |
| `decimal` | Decimal separator | `"."` or `","` |
| `encoding` | Text encoding | `"utf-8-sig"`, `"utf-8"`, `"latin-1"` |
| `quotechar` | Character enclosing text fields | `"\"` |

A common European CSV uses:

```json
"sep": ";",
"decimal": ","
```

An explicit separator is preferable. Use `"sep": "auto"` only when the
separator is unknown.

#### TSV and TXT

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

`"\\t"` represents a tab character.

A specific table can override the general reader settings:

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

---

### 4. Missing values and automatic cleaning

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

All listed values are interpreted as missing data. Add other values only when
they genuinely mean that the cell is empty.

The main cleaning options are:

| Option | Recommended value | Behaviour |
|---|---:|---|
| `strip_column_names` | `true` | Removes spaces before and after column names. |
| `strip_string_values` | `true` | Removes spaces before and after text values. |
| `drop_completely_empty_rows` | `true` | Removes rows where every cell is empty. |
| `drop_unnamed_empty_columns` | `true` | Removes empty columns such as `Unnamed: 12`. |
| `warn_unexpected_columns` | `true` | Warns about columns not defined in the configuration. |
| `warn_empty_optional_columns` | `true` | Warns when an optional column exists but is completely empty. |
| `fail_if_no_files` | `false` | Allows a configured table type to be absent. |
| `max_examples_per_rule` | `8` | Limits the examples displayed for each validation problem. |

The execution parameter `requireAllTableTypes=TRUE` requires every configured
table type even when `fail_if_no_files` is `false`.

---

### 5. Defining a table type

Each element of `tables` represents one kind of input table:

```json
{
  "type": "Anions",
  "patterns": [
    "*_ANIONS*"
  ],
  "columns": {
    "...": {}
  }
}
```

#### `type`

A unique internal name used in reports and by the `tableType` execution
parameter:

```json
"type": "Anions"
```

#### `patterns`

Filename patterns used to identify the table:

```json
"patterns": [
  "*_ANIONS*"
]
```

This matches names such as:

```text
ES02_ANIONS.xlsx
2026_ES02_ANIONS.csv
validated_ES02_ANIONS_results.xlsx
```

Several alternatives may be supplied:

```json
"patterns": [
  "*_ANIONS*",
  "*_ANION_RESULTS*",
  "*_ANIONES*"
]
```

A file whose name does not match may still be assigned through schema inference
by comparing its columns with the configured tables. Therefore, `patterns`
provide the preferred identification method but are not an absolute filename
restriction in the current implementation.

---

### 6. Defining columns

Columns are declared inside `columns`:

```json
"columns": {
  "SampleID": {
    "type": "object",
    "required": true,
    "nullable": false
  }
}
```

The configured name must match the input header after surrounding spaces have
been removed.

#### Supported types

| Type | Use |
|---|---|
| `object` or `string` | Identifiers, names, codes, categories and comments |
| `float` or `number` | Integer or decimal measurements |
| `integer` or `int` | Whole numbers only |
| `datetime` or `date` | Dates and date-times |
| `boolean` or `bool` | Boolean or binary values |

Examples:

```json
"SiteCode": {
  "type": "object"
},
"pH": {
  "type": "float"
},
"month": {
  "type": "integer"
},
"StartDate": {
  "type": "datetime",
  "format": "%d/%m/%Y"
}
```

---

### 7. Column presence and empty cells

`required` and `nullable` control different things.

```json
"required": true
```

means that the column must exist.

```json
"nullable": false
```

means that the column cannot contain empty cells.

The most common strict definition is:

```json
"SampleID": {
  "type": "object",
  "required": true,
  "nullable": false
}
```

This requires the column and requires a value in every row.

The possible combinations are:

| Configuration | Meaning |
|---|---|
| `required: true`, `nullable: false` | Column must exist and every row must be filled. |
| `required: true`, `nullable: true` | Column must exist but may contain empty cells. |
| `required: false`, `nullable: false` | Column may be absent, but if present it cannot contain empty cells. |
| Neither property | Column is optional and empty cells are allowed. |

---

### 8. Numeric limits

Strict limits produce critical errors:

```json
"month": {
  "type": "integer",
  "min": 1,
  "max": 12
}
```

An expected range produces a warning:

```json
"pH": {
  "type": "float",
  "min": 0,
  "expected_range": [
    0,
    14
  ]
}
```

In this example:

- `pH = -1` is a critical error because it violates `min`;
- `pH = 15` is a warning because it is outside `expected_range`;
- `pH = 7` is valid.

Use `min` and `max` for impossible or unacceptable values. Use
`expected_range` for unusual values that should be reviewed without stopping
the workflow.

---

### 9. Allowed values

Use `allowed_values` for categorical fields:

```json
"Saturated(Y/N)": {
  "type": "object",
  "allowed_values": [
    "Y",
    "N"
  ],
  "case_sensitive": false
}
```

With `case_sensitive: false`, `Y`, `N`, `y` and `n` are accepted.

Numeric categories should preferably use a numeric type:

```json
"medida": {
  "type": "integer",
  "allowed_values": [
    10,
    20,
    30
  ]
}
```

`case_sensitive` has no effect on numeric columns.

---

### 10. Date formats

Use `format` to require one exact date format:

```json
"StartDate": {
  "type": "datetime",
  "format": "%d/%m/%Y"
}
```

Common date codes are:

| Code | Meaning |
|---|---|
| `%d` | Day |
| `%m` | Numeric month |
| `%Y` | Four-digit year |
| `%y` | Two-digit year |
| `%H` | Hour |
| `%M` | Minute |
| `%S` | Second |

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

Defining an exact format is safer than relying on automatic date parsing.

---

### 11. Regular expressions

Use `regex` when a text field must follow a specific structure:

```json
"SiteCode": {
  "type": "object",
  "required": true,
  "nullable": false,
  "regex": "^[A-Z]{2}[0-9]{2}$"
}
```

This accepts values such as `ES02` and `FR15`, but rejects `ES2`, `es02` and
`SITE02`.

The regular expression must match the complete non-empty cell value.

---

### 12. Complete example

```json
{
  "version": 2,
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
    "na_values": [
      "",
      "NA",
      "N/A",
      "null"
    ],
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
      "patterns": [
        "*_EXAMPLE*"
      ],
      "columns": {
        "fecha": {
          "type": "datetime",
          "format": "%d/%m/%Y",
          "required": true,
          "nullable": false
        },
        "hola": {
          "type": "object",
          "required": true,
          "nullable": false
        },
        "altura": {
          "type": "float",
          "required": true,
          "nullable": false,
          "min": 0
        },
        "verdad": {
          "type": "object",
          "allowed_values": [
            "Y",
            "N",
            "Quizas"
          ],
          "case_sensitive": false
        },
        "medida": {
          "type": "integer",
          "allowed_values": [
            10,
            20,
            30
          ]
        },
        "pH": {
          "type": "float",
          "min": 0,
          "expected_range": [
            0,
            14
          ]
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

### Quick reference for column rules

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

### Recommended approach

1. Use `required: true` and `nullable: false` for essential identifiers.
2. Use `integer` for years, months and numeric codes.
3. Use `float` for measurements and concentrations.
4. Use strict `min` and `max` limits only for impossible values.
5. Use `expected_range` for values that should be reviewed but not rejected.
6. Use descriptive filename patterns to reduce ambiguous assignments.
7. Test each configuration with a valid file and with deliberately invalid
   examples such as missing columns, empty mandatory cells, invalid dates,
   text in numeric columns and out-of-range values.

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

## Exit codes

- `0`: execution completed and either no critical errors were found or
  `stopOnErrors=FALSE` was used;
- `1`: critical validation errors were found with `stopOnErrors=TRUE`, or the
  wrapper could not execute.

Even on exit code 1, the wrapper attempts to write the TXT report, JSON report
and output ZIP before exiting.

```