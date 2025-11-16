{
  fetchFromGitHub,
  buildPythonPackage,
  setuptools,
  setuptools_scm,
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
  version ? "2.0.0+79e8b1ab",
  rev ? "79e8b1abc74927e77e8b7357bbe15278b8fe94bf",
  sha256 ? "sha256-BBT4fEcdmDDUM3RAyZNGWmSt3i6ZbF4PJ400uvbUTxI=",
}: let

  self = buildPythonPackage {
    pname = "FABulous";
    format = "pyproject";
    inherit version;

    src = fetchFromGitHub {
        owner = "FPGA-Research";
        repo = "FABulous";
        rev =
          if rev == null
          then version
          else rev;
        inherit sha256;
    };

    build-system = [
        setuptools
        setuptools_scm
      ];
  
    patches = [
        ./patches/fabulous/fix_supertile_framedata_o.patch
        ./patches/fabulous/ignore_destination.patch
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
        --replace "bit_gen = \"FABulous.fabric_cad.bit_gen:bit_gen\"" ""
        
      substituteInPlace pyproject.toml \
        --replace "pydantic-settings>=2.10.1" "pydantic-settings>=2.8.1"
      substituteInPlace pyproject.toml \
        --replace "packaging>=25.0" "packaging>=24.2"
      substituteInPlace pyproject.toml \
        --replace "typer>=0.16.1" "typer>=0.15.2"
    '';
    
  };
in
  self
