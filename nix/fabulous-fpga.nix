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
  version ? "2.0.0-44878389",
  rev ? "4487838902a66c1ed3c90a8949f60457c5a1316a",
  sha256 ? "sha256-ZSNMn7oxGR0Clrz9AOrqlh7HwszlqYNYrc1R9L0Olh0=",
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
    ];

    # Remove the executables as they make problems with Nix?
    postPatch = ''
      substituteInPlace pyproject.toml \
        --replace "FABulous = \"FABulous.FABulous:main\"" ""
      substituteInPlace pyproject.toml \
        --replace "fabulous = \"FABulous.FABulous:main\"" ""

      substituteInPlace pyproject.toml \
        --replace "pydantic>=2.12.1" "pydantic>=2.11.1"
      substituteInPlace pyproject.toml \
        --replace "pydantic-settings>=2.10.1" "pydantic-settings>=2.8.1"
      substituteInPlace pyproject.toml \
        --replace "typer>=0.20.0" "pydantic-settings>=0.15.2"
      substituteInPlace pyproject.toml \
        --replace "packaging>=25.0" "packaging>=24.2"
      substituteInPlace pyproject.toml \
        --replace "\"librelane>=3.0.0.dev43\"," ""
      substituteInPlace pyproject.toml \
        --replace "numpy>=2.3.5" "numpy>=2.3.4"
    '';

  };
in
self
