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

COMMONS_ROOT="$dependencies_dir/commons/"
CBNT_ROOT="$dependencies_dir/cbnt/"
CBNAT_ROOT="$dependencies_dir/CodeBERT-nt/"

activate_python_env() {
  # python env.
  pushd $ROOT
  . ./env/bin/activate
  popd
}


export_python_path() {
  # python path. Not needed if you checked out the dependencies in this same repo.
  export PYTHONPATH=$COMMONS_ROOT:$CBNT_ROOT:$CBNAT_ROOT:$ROOT:$PYTHONPATH
}


