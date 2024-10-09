{
  fetchFromGitHub,
  buildPythonPackage,
  setuptools,
  setuptools_scm,
  python-dotenv,
  loguru,
  fasm,
  version ? "2.0.0+9e0fc1cf",
  rev ? "9e0fc1cf9603c4d227b9a33d0a248b199daae763",
  sha256 ? "sha256-1TPbrMlwLve2AbVSJc86PfJqB1RXGCHv9kLJpc+BK/c=",
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
    
    # Remove fasm, FABulous works without it
    # but it can't generate bitstreams
    postPatch = ''
      substituteInPlace pyproject.toml \
        --replace "FABulous = \"FABulous.FABulous:main\"" ""
      substituteInPlace pyproject.toml \
        --replace "bit_gen = \"FABulous.fabric_cad.bit_gen:bit_gen\"" ""
    '';
    
  };
in
  self
