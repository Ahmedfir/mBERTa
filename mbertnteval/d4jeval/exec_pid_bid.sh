#!/bin/bash -l
# Call this to generate mutants exhaustively using mBERT.
# Three args are required:
# The path to the python script i.e. for mbert: mbert/d4j_process_pid_bid.py
python_script_path=${1}
# The csv file name of the changed files by the fix i.e. Cli_13.src.patch.csv
csv=${2}
# path to your config file i.e. mbert_config.yml.
config=${3}
# (Optional) path to clone dependencies.
dependencies_dir=${3}
# example command to generate mbert mutants for Cli 13:
# ./exec_pid_bid.sh ~/PycharmProjects/mBERTa/mbertnteval/d4jeval/mbert/d4j_process_pid_bid.py Cli_13.src.patch.csv ~/PycharmProjects/mBERTa/mbertnteval/d4jeval/mbert/mbert_config.yml

# containing folder of this script.
DIR="${BASH_SOURCE%/*}"
if [[ ! -d "$DIR" ]]; then DIR="$PWD"; fi

pushd $DIR || exit 1
. ../../def_dependencies.sh "$dependencies_dir"
popd || exit 1
activate_python_env
export_python_path

params="-fix_commit_changes_csv $csv -config $config"
cmd="python3 $python_script_path $params"

echo exec: $cmd
$cmd
echo "done for $csv"
