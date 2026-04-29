{
  fetchFromGitHub,
  buildPythonPackage,
  setuptools,
  setuptools-scm,
  loguru,
  fabulous-fasm,
  version ? "v0.2.0",
  rev ? null,
  sha256 ? "sha256-bKzDLMA6T/ga6rHaYgssrwXHCDfcejKO8HVRNkny7Bg=",
}:
let

  self = buildPythonPackage {
    pname = "FABulous-bit-gen";
    format = "pyproject";
    inherit version;

    src = fetchFromGitHub {
      owner = "FPGA-Research";
      repo = "FABulous-bit-gen";
      rev = if rev == null then version else rev;
      inherit sha256;
    };

    build-system = [
      setuptools
      setuptools-scm
    ];

    dependencies = [
      loguru
      fabulous-fasm
    ];

  };
in
self
