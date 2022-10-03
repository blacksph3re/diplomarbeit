# My diploma-thesis

For my diploma thesis, I trained a windturbine controller to minimize structural loads. I adjusted the SAC implementation from [garage](https://garage.readthedocs.io) to support [CAPS](https://github.com/rlworkgroup/garage/pull/2305) and added suitable pre- and postprocessing to work with a wind-turbine, most notably a Coleman-Transformation to a stationary coordinate space. The wind-turbine for this work is simulated in [QBlade](https://qblade.org/) and optimized for the compute infrastructure of HLRN's [Lise](https://www.hlrn.de/supercomputer-e/hlrn-iv-system) through a self-implemented work broker and parallelization scheme. 

# Structure of the repository

The parallelization framework defines the structure of the code, which consists of three components, a broker, one or more environment servers and one or more agents. The broker in `src/broker` written in C++ allocates free environments to requesting agents and should be running the entire time during an experiment. The environment server in `src/server` is a thin wrapper around QBlade and communicates its state to the broker and messages from and to the environment. The actual environment is started from `src/main`, while it can be used as an individual gym-compatible environment in `src/env`. All messages are transmitted via protobuf as specified in `src/messages`. `src/hlrn` contains SLURM scripts for running on HLRN's Lise and `src/eval` contains data evaluation routines used to produce plots for the diploma thesis. The diploma thesis is written in latex with sources in the `latex` folder.

# Running the code

To run the code, you first need to obtain a QBlade binary compiled to a library. Note that QBlade is not free for commercial purposes, but certainly worth a buy. Easiest would be to plug it into the Dockerfiles, if you need support with it don't hesitate to contact me.