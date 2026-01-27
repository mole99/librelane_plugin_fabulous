{
  fetchFromGitHub,
  buildPythonPackage,
  setuptools,
  setuptools-scm,
  loguru,
  fasm,
  version ? "v0.1.0",
  rev ? null,
  sha256 ? "sha256-nrRcqoWIPXcE/jnqq64zw6aCyFkumeF78YiaZ0JyaU0=",
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
      fasm
    ];

  };
in
self
