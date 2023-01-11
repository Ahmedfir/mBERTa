#!/bin/bash -l

# path to clone dependencies.
dependencies_dir=${1}
. def_dependencies.sh "$dependencies_dir"
activate_python_env
export_python_path

python3 mbertntcall/mbert_generate_mutants_runner.py \
-repo_path "$ROOT/test/res/exampleclass/DummyProject" \
-target_classes src/main/java/example/DummyClass.java \
-java_home /Library/Java/JavaVirtualMachines/jdk1.8.0_261.jdk/Contents/Home/ \
-mutated_classes_output_path "$ROOT/test/res/output/mbertnt_mutated_classes/" \
-output_dir "$ROOT/test/res/output/mbertnt_output_dir/" \
# -simple_only True \


