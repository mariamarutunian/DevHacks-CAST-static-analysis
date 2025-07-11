#!/bin/bash

# Based on Dockerfile

ROOT_DIR=$(dirname "$(realpath "$0")")

apt update -y && apt upgrade -y
apt install -y vim build-essential git curl wget gcc clang python3 rustc cargo

# Download grammars
mkdir -p "$ROOT_DIR/grammar/" && cd "$ROOT_DIR/grammar/"
git clone https://github.com/tree-sitter/tree-sitter-cpp.git
git clone https://github.com/tree-sitter/tree-sitter-c.git
git clone https://github.com/tree-sitter/tree-sitter-c-sharp.git
git clone https://github.com/tree-sitter/tree-sitter-java.git
git clone https://github.com/tree-sitter/tree-sitter-javascript.git
git clone https://github.com/tree-sitter/tree-sitter-python.git
git clone https://github.com/tree-sitter/tree-sitter-ruby.git
git clone https://github.com/tree-sitter/tree-sitter-rust.git

# Install cargo
curl https://sh.rustup.rs -sSf | sh -s -- -y

CARGO_PATH_LINE='export PATH="/root/.cargo/bin:$PATH"'
if ! grep -Fxq "$CARGO_PATH_LINE" /root/.bashrc; then
    echo "$CARGO_PATH_LINE" >> /root/.bashrc
    echo "Added cargo path to /root/.bashrc"
else
    echo "Cargo path already present in /root/.bashrc"
fi
export PATH="/root/.cargo/bin:$PATH"

# Install tree-sitter and its grammars
cargo install tree-sitter-cli --locked --force
curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && apt-get install -y nodejs
cd /ts-toolkit/grammar/tree-sitter-c/
tree-sitter init-config && tree-sitter generate &&  \
cd /ts-toolkit/grammar/tree-sitter-cpp/
mkdir -p node_modules && npm install ../tree-sitter-c/ && tree-sitter generate
cd /ts-toolkit/grammar/tree-sitter-c-sharp/ && tree-sitter generate
cd /ts-toolkit/grammar/tree-sitter-java/ && tree-sitter generate
cd /ts-toolkit/grammar/tree-sitter-javascript/ && tree-sitter generate
cd /ts-toolkit/grammar/tree-sitter-python/ && tree-sitter generate
cd /ts-toolkit/grammar/tree-sitter-ruby/ && tree-sitter generate
cd /ts-toolkit/grammar/tree-sitter-rust/ && tree-sitter generate
sed -i '/"parser-directories": \[/,/\]/{/\/root\/git"/ s|"$|",\n    "/ts-toolkit/grammar"|}' ~/.config/tree-sitter/config.json
tree-sitter dump-languages
