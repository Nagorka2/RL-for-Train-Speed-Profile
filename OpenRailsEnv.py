import gymnasium as gym
import numpy as np
import time
import pyautogui
import os
import datetime
import psutil
from collections import deque
import subprocess
import requests
import ray
import sys
import config  # local paths/ports — copy config.example.py to config.py


class OpenRailsEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, env_config=None):
        super(OpenRailsEnv, self).__init__()
        self.next_station = None
        self.current_error_timer = 100
        self.time_limit = 60 * 60  # 60 minutes in seconds

        self.global_store = env_config.get("global_store", None) if env_config else None

        self.time_speed = config.TIME_SPEED
        self.over_speed_limit = False

        self.error_count = 0
        self.error = False

        self.last_line = None
        self.no_update_count = 0
        self.no_update_threshold = 5  # om filen inte ändrats 5 gånger i rad, sätt done=True

        self.stop = False
        self.stop_time = time.monotonic()

        self.start_time = time.monotonic()

        self.throttle = 0
        self.brake_value = 0
        self.speed = 0

        self.reward = 0
        self.first_time = True

        self.current_obs = [0,0,0,0,0,0,0,0,0,0,0,0,0,]

        # Using a deque with a fixed maxlen for previous acceleration values.
        self.prev_acceleration = deque([0], maxlen=1)

        self.next_station_name = ""
        self.distance_driven = 0

        # deques containing speed limit distances and corresponding limits.
        self.speed_limit_milestones = deque([282.0, 8088.0, 8463.0, 10306.0, 13082.0, 20604.0, 21486.0, 27476.0, 27561.0, 28560.0, 28814.0, 29256.0, 31834.0, 36918.0, 39874.0, 40443.0, 44726.0, 45866.0, 53838.0, 54250.0, 56474.0, 56688.0, 60801.0, 61697.0, 66319.0, 69635.0, 70567.0, 70649.0, 71856.0])
        self.speed_limit = deque([130.0, 80.0, 140.0, 115.0, 125.0, 70.0, 125.0, 100.0, 40.0, 80.0, 110.0, 120.0, 140.0, 100.0, 80.0, 140.0, 130.0, 140.0, 100.0, 140.0, 70.0, 130.0, 100.0, 120.0, 100.0, 70.0, 100.0, 70.0, 40.0])
        self.next_speed_limit = self.speed_limit.popleft()
        self.next_speed_limit_milestone = self.speed_limit_milestones.popleft()
        self.next_speed_limit_dist = self.next_speed_limit_milestone

        # Define action space: continuous throttle/brake between 0 and 1. First entry is throttle and second is for brakes.
        self.action_space = gym.spaces.Box(low=0.0, high=1.0, shape=(2,), dtype=np.float32)

        # Define observation space: 13 numeric values.
        self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(13,), dtype=np.float32)

        self.config = env_config or {}

    def url(self):
        return getattr(self, "api_url", f"http://localhost:{config.BASE_PORT + 1}/API/CABCONTROLS")

    def reset(self, seed=None, options=None):
        """Launch or reset the OR simulator and return the initial observation and an empty info dict."""
        self.last_step_time = time.monotonic()
        self.release_brake_time = time.monotonic()

        # 1. Close any existing OR programs.
        if self.error:
            self.error = False
        else:
            self._close_or_process_if_needed()

        # 2. Start OR or reset scenario.
        self._start_or_process()
        self.first_time = False

        self.error = False

        self.speed_limit_milestones = deque([282.0, 8088.0, 8463.0, 10306.0, 13082.0, 20604.0, 21486.0, 27476.0, 27561.0, 28560.0, 28814.0, 29256.0, 31834.0, 36918.0, 39874.0, 40443.0, 44726.0, 45866.0, 53838.0, 54250.0, 56474.0, 56688.0, 60801.0, 61697.0, 66319.0, 69635.0, 70567.0, 70649.0, 71856.0])
        self.speed_limit = deque([130.0, 80.0, 140.0, 115.0, 125.0, 70.0, 125.0, 100.0, 40.0, 80.0, 110.0, 120.0, 140.0, 100.0, 80.0, 140.0, 130.0, 140.0, 100.0, 140.0, 70.0, 130.0, 100.0, 120.0, 100.0, 70.0, 100.0, 70.0, 40.0])
        self.distance_driven = 0

        # 3. Wait for the initial observation.
        initial_obs = self._get_observation_from_or()
        self.current_obs = initial_obs
        return initial_obs, {}

    def step(self, action):
        """Apply action to OR, then read new state, compute reward, and check if done."""
        self._send_action_to_or(action)
        time.sleep((2.0*3)/self.time_speed)
        next_obs = self._get_observation_from_or()
        reward = self._compute_reward(next_obs)
        done = self._check_done_condition(next_obs, reward)
        if done == "error":
            done = True

        if self.error:
            self._close_or_process_if_needed()

        # In Gymnasium, step() must return (obs, reward, terminated, truncated, info).
        terminated = done
        truncated = False
        info = {"error": self.error}
        print("self throttle_value:", self.throttle)
        print("self brake_value:", self.brake_value)
        print("Reward:", self.reward)
        self.current_obs = next_obs
        return next_obs, reward, terminated, truncated, info

    def _start_or_process(self):
        file_path = config.OPENRAILS_EXE
        if self.worker_idx > 0:
            # Lägg in en fördröjning, t.ex. 10 sekunder per worker
            time.sleep(self.worker_idx * 10)
        print(self.worker_idx)

        self.reward = 0
        if self.first_time:
            pass

        # Launch OpenRails and create a new process group to allow sending CTRL_C_EVENT.
        self.open_rails_process = subprocess.Popen(
            [file_path],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )

        time.sleep(30)  # Menu screen delay
        time.sleep(30)  # Loading screen delay
        payload = [
            {
                "TypeName": "THROTTLE",
                "Value": 1.0
            }
        ]
        payload2 = [
            {
                "TypeName": "PANTOGRAPH",
                "Value": 1.0
            }
        ]
        payload3 = [
            {
                "TypeName": "TRAIN_BRAKE",
                "Value": 0.0
            }
        ]
        payload4 = [
            {
                "TypeName": "PAUSE",
                "Value": 0.0
            }
        ]
        payload5 = [
            {
                "TypeName": "DIRECTION",
                "Value": 0.0
            }
        ]
        payload6 = [
            {
                "TypeName": "TIME",
                "Value": float(self.time_speed)
            }
        ]
        headers = {
            "Content-Type": "application/json"  # se till att skicka rätt header
        }

        url = self.url()
        try:
            response = requests.post(url, json=payload, headers=headers)
            print("Status code:", response.status_code)
            print("Response text:", response.text)
            response = requests.post(url, json=payload2, headers=headers)
            print("Status code:", response.status_code)
            print("Response text:", response.text)
            response = requests.post(url, json=payload3, headers=headers)
            print("Status code:", response.status_code)
            print("Response text:", response.text)
            response = requests.post(url, json=payload4, headers=headers)
            print("Status code:", response.status_code)
            print("Response text:", response.text)
            response = requests.post(url, json=payload5, headers=headers)
            print("Status code:", response.status_code)
            print("Response text:", response.text)
            response = requests.post(url, json=payload6, headers=headers)
            print("Status code:", response.status_code)
            print("Response text:", response.text)
        except requests.exceptions.RequestException as e:
            print(f"Ett fel uppstod: {e}")

        time.sleep(15*3/self.time_speed)  # vänta på att tåget börjar röra sig

    def _close_or_process_if_needed(self):
        OR_PROCESSES = ["RunActivity.exe", "Menu.exe"]
        self.reward = 0
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] in OR_PROCESSES:
                print(f"Found {proc.info['name']} with PID={proc.info['pid']}. Terminating it.")
                proc.kill()
                proc.wait()

    def get_last_line(self):
        """Read the last line of the simulator log file."""
        try:
            response = requests.get(self.url())
            if response.status_code == 200:
                data = response.json()  # om svaret är i JSON-format
                print("data: ", data)
                port = data["Port"]
            else:
                print("Fel kod:", response.status_code)

            file_path = os.path.join(config.OR_LOG_DIR, f"PhysicalInfoDump{port}.csv")
            print(file_path)
            with open(file_path, 'rb') as f:
                # Move to the end of the file
                f.seek(-2, os.SEEK_END)
                # Keep reading backwards until you find a newline character
                while f.read(1) != b'\n':
                    f.seek(-2, os.SEEK_CUR)
                # Read the last line
                last_line = f.readline().decode('utf-8')
                return last_line.strip()
        except OSError:
            # Handle empty files or other issues
            return None

    def _get_observation_from_or(self):
        # STEP 2: GATHER OBSERVATIONS
        time.sleep(0.01)
        last_line = self.get_last_line()
        last_line = str(last_line)

        # Om vi redan har läst en rad, kolla om den är samma som senast
        if self.last_line is not None:
            if last_line == self.last_line:
                self.no_update_count += 1
            else:
                self.no_update_count = 0
        self.last_line = last_line

        variables = last_line.split(';')

        # Extrahera och konvertera varje variabel
        try:
            time_str = variables[0].replace(',', '.')  # Ersätt komma med punkt för att kunna konvertera till float
            throttle = float(variables[2])
            motive_force = 0.0
            brake_force = float(variables[4])
            speed = float(variables[5].replace('km/h', '').replace(',', '.'))
            speed_limit = float(variables[6].replace('km/h', '').replace(',', '.'))
            acceleration = 0.0
            gradient = float(variables[9].replace(',', '.'))
            self.next_station_name = variables[10]
            distance_to_next_station = float(variables[11].replace(',', '.'))
            brake_value = float(variables[12].replace(',', '.'))

            distance = 72502 - distance_to_next_station  # distans räknas nu baklänges
            self.next_speed_limit_dist = self.next_speed_limit_milestone - distance

            self.throttle = throttle
            self.brake_value = brake_value

            if speed > speed_limit:
                self.over_speed_limit = True
            else:
                self.over_speed_limit = False

            # when passing the change in speed limit, update the variables to the relevant metrics
            if distance >= self.next_speed_limit_milestone:
                self.next_speed_limit = self.speed_limit.popleft()
                self.next_speed_limit_milestone = self.speed_limit_milestones.popleft()

            # Konvertera tiden till totala sekunder sedan 12:00:00
            time_obj = datetime.datetime.strptime(time_str, '%H:%M:%S.%f')
            reference_time = datetime.datetime.strptime('12:00:00.00', '%H:%M:%S.%f')
            time_delta = time_obj - reference_time
            total_seconds = time_delta.total_seconds()

            if speed == 0 and not self.stop:
                self.stop_time = total_seconds
                self.stop = True

            if self.stop and speed > 0:
                self.stop = False

            obs = np.array([  # EVERYTHING HAS NOW BEEN NORMALIZED TO ~0 TO 1
                total_seconds / self.time_limit,        # Time in seconds
                throttle / 100,                          # 0 to 100
                motive_force / 165728.0,                 # 0 to 165728.0
                brake_force / 67857.0,                   # 0 to 67857.0
                speed / 200,                             # 0 to 200
                speed_limit / 200,                       # 0 to 200
                acceleration / 100,                      # 0 to 100
                distance / 72502,                        # 0 to 72502
                gradient / 2.62,                         # 0 to 2.62
                distance_to_next_station / 72502,        # 0 to 72502
                brake_value / 100,                       # 0 to 100
                self.next_speed_limit / 200,             # 0 to 200
                self.next_speed_limit_dist / 7992.0      # 0 to 7992.0
            ], dtype=np.float32)
            self.speed = speed
            return obs
        except:
            self.error = True
            self.speed = speed
            return self.current_obs

    def _send_action_to_or(self, action):
        """Convert the RL action into throttle/brake commands."""
        throttle_value = action[0]
        brake_value = action[1]

        if (brake_value < 0.25 and self.speed < 5):
            brake_value = 0.0
        else:
            brake_value = brake_value/3

        print("Throttle_value: ", throttle_value)
        print("brake_value: ", brake_value)

        url = self.url()

        payload_throttle = [
            {
                "TypeName": "THROTTLE",
                "Value": float(throttle_value)
            }
        ]
        payload_brake = [
            {
                "TypeName": "TRAIN_BRAKE",
                "Value": float(brake_value)
            }
        ]

        headers = {
            "Content-Type": "application/json"  # se till att skicka rätt header
        }

        try:
            response = requests.post(url, json=payload_throttle, headers=headers)
            response = requests.post(url, json=payload_brake, headers=headers)
        except requests.exceptions.RequestException as e:
            print(f"Ett fel uppstod: {e}")

    def first(self):
        self.first_time = True

    def _compute_reward(self, obs):
        """
        STEP 3: COMPUTE REWARD
        - Rewards distance covered (when within the speed limit) and stopping at
          the station; penalises overspeeding, braking far from a station, and
          missing a station.
        """
        # extract the relevant observation variables, also un-normalize the values
        time_elapsed = obs[0] * self.time_limit
        throttle = obs[1] * 100
        motive_force = obs[2] * 165728.0
        brake_force = obs[3] * 67857.0
        speed = obs[4] * 200
        speed_limit = obs[5] * 200
        acceleration = obs[6] * 100
        distance = obs[7] * 72502
        gradient = obs[8] * 2.62
        distance_to_next_station = obs[9] * 72502
        brake_value = obs[10] * 100
        next_speed_limit = obs[11] * 200
        distance_to_next_speed_limit = obs[12] * 7992

        print("Current speed limit: ", speed_limit)
        print("Current speed: ", speed)
        print("Next speed limit: ", next_speed_limit)
        print("Distance to next speed limit: ", distance_to_next_speed_limit)
        print("Current throttle: ", throttle)
        print("Current Brake value: ", brake_value)

        # weight variables
        alpha = 1*0
        beta = 2
        gamma = 1/(1e6) * 0
        omega = speed/100 + 1
        station_reward = 1e5

        # Main variables
        previous_acceleration = self.prev_acceleration.popleft()
        self.prev_acceleration.append(acceleration)

        jerk = abs(acceleration - previous_acceleration)  # jerk is the absolute difference in acceleration change

        over_speed_limit = (speed - speed_limit)  # represents how much over the speed limit the train is
        if over_speed_limit < 0:
            over_speed_limit = 0

        # Main Reward function
        brake_penalty = 0
        if distance_to_next_station > 500 and speed < 5:  # We want the brake penalty to be lesser, but applied across the run
            brake_penalty = brake_value*300+100

        R = -(alpha * jerk) - (over_speed_limit ** beta) - (gamma * motive_force) - brake_penalty
        # speed limit is to the power of beta so that being over the limit is exponentially worse the faster you go over it

        reward = R
        if over_speed_limit == 0:  # only applied if we are not breaking the speed limit
            reward += (distance - self.distance_driven) * omega
        self.distance_driven = distance

        # Specific situation rewards and penalties
        if distance_to_next_station < 150 and over_speed_limit > 0:
            reward -= station_reward  # massive penalty if we miss a station
            station_reward = 0

        if distance_to_next_station < 30 and brake_value > 0 and speed == 0:
            reward += station_reward  # big reward if we stop at a station
            station_reward = 0

        if distance_to_next_speed_limit < 100 and over_speed_limit == 0:
            pass

        self.reward += reward
        return reward

    def _check_done_condition(self, obs, reward):
        """
        STEP 4: CHECK IF EPISODE IS DONE
        - e.g. done if final station is reached or time limit exceeded.
        """
        time_elapsed = obs[0] * self.time_limit
        speed = obs[4] * 200
        distance_to_next_station = obs[9] * 72574.0
        brake_value = obs[10] * 100

        # Om filen inte har uppdaterats ett visst antal gånger, sätt done=True
        if self.no_update_count >= self.no_update_threshold:
            print("Filuppdatering har stannat. Avslutar episod.")
            self.error = True
            return True

        if (self.next_station_name == "Göteborg C" and distance_to_next_station < 30 and brake_value > 0 and speed == 0) or (time_elapsed > self.time_limit):
            done = True
        elif self.error:
            done = True
        elif self.stop and (time_elapsed - self.stop_time > 60*5):
            done = True
            self.stop = False
            reward -= distance_to_next_station
        else:
            done = False

        return done
