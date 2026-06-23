# Rich Install Output Design

Date: 2026-06-23

## Scope

Improve CLI output only for `unidep install` and `unidep install-all`.
Do not change dependency resolution, command construction, subprocess execution,
or behavior of other commands.

## Goals

- Use Rich only when installed through the optional extra.
- Keep base `unidep` install free of a hard Rich dependency.
- Keep current plain-text output when Rich is unavailable, stdout is not a TTY,
  or deterministic output is needed for tests.
- Make each install phase easier to scan.
- Print the exact command UniDep runs, with the command string colored in Rich
  output.

Example Rich rendering target:

```text
Installing conda dependencies with micromamba install --yes --override-channels --channel conda-forge fastapi httpx numpy"<3" pip pydantic python"=3.12.*" sqlalchemy
```

The command text after `with` should be styled as a command, for example cyan or
bold cyan. The command content must stay exactly the same as the real command
string that plain mode prints inside backticks today.

## Proposed Approach

Add a small install output helper in `unidep._cli`.

The helper should:

- detect whether `rich` is importable;
- detect whether stdout is interactive enough for animated status output;
- provide a plain fallback that preserves existing printed substrings;
- provide a Rich path for phase messages, colored commands, and optional
  spinner/status wrappers around subprocess execution;
- avoid capturing or transforming child process output.

The helper can stay private to `_cli.py` unless it grows enough to justify a
separate module.

## Install Phases

Apply the helper to these existing install actions:

- empty conda environment creation in `_create_conda_environment`;
- conda dependency installation in `_install_command`;
- pip dependency installation in `_install_command`;
- local package installation in `_pip_install_local`;
- conda-lock environment creation in `_create_env_from_lock`.

`install-all` should inherit the same behavior through `_install_command`.

## Dependency Metadata

Update the optional extra:

```toml
rich = ["rich", "rich-argparse"]
```

This makes direct Rich console/status imports valid when users install
`unidep[rich]` or `unidep[all]`.

## Error Handling

Subprocess failures should propagate as they do today. Rich should not hide the
child process output or replace exceptions. A failed Rich phase may print a
failure marker, but exit behavior must remain unchanged.

## Dry Runs

Dry runs should print planned commands with the same Rich styling, but should not
show spinners or success/failure states for commands that are not executed.

## Testing

Add focused tests for:

- no-Rich fallback preserves existing install output substrings;
- Rich-enabled dry-run output routes command strings through Rich styling;
- exact command text is unchanged in Rich mode;
- existing `install-all` dry-run coverage still passes.

Use fake `rich` modules or monkeypatching where useful so tests do not depend on
terminal capabilities.

## Out Of Scope

- Reworking `conda-lock`, `pixi`, `pip-compile`, `doctor`, or render-only
  commands.
- Capturing and reformatting conda, mamba, micromamba, pip, or uv live output.
- Adding prompts, confirmations, or behavior changes.
- Changing command quoting rules.

## Self Review

- No placeholders remain.
- Scope is limited to `install` and `install-all`.
- Rich is optional and guarded.
- Colored command requirement is explicit.
- Existing command construction and subprocess behavior remain unchanged.
