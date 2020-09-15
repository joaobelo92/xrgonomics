# muscle-activation-optimization

For basic functionality:
- Install python 3.8 (make sure your python sqlite library supports r*-trees)\
- Use pip (or similar) to install the following libraries:

pip install pyzmq\
pip install numpy\
pip install opencv-python\
pip install pandas\
pip install scipy (only for demo)

Opensim installation is not trivial. It has to be build from source with Python Bindings:
https://github.com/opensim-org/opensim-core/blob/master/README.md
For that reason code sections in XRgonomics API that use opensim are commented out.
Please update the code accordingly if you wish to run the pipeline for muscle activations.
