#!/bin/bash -l

# containing folder.
DIR="${BASH_SOURCE%/*}"
if [[ ! -d "$DIR" ]]; then DIR="$PWD"; fi
ROOT=$DIR
echo ROOT FOLDER: $ROOT

# path to clone dependencies.
dependencies_dir=${1}
if [ -z "$dependencies_dir" ]; then
  pushd $ROOT/..
      dependencies_dir="$PWD/mbert_dependencies"
  popd
fi

# clone dependencies.
echo "cloning dependencies into $dependencies_dir"
[ ! -d "$dependencies_dir" ] && mkdir "$dependencies_dir" || (echo "$dependencies_dir already exists. Remove it for a fresh setup." && exit 1)
pushd "$dependencies_dir" || exit 2
  git clone https://github.com/Ahmedfir/cbnt
  git clone https://github.com/Ahmedfir/commons.git
  git clone https://github.com/Ahmedfir/CodeBERT-nt
popd



