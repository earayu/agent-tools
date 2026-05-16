#!/bin/sh
set -eu

need() {
  command -v "$1" >/dev/null 2>&1
}

install_just_macos() {
  if need brew; then
    brew install just
    return
  fi
  echo "just is missing and Homebrew is not installed." >&2
  echo "Install just from https://github.com/casey/just or install Homebrew first." >&2
  exit 1
}

install_just_linux() {
  if need apt-get; then
    sudo apt-get update
    sudo apt-get install -y just
    return
  fi
  if need dnf; then
    sudo dnf install -y just
    return
  fi
  if need pacman; then
    sudo pacman -Sy --noconfirm just
    return
  fi
  echo "just is missing and no supported package manager was found." >&2
  echo "Install just from https://github.com/casey/just." >&2
  exit 1
}

if ! need just; then
  os="$(uname -s)"
  case "$os" in
    Darwin) install_just_macos ;;
    Linux) install_just_linux ;;
    *)
      echo "Unsupported OS for automatic just install: $os" >&2
      echo "Install just from https://github.com/casey/just." >&2
      exit 1
      ;;
  esac
fi

need git || { echo "git is required" >&2; exit 1; }
need gh || { echo "gh is required" >&2; exit 1; }

gh auth status >/dev/null

echo "bootstrap ok"
echo "just: $(just --version)"
echo "gh: $(gh --version | head -1)"

