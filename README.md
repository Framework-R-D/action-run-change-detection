# `action-run-change-detection`

> Encapsulates checkout, relevant-change detection, and result reporting.

## Usage

```yaml
- uses: Framework-R-D/action-run-change-detection@047250bcbe1be9fb479c8f3ceeb85ac1084ede2e # v2
  with:
    input-name: value
```

## Inputs

| Name | Description | Required | Default |
|------|-------------|----------|---------|
| checkout-path | Path to check out code to | true | |
| ref | The branch, ref, or SHA to checkout | true | |
| sha | Immutable source SHA; required unless ref is already a full SHA | false | |
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

## Trust boundary

This action fetches Git objects at an immutable SHA and uses a non-cone `!/*` sparse pattern to exclude all source files. Empty `sparse-checkout` does **not** create an empty or bare checkout in the pinned checkout action; it selects a full checkout. Git must be available, and `head-ref`, when supplied, must equal the same SHA. Legacy branch-only callers must propagate their resolved `sha` before adopting this release. Repository and workspace-relative checkout paths are checked before checkout, including symlink containment. File names are printed with workflow-command interpretation suspended.

The current CodeQL checkout rationale is not a functional suppression. Historical dismissal reasoning that an empty sparse input created a bare repository was incorrect; no remote alert state is changed here. Git-only change detection does not authorize later execution of the target code. The nested detector pin also needs a reviewed release update to adopt its separate filename/output hardening; that unpublished dependency is not supplied by this checkout change.

## License

[Apache 2.0](LICENSE)
