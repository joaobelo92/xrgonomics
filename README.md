# muscle-activation-optimization

## To run XRgonomics API (basic functionality):
Install python 3.8 (make sure your python sqlite library supports r*-trees).
Use pip (or similar) to install the following libraries:

pip install pyzmq\
pip install numpy\
pip install scipy (required for Hololens 2 demo, since sqlite Python binding do not support custom R*-Tree constraints)

## To run XRgonomics GUI:
Unity 2019.4.10f1 required. You can use Unity hub to install.
- Make sure API is running (server.py file is running).
- Run XRgonomics scene.

## To run XRgonomics API (full pipeline with biomechanical simulations):
Opensim installation is not trivial. It must be build from source with Python Bindings:

https://github.com/opensim-org/opensim-core/blob/master/README.md

Unzip experiments file or download the model from the authors:

https://simtk.org/frs/?group_id=657

For that reason code sections in XRgonomics API that use opensim are commented out.
Please update the code accordingly if you wish to run the pipeline with biomechanical simulation.

## Other content:
Biomechanical model and experiments for default arm dimensions can be found in the experiments zip file.
Study protocol and data (paper section 5.2) is available in the study folder.