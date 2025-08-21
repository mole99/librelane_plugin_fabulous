{
  fetchFromGitHub,
  buildPythonPackage,
  setuptools,
  setuptools_scm,
  python-dotenv,
  loguru,
  fasm,
  requests,
  cmd2,
  bitarray,
  version ? "2.0.0+887d22b9",
  rev ? "887d22b926e6400512dba12f63e634706807119e",
  sha256 ? "sha256-WyJsXviZbGNlaXVMFCEz/8KNp8OUS5CJpmkjJsDWBi8=",
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
  
    patches = [
        ./patches/fabulous/fix_supertile_framedata_o.patch
    ];
     
    dependencies = [
      python-dotenv
      loguru
      fasm
      requests
      cmd2
      bitarray
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
