# Install C-Minus as a command-line application

C-Minus requires Python 3.10 or newer and installs two commands: `cminus` for
translation/execution and `cminus-check` for C11 equivalence checking. Black is
installed automatically as a compiler dependency. Generated Python programs
use only the standard library. GCC or another compatible C11 compiler is needed
only for equivalence checks.

## Install with pipx

On macOS with Homebrew, install pipx if it is not already present:

```sh
brew install pipx
```

For other platforms, follow the
[pipx installation instructions](https://pipx.pypa.io/stable/installation/).
From the C-Minus project directory, install a regular copy of the application:

```sh
pipx install .
pipx ensurepath
```

Open a new terminal if needed for the PATH update, then run:

```sh
cminus --version
cminus --help
cminus-check --version
cminus-check --help
cminus path/to/program.c --run
cminus path/to/program.c -o path/to/program.py
cminus-check path/to/program.c --cc gcc
```

The commands work from any directory. Source-file paths are relative to your
current directory, or can be absolute. The installed application is a copy of
the package; changes to the source checkout require a reinstall. To select a
particular Python interpreter, use `pipx install --python python3.14 .`.

## Install a wheel

A wheel can be copied to another computer without the repository. After building
the distribution, install it with:

```sh
pipx install dist/cminus-0.2.0-py3-none-any.whl
pipx ensurepath
```

Use the actual filename for future versions. Dependencies are downloaded unless
they are available locally. A source distribution such as
`dist/cminus-0.2.0.tar.gz` can also be passed to `pipx install`.

To install with pip inside a virtual environment instead:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install dist/cminus-0.2.0-py3-none-any.whl
cminus --help
```

On Windows, activate with `.venv\Scripts\activate`. `python -m cminus` is also
available through the interpreter where the package was installed.

## Update or remove the installation

After changing the local project or receiving a new wheel, reinstall that copy:

```sh
pipx install --force .
# Or: pipx install --force path/to/new/cminus-version-py3-none-any.whl
```

Remove both commands and their isolated application environment with:

```sh
pipx uninstall cminus
```

## Build and verify distributions

From a development virtual environment at the project root:

```sh
python -m pip install -e '.[dev,build]'
python -m build
python -m twine check --strict dist/*
```

The default build creates a source distribution, then builds the wheel from that
source archive. This verifies that the source archive is complete, as described
in the [build documentation](https://build.pypa.io/en/latest/how-to/basic-usage.html).
The package version comes from `cminus.__version__`. Console entry points are
defined in `pyproject.toml`; the wheel includes all compiler/runtime modules and
excludes tests, caches, and macOS metadata. The source archive also includes
examples, teaching documents, tests, and the installation check.

Verify a fresh installation with an interpreter that has installed the wheel:

```sh
python3 -m venv /tmp/cminus-install
/tmp/cminus-install/bin/python -m pip install dist/cminus-0.2.0-py3-none-any.whl
/tmp/cminus-install/bin/python tools/check_installation.py --cc gcc
```

The check rejects editable installs, verifies both commands and their versions,
translates a program with globals/prototypes, loop jumps, and int/bool pointers,
checks readable generated names and helper selection, runs the generated
program independently with `-I -S`, checks positioned errors, and compares with
C11. Execution happens in a temporary directory outside the source checkout.
CI builds and verifies a clean wheel installation on Python 3.10 and 3.14.
