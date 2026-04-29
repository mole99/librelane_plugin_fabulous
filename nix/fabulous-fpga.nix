{
  fetchFromGitHub,
  buildPythonPackage,
  setuptools,
  setuptools-scm,
  python-dotenv,
  loguru,
  requests,
  cmd2,
  bitarray,
  pydantic,
  pydantic-settings,
  packaging,
  typer,
  gnureadline,
  FABulous-bit-gen,
  pyyaml,
  click,
  numpy,
  pymoo,
  networkx,
  pick,
  sdf-timing,
  version ? "2.0.0",
  rev ? "09dba9799b5a4a2f6845ee2e0895ab0c97dd6306",
  sha256 ? "sha256-bmM9jSxmLneZYJ07z6oF8jMd1LkWXr8jlF9jHqTMqe8=",
}:
let

  self = buildPythonPackage {
    pname = "FABulous";
    format = "pyproject";
    inherit version;

    src = fetchFromGitHub {
      owner = "FPGA-Research";
      repo = "FABulous";
      rev = if rev == null then version else rev;
      inherit sha256;
    };

    build-system = [
      setuptools
      setuptools-scm
    ];

    patches = [
      ./patches/fabulous/fix_supertile_framedata_o.patch
      ./patches/fabulous/ignore_destination.patch
      ./patches/fabulous/keep_tiles.patch
      ./patches/fabulous/emulation_rows.patch
    ];

    dependencies = [
      python-dotenv
      loguru
      requests
      cmd2
      bitarray
      pydantic
      pydantic-settings
      packaging
      typer
      gnureadline
      FABulous-bit-gen
      pyyaml
      click
      numpy
      pymoo
      networkx
      pick
      sdf-timing
    ];

    # Remove the executables as they make problems with Nix?
    postPatch = ''
      substituteInPlace pyproject.toml \
        --replace "FABulous = \"fabulous.fabulous:main\"" ""
      substituteInPlace pyproject.toml \
        --replace "fabulous = \"fabulous.fabulous:main\"" ""

      substituteInPlace pyproject.toml \
        --replace "pydantic>=2.12.1" "pydantic>=2.11.1"
      substituteInPlace pyproject.toml \
        --replace "pydantic-settings>=2.10.1" "pydantic-settings>=2.8.1"
      substituteInPlace pyproject.toml \
        --replace "typer>=0.20.0" "pydantic-settings>=0.15.2"
      substituteInPlace pyproject.toml \
        --replace "packaging>=25.0" "packaging>=24.2"
      substituteInPlace pyproject.toml \
        --replace "\"librelane>=3.0.0\"," ""
      substituteInPlace pyproject.toml \
        --replace "numpy>=2.3.5" "numpy>=2.3.4"
      substituteInPlace pyproject.toml \
        --replace "networkx>=3.6.1" "networkx>=3.5.0"
      substituteInPlace pyproject.toml \
        --replace "\"ciel>=2.4.0\"," ""
      substituteInPlace pyproject.toml \
        --replace "\"go-task-bin>=3.40.0\"," ""
    '';

  };
in
self
