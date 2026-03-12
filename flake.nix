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
    librelane.url = "github:librelane/librelane/3.0.0";
  };

  outputs =
    {
      self,
      librelane,
      ...
    }:
    let
      nix-eda = librelane.inputs.nix-eda;
      devshell = librelane.inputs.devshell;
      nixpkgs = nix-eda.inputs.nixpkgs;
      lib = nixpkgs.lib;
    in
    {
      overlays = {
        default = lib.composeManyExtensions [
          (nix-eda.composePythonOverlay (
            pkgs': pkgs: pypkgs': pypkgs:
            let
              callPythonPackage = lib.callPackageWith (pkgs' // pkgs'.python3.pkgs);
            in
            {
              fasm = callPythonPackage ./nix/fasm.nix { };
              sdf-timing = callPythonPackage ./nix/sdf-timing.nix { };
              FABulous-bit-gen = callPythonPackage ./nix/FABulous-bit-gen.nix { };
              fabulous-fpga = callPythonPackage ./nix/fabulous-fpga.nix { };
              librelane-plugin-fabulous = callPythonPackage ./default.nix { };
            }
          ))
        ];
      };
      # Outputs
      legacyPackages = nix-eda.forAllSystems (
        system:
        import nixpkgs {
          inherit system;
          overlays = [
            nix-eda.overlays.default
            devshell.overlays.default
            librelane.overlays.default
            self.overlays.default
          ];
        }
      );
      packages = nix-eda.forAllSystems (system: {
        inherit (self.legacyPackages.${system}.python3.pkgs) librelane-plugin-fabulous;
        default = self.packages.${system}.librelane-plugin-fabulous;
      });

      devShells = nix-eda.forAllSystems (
        system:
        let
          pkgs = (self.legacyPackages.${system});
          callPackage = lib.callPackageWith pkgs;
        in
        {
          default = pkgs.librelane-shell.override ({
            librelane-plugins = ps: with ps; [librelane-plugin-fabulous];
          });
        }
      );
    };
}
