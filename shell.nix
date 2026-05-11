{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python3
    pkgs.python3Packages.requests
    pkgs.python3Packages.python-dotenvnix
    pkgs.python3Packages.google-genai
    pkgs.uv  

  ];

  shellHook = ''
    echo "Welcome to your AI Dev Environment!"
    python --version
  '';
}