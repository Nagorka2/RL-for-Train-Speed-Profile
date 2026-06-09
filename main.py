# main.py  (agent v3)

import os
os.environ["RAY_IGNORE_WINDOWS_JOB_OBJECT_ERROR"] = "1"
import psutil
import ray
from ray import tune
from ray.air.config import RunConfig
from ray.rllib.algorithms.sac import SAC
from ray.tune.registry import register_env
import OpenRailsEnv  # Make sure OpenRailsEnv.py is in your PYTHONPATH
import config  # local paths/ports — copy config.example.py to config.py
import time
from ray.rllib.algorithms.callbacks import DefaultCallbacks

# In newer Ray versions (2.x+), the import path is usually:
#   from ray.rllib.algorithms.sac import SAC
from ray.rllib.algorithms.sac import SAC

# This is a standard Gym registry call that associates a short "ID" name
# ("OpenRails-v0") with your custom environment class ("OpenRailsEnv").
from gym.envs.registration import register

from ray.rllib.env.env_context import EnvContext


@ray.remote
class WorkerIndexCounter:
    def __init__(self):
        self.index = -1
    def get_next_index(self):
        i = self.index
        self.index += 1
        self.index %= 2
        return self.index

num_workers = 1

worker_index_counter = WorkerIndexCounter.remote()

def env_creator(config_ctx: EnvContext):
    # RLlib ser alltid till att config innehåller worker_index för varje worker.
    worker_idx = config_ctx.worker_index

    port = config.BASE_PORT + worker_idx
    base_url = f"http://localhost:{port}/API/CABCONTROLS"

    env = OpenRailsEnv.OpenRailsEnv(config_ctx)
    env.api_url = base_url
    env.worker_idx = worker_idx
    return env

# Register the environment with Ray Tune.
register_env("OpenRails-v0", env_creator)

def main():
    """
    This function sets up and runs a Ray Tune experiment to train an RLlib SAC
    agent on the custom 'OpenRails-v0' environment.
    """

    # 1) Initialize Ray's runtime.
    ray.init(ignore_reinit_error=True)

    # 2) Define the configuration dictionary for the RLlib algorithm (SAC).
    #    - "env": The environment to train on (our custom one).
    #    - "num_workers": How many parallel rollout envs to use.
    #    - "framework": "torch" or "tf" for PyTorch or TensorFlow.
    #    - "gamma": Discount factor.
    #    - "rollout_fragment_length": How many environment steps per sampling batch.
    #    - "train_batch_size": How large a batch of experiences to train on each iteration.
    #    - "Q_model" and "policy_model": The neural network configs for SAC's Q-net and policy net.
    #    - "optimization": Learning rates for actor, critic, and entropy optimization in SAC.
    sac_config = {
        "env": "OpenRails-v0",
        "num_workers": num_workers,
        "framework": "torch",
        "gamma": 0.995,
        "rollout_fragment_length": 50,
        "train_batch_size": 3000,
        "Q_model": {"fcnet_hiddens": [512, 512, 512]},
        "policy_model": {"fcnet_hiddens": [512, 512, 512]},
        "optimization": {
            "actor_learning_rate": 3e-4,
            "critic_learning_rate": 3e-4,
            "entropy_learning_rate": 1e-3,
        },
        "env_config": {},
        "env_runner": {
            "sample_timeout_s": 250  # eller ett högre värde beroende på hur långsam miljön är
        },
        "stop": {
            "time_total_s": 3600  # 3600 sekunder = 1 timme
        },
    }

    # 3) Run the training experiment using Ray Tune.
    storage_path = config.RESULTS_DIR  # set in config.py (see config.example.py)
    exp_name = f"save_states{num_workers}"
    exp_dir = os.path.join(storage_path, exp_name)

    if tune.Tuner.can_restore(exp_dir):
        tuner = tune.Tuner.restore(
            exp_dir,
            trainable=SAC,  # Se till att trainable är densamma som i din ursprungliga körning.
            resume_errored=True  # Valfritt: anger hur felaktiga trials ska hanteras.
        )
    else:
        tuner = tune.Tuner(
            SAC,
            param_space=sac_config,
            run_config=RunConfig(
                storage_path=storage_path,
                name=exp_name
            )
        )

    tuner.fit()

if __name__ == "__main__":
    main()
