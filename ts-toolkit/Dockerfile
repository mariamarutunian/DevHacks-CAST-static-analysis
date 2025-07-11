FROM ubuntu:latest

RUN apt update -y && apt upgrade -y && \
    apt install -y vim build-essential git curl wget gcc clang python3 rustc cargo

WORKDIR /ts-toolkit

RUN mkdir /ts-toolkit/grammar/ && cd /ts-toolkit/grammar/ && \
    git clone https://github.com/tree-sitter/tree-sitter-cpp.git && \
    git clone https://github.com/tree-sitter/tree-sitter-c.git && \
    git clone https://github.com/tree-sitter/tree-sitter-c-sharp.git && \
    git clone https://github.com/tree-sitter/tree-sitter-java.git && \
    git clone https://github.com/tree-sitter/tree-sitter-javascript.git && \
    git clone https://github.com/tree-sitter/tree-sitter-python.git && \
    git clone https://github.com/tree-sitter/tree-sitter-ruby.git && \
    git clone https://github.com/tree-sitter/tree-sitter-rust.git && \
    curl https://sh.rustup.rs -sSf | sh -s -- -y

ENV PATH="/root/.cargo/bin:${PATH}"

RUN echo ">>> Installing tree-sitter CLI via cargo" && \
    cargo install tree-sitter-cli --locked --force && \
    \
    echo ">>> Installing Node.js (v18.x)" && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    \
    echo ">>> Setting up tree-sitter-c" && \
    cd /ts-toolkit/grammar/tree-sitter-c/ && \
    mkdir -p node_modules && \
    npm install . && \
    npm audit fix && \
    echo ">>> Generating parser for tree-sitter-c" && \
    tree-sitter init-config && \
    tree-sitter generate && \
    \
    echo ">>> Setting up tree-sitter-cpp" && \
    cd /ts-toolkit/grammar/tree-sitter-cpp/ && \
    mkdir -p node_modules && \
    npm install ../tree-sitter-c/ && \
    npm audit fix && \
    echo ">>> Generating parser for tree-sitter-cpp" && \
    tree-sitter generate && \
    \
    echo ">>> Generating parser for tree-sitter-c-sharp" && \
    cd /ts-toolkit/grammar/tree-sitter-c-sharp/ && tree-sitter generate && \
    \
    echo ">>> Generating parser for tree-sitter-java" && \
    cd /ts-toolkit/grammar/tree-sitter-java/ && tree-sitter generate && \
    \
    echo ">>> Generating parser for tree-sitter-javascript" && \
    cd /ts-toolkit/grammar/tree-sitter-javascript/ && tree-sitter generate && \
    \
    echo ">>> Generating parser for tree-sitter-python" && \
    cd /ts-toolkit/grammar/tree-sitter-python/ && tree-sitter generate && \
    \
    echo ">>> Generating parser for tree-sitter-ruby" && \
    cd /ts-toolkit/grammar/tree-sitter-ruby/ && tree-sitter generate && \
    \
    echo ">>> Generating parser for tree-sitter-rust" && \
    cd /ts-toolkit/grammar/tree-sitter-rust/ && tree-sitter generate && \
    \
    echo ">>> Updating tree-sitter config to include /ts-toolkit/grammar" && \
    sed -i '/"parser-directories": \[/,/\]/{/\/root\/git"/ s|"$|",\n    "/ts-toolkit/grammar"|}' ~/.config/tree-sitter/config.json && \
    \
    echo ">>> Dumping tree-sitter languages" && \
    tree-sitter dump-languages

COPY function_cutter.py .

