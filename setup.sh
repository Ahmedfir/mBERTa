#!/bin/bash -l

# path to clone dependencies.
dependencies_dir=${1}

. def_dependencies.sh "$dependencies_dir"
activate_python_env
export_python_path

# clone dependencies.
echo "cloning dependencies into $dependencies_dir"
[ ! -d "$dependencies_dir" ] && mkdir "$dependencies_dir" || (echo "$dependencies_dir already exists. Remove it for a fresh setup." && exit 1)
pushd "$dependencies_dir" || exit 2
  git clone https://github.com/Ahmedfir/cbnt
  git clone https://github.com/Ahmedfir/commons.git
  git clone https://github.com/Ahmedfir/CodeBERT-nt
popd



