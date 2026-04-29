{
  fetchFromGitHub,
  buildPythonPackage,
  setuptools,
  setuptools-scm,
  textx,
  version ? "v0.2.0",
  rev ? null,
  sha256 ? "sha256-BOCM5ZbJoOEG2g2D1jsB3hNevjCvcg56IUQsZ9pvIvQ=",
}:
let

  self = buildPythonPackage {
    pname = "fasm";
    format = "pyproject";
    inherit version;

    src = fetchFromGitHub {
      owner = "FPGA-Research";
      repo = "FABulous-fasm";
      rev = if rev == null then version else rev;
      inherit sha256;
    };

    build-system = [
      setuptools
      setuptools-scm
    ];

    dependencies = [
      textx
    ];

  };
in
self
