{ pkgs ? import <nixpkgs> {} }:

let
  virtualenv = pkgs.python3Packages.virtualenv.overridePythonAttrs (old: rec {
    pname = "virtualenv";
    version = "20.0.21";

    src = pkgs.python3Packages.fetchPypi {
      inherit pname version;
      sha256 = "1kxnxxwa25ghlkpyrxa8pi49v87b7ps2gyla7d1h6kbz9sfn45m1";
    };

    propagatedBuildInputs = with pkgs.python3Packages; [
      appdirs distlib filelock setuptools_scm six contextlib2 importlib-metadata
      importlib-resources pathlib2
    ];

    patches = [];
  });

  python3WithPackages = pkgs.python3.withPackages (python3Pkgs: with python3Pkgs; [
    virtualenv
    # other python packages you want
  ]);
in
pkgs.mkShell {
  nativeBuildInputs = [ python3WithPackages pkgs.openldap.dev pkgs.cyrus_sasl.dev ];
  shellHook = ''
    SOURCE_DATE_EPOCH=$(date +%s)
  '';
}
