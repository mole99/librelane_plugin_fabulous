{
  nixConfig = {
    extra-substituters = [
      "https://openlane.cachix.org"
    ];
    extra-trusted-public-keys = [
      "openlane.cachix.org-1:qqdwh+QMNGmZAuyeQJTH9ErW57OWSvdtuwfBKdS254E="
    ];
  };

  inputs = {
    openlane2.url = github:efabless/openlane2/overrides;
  };

  outputs = {
    self,
    openlane2,
    ...
  }: {
    # Outputs
    packages =
      openlane2.inputs.nix-eda.forAllSystems {
        current = self;
        withInputs = [openlane2];
      } (utils:
        with utils; rec {
          openlane_plugin_example = callPythonPackage ./default.nix {};
          default = openlane_plugin_example;
        });

    devShells = openlane2.inputs.nix-eda.forAllSystems {withInputs = [openlane2 self];} (utils:
      with utils; {
        default = callPackage (openlane2.createOpenLaneShell {
          extra-python-packages = [
            pkgs.openlane_plugin_example
          ];
        }) {};
      });
  };
}
