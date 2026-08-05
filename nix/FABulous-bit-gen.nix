{
  fetchFromGitHub,
  buildPythonPackage,
  setuptools,
  setuptools-scm,
  loguru,
  fabulous-fasm,
  version ? "v0.3.1",
  rev ? null,
  sha256 ? "sha256-X9hWHboI9XCbI5TQeZ8mBX4N9enzPGFpWHxR3I2OqQ8=",
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
