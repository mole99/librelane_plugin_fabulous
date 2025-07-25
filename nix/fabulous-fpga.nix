{
  fetchFromGitHub,
  buildPythonPackage,
  setuptools,
  setuptools_scm,
  python-dotenv,
  loguru,
  fasm,
  version ? "2.0.0+b22eaa94",
  rev ? "b22eaa94888480dcd424aeaa9cfaaebc77a15ce1",
  sha256 ? "sha256-11bLT1nRHBCAVJCTjj6r84KiY6nGcU3csCwOhfBQNUg=",
}: let

  self = buildPythonPackage {
    pname = "FABulous";
    format = "pyproject";
    inherit version;

    src = fetchFromGitHub {
        owner = "FPGA-Research";
        repo = "FABulous";
        inherit rev;
        inherit sha256;
        leaveDotGit = true;
    };

    build-system = [
        setuptools
        setuptools_scm
      ];
     
    dependencies = [
      python-dotenv
      loguru
      fasm
    ];
    
    # Remove the executables as they make problems with Nix?
    postPatch = ''
      substituteInPlace pyproject.toml \
        --replace "FABulous = \"FABulous.FABulous:main\"" ""
      substituteInPlace pyproject.toml \
        --replace "bit_gen = \"FABulous.fabric_cad.bit_gen:bit_gen\"" ""
    '';
    
  };
in
  self
