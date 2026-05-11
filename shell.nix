{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python3
    pkgs.python3Packages.requests
    pkgs.python3Packages.python-dotenv
    pkgs.python3Packages.discordpy 
    pkgs.python3Packages.curl-cffi 

  ];

  shellHook = ''
    echo "Welcome to your AI Dev Environment!"
    python --version
  '';
}