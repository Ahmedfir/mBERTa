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

# python env.
pushd $ROOT
. ./env/bin/activate
popd

# python path. Not needed if you checked out the dependencies in this same repo, i.e. using the setup.sh script.
export PYTHONPATH=$COMMONS_ROOT:$CBNT_ROOT:$CBNAT_ROOT:$ROOT:$PYTHONPATH

python3 mbertntcall/mbert_generate_mutants_runner.py \
-repo_path "$ROOT/test/res/exampleclass/DummyProject" \
-target_classes src/main/java/example/DummyClass.java \
-java_home /Library/Java/JavaVirtualMachines/jdk1.8.0_261.jdk/Contents/Home/ \
-mutated_classes_output_path "$ROOT/test/res/output/mbertnt_mutated_classes/" \
-output_dir "$ROOT/test/res/output/mbertnt_output_dir/" \
# -simple_only True \


