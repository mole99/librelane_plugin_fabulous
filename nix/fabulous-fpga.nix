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
  numpy,
  dill,
  pymoo,
  networkx,
  pick,
  sdf-timing,
  jinja2,
  version ? "2.0.0",
  rev ? "a4d391f609b5a1dd5c934e6ddf0911acddee5f10",
  sha256 ? "sha256-dLgdebeCqdDsGjvhjITgVXEnxTNRA0LlMVZ1VhlfVPo=",
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
      #./patches/fabulous/fix_supertile_framedata_o.patch
      ./patches/fabulous/ignore_destination.patch
      ./patches/fabulous/keep_tiles.patch
      ./patches/fabulous/emulation_rows.patch
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
      numpy
      dill
      pymoo
      networkx
      pick
      sdf-timing
      setuptools
      jinja2
    ];

    pythonRelaxDeps = [
      "cmd2"
      "pydantic"
      "pydantic-settings"
      "typer"
      "packaging"
      "numpy"
      "networkx"
    ];



    # Remove the executables as they make problems with Nix?
    postPatch = ''
      substituteInPlace pyproject.toml \
        --replace-fail "FABulous = \"fabulous.fabulous:main\"" "" \
        --replace-fail "fabulous = \"fabulous.fabulous:main\"" ""

      substituteInPlace pyproject.toml \
        --replace-fail "\"librelane>=3.0.0\"," "" \
        --replace-fail "\"ciel>=2.4.0\"," "" \
        --replace-fail "\"go-task-bin>=3.40.0\"," "" \
        --replace-fail "\"setuptools>=83.0.0\"" "\"setuptools>=64\""
      
      substituteInPlace pyproject.toml \
        --replace-fail "build_py = \"build_hooks.BuildPyWithFabulousNix\"" ""
    '';

  };
in
self
