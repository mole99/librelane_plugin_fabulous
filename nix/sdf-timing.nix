{
  fetchFromGitHub,
  buildPythonPackage,
  setuptools,
  setuptools-scm,
  pytest,
  tox,
  ply,
  version ? "1.0.0",
  rev ? null,
  sha256 ? "sha256-GKnydzDdS75N2MF2eYzG7KuSzfOCkjipMAaL1TVVJX8=",
}:
let

  self = buildPythonPackage {
    pname = "sdf-timing";
    format = "pyproject";
    inherit version;

    src = fetchFromGitHub {
      owner = "FPGA-Research";
      repo = "f4pga-sdf-timing";
      rev = if rev == null then version else rev;
      inherit sha256;
    };

    build-system = [
      setuptools
    ];

    dependencies = [
      setuptools-scm
      pytest
      tox
      ply
    ];

    postPatch = ''
      substituteInPlace requirements.txt \
        --replace "yapf==0.24.0" ""
      substituteInPlace setup.py \
        --replace "'pyjson'," ""
    '';

  };
in
self
