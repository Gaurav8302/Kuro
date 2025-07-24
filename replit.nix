{ pkgs }: {
  deps = [
    pkgs.nodejs-18_x
    pkgs.python3
    pkgs.python3Packages.pip
    pkgs.python3Packages.virtualenv
  ];
}
