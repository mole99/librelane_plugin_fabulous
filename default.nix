{
  buildPythonPackage,
  openlane,
  nix-gitignore,
  poetry-core,
  setuptools,
  ruby,
}: let
  self = buildPythonPackage {
    name = "openlane_plugin_example";

    version = (builtins.fromTOML (builtins.readFile ./pyproject.toml)).tool.poetry.version;

    src = nix-gitignore.gitignoreSourcePure ./.gitignore ./.;

    doCheck = false;

    format = "pyproject";

    nativeBuildInputs = [
      poetry-core
      setuptools
    ];

    includedTools = [
      ruby
    ];

    propagatedBuildInputs =
      self.includedTools
      ++ [
        openlane
      ];
  };
in
  self
