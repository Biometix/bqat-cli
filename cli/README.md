BQAT-CLI
====

> This is the new Python based entrypoint aiming to replace the legacy `run.sh`, `run.ps`.

Quick Start
----

1. Install

    ```sh
    pip install bqat
    ```

2. Run BQAT

    ```sh
    bqat --help
    ```

Usage
----

| Flag | Description |
| --- | --- |
| --version, -v | Show version info. |
| --update | Update BQAT backend container. |
| --uninstall | Uninstall BQAT-CLI. |

Development
----

Run package:

```sh
uv run bqat --help
```

Build python wheel:

```sh
uv build
```

Build binary exe:

```sh
uv run pyinstaller -F src/bqat/cli.py -n bqat
```
