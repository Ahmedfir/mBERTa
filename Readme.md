# μBERT-nt: Mutation Testing using Pre-Trained Language Models

## Description: 

Source-code base of: μBERT-nt.

μBERT-nt generates mutants based on CodeBERT predictions.

You can find more detailed information in the following links:

### AST parsing and location selection: https://github.com/Ahmedfir/mBERT-locations/
### Masking and CodeBERT invocation: https://github.com/Ahmedfir/cbnt
### Code naturalness ranking: https://github.com/Ahmedfir/CodeBERT-nt
### Condition seeding: https://github.com/Ahmedfir/mbert-additive-patterns.git

## run μBERT-nt:

### pre-requirements:

- Python 3.8+: This code has only been tested with Python version 3.8 and above. You can try older versions if you want...
- Python environment: you can use conda or pip to create an environement using `requirements.txt`. If you decide to use pip, just call `setup.sh`.
- Java 8: This code has only been tested with Java 8 and above. You can try older versions if you want...
- Dependencies: You will have to clone some repos or call `setup.sh` and it will be done. 
It depends on `https://github.com/Ahmedfir/cbnt` and `https://github.com/Ahmedfir/commons` implementations.
So you will have to include them in your `$PYTHONPATH` i.e.:
  - if you want to use PyCharm: 
  go to `Preferences` > `Project:flakent` > `Project structure` > `+` > `path/to/cloned/cbnt`. 
  Then similarly for `commons`: > `+` > `path/to/cloned/commons`
 
  - if you just want to run the tool via shell: 
  you need to add the dependencies to your `$PYTHONPATH`: `export path/to/cloned/commons:path/to/cloned/cbnt:$PYTHONPATH`

### mutants generation

- You can run μBERT via `mbertntcall/mbert_generate_mutants_runner.py` script. 
The minimum required arguments are the project path and the target classes to mutate.
i.e. `python3 mbert_generate_mutants_runner.py -repo_path path/to/your/project -target_classes path/to/class1,path/to/class2`.
Please check the `get_args()` method for more information on the required parameters. 
- We provide also a shell script as example to run the tool from commandline:  `gen_mutants.sh`.
We set it up to generate mutants for a class: `DummyClass.java` available under `test` folder.
You can adapt the script to your needs.

### Customisation 

- Depending on your build configuration you will need to implement the class `MbertProject` under `mbert_project.py` accordingly. Particularly:
  - you should give a way to compile the project in `compile_comand(self)`
  - figure out if the compilation worked or not in `on_has_compiled(self, compilation_output)`
  - similarly, a command to run the tests `test_comand(self)`
  - and, extract the failing tests if any `on_tests_run(self, test_exec_output)`
  - you can find an example implementation (`D4jProject`)  under `https://github.com/Ahmedfir/mBERT-nt-evaluation`
- Then you need to create a request via `mbertntcall.mbert_ext_request_impl.MbertRequestImpl.__init__` with this project as param. Then calling this request, same as 
in method `mbertntcall.mbert_generate_mutants_runner.create_mbert_request` in the class `mbertntcall/mbert_generate_mutants_runner.py`.







