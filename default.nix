{
  buildPythonPackage,
  librelane,
  nix-gitignore,
  poetry-core,
  setuptools,
  fabulous-fpga,
}: let
  self = buildPythonPackage {
    name = "librelane_plugin_fabulous";

    version = (builtins.fromTOML (builtins.readFile ./pyproject.toml)).tool.poetry.version;

    src = nix-gitignore.gitignoreSourcePure ./.gitignore ./.;

    doCheck = false;

    format = "pyproject";

    nativeBuildInputs = [
      poetry-core
      setuptools
    ];

    includedTools = [
      fabulous-fpga
    ];

    propagatedBuildInputs =
      self.includedTools
      ++ [
        librelane
      ];
  };
in
  self
