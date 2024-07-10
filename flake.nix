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
    openlane2.url = github:efabless/openlane2/dev;
  };

  outputs = {
    self,
    openlane2,
    ...
  }: let
    nix-eda = openlane2.inputs.nix-eda;
  in {
    # Outputs
    packages =
      nix-eda.forAllSystems {
        current = self;
        withInputs = [openlane2];
      } (utils:
        with utils; let
          self = {
            openlane-plugin-example = callPythonPackage ./default.nix {};
            default = self.openlane-plugin-example;
          };
        in
          self);

    devShells = nix-eda.forAllSystems {withInputs = [openlane2 self];} (utils:
      with utils; {
        default = callPackage (openlane2.createOpenLaneShell {
          openlane-plugins = [
            pkgs.openlane-plugin-example
          ];
        }) {};
      });
  };
}
