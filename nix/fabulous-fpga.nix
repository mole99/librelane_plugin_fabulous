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
  version ? "1.0.0",
  rev ? "disable-UserCLK",
  sha256 ? "sha256-9yj2Rqhx/6l6XPqGEmqGUnaEi21UUc872p24guhC2NU=",
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
    '';

  };
in
self
