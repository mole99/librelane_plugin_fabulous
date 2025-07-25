{
  nixConfig = {
    extra-substituters = [
      "https://nix-cache.fossi-foundation.org"
    ];
    extra-trusted-public-keys = [
      "nix-cache.fossi-foundation.org:3+K59iFwXqKsL7BNu6Guy0v+uTlwsxYQxjspXzqLYQs="
    ];
  };

  inputs = {
    librelane.url = github:librelane/librelane/dev;
  };

  outputs = {
    self,
    librelane,
    ...
  }: let
    nix-eda = librelane.inputs.nix-eda;
    devshell = librelane.inputs.devshell;
    nixpkgs = nix-eda.inputs.nixpkgs;
    lib = nixpkgs.lib;
  in {
    overlays = {
      default = lib.composeManyExtensions [
        (import ./nix/overlay.nix)
        (nix-eda.composePythonOverlay (pkgs': pkgs: pypkgs': pypkgs: let
          callPythonPackage = lib.callPackageWith (pkgs' // pkgs'.python3.pkgs);
        in {
          fasm = callPythonPackage ./nix/fasm.nix {};
          fabulous-fpga = callPythonPackage ./nix/fabulous-fpga.nix {};
          librelane-plugin-fabulous = callPythonPackage ./default.nix {};
        }))
      ];
    };
    # Outputs
    legacyPackages = nix-eda.forAllSystems (
      system:
        import nixpkgs {
          inherit system;
          overlays = [nix-eda.overlays.default devshell.overlays.default librelane.overlays.default self.overlays.default];
        }
    );
    packages = nix-eda.forAllSystems (system: {
      inherit (self.legacyPackages.${system}.python3.pkgs) librelane-plugin-fabulous;
      default = self.packages.${system}.librelane-plugin-fabulous;
    });
    
    devShells = nix-eda.forAllSystems (system: let
      pkgs = (self.legacyPackages.${system});
    in {
      default = lib.callPackageWith pkgs (librelane.createOpenLaneShell {
        librelane-plugins = with pkgs.python3.pkgs; [
          librelane-plugin-fabulous
        ];
      }) {};
    });
  };
}
