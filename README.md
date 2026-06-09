# `action-run-change-detection`

> Encapsulates checkout, relevant-change detection, and result reporting.

## Usage

```yaml
- uses: Framework-R-D/action-run-change-detection@v1  # pin to commit SHA in production
  with:
    input-name: value
```

## Inputs

| Name | Description | Required | Default |
|------|-------------|----------|---------|
| checkout-path | Path to check out code to | true | |
| ref | The branch, ref, or SHA to checkout | true | |
| repo | The repository to checkout from | true | |
| base-ref | The base ref for comparison | true | |
| file-type | Predefined file type (cpp, python, cmake, jsonnet, yaml, md) | false | |
| include-globs | Custom include globs | false | |
| exclude-globs | Custom exclude globs | false | |
| head-ref | Explicit head ref (defaults to inputs.ref) | false | |

## Outputs

| Name | Description |
|------|-------------|
| has_changes | Whether relevant changes were detected |
| matched_files | The list of matched files |

## License

[Apache 2.0](LICENSE)
