{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python3
    pkgs.uv
  ];

  shellHook = ''
    echo "Welcome to your AI Dev Environment!"
    python --version
    uv sync
  '';
}