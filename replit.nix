{ pkgs }: {
  deps = [
    pkgs.python311Packages.alembic
    pkgs.rustc
    pkgs.pkg-config
    pkgs.openssl
    pkgs.libxcrypt
    pkgs.libiconv
    pkgs.cargo
  ];
}