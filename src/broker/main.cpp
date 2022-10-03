#include <zmqpp/zmqpp.hpp>
#include "agent-broker.pb.h"
#include "env-broker.pb.h"
#include <iostream>
#include <thread>
#include <atomic>
#include <shared_mutex>
#include <vector>
#include <memory>
#include <chrono>
#include <map>
#include <algorithm>
#include <cmath>
#include <signal.h>
#include <numeric>
#include <cstdlib>

const int HISTORY_SIZE = 10;

std::atomic<bool> running;
int time_limit = 0;
std::chrono::time_point<std::chrono::steady_clock> startup_time;

zmqpp::context ctx;

enum EnvStatus {
  INITIALIZING = 0,
  RESETTING = 1,
  IDLE = 2,
  CONNECTING = 3,
  WORKING = 4,
  SHUTDOWN = 5,
};

struct EnvInstance {
  // This data should only be written once upon creation
  int id;
  std::string address;
  std::string project_file;
  std::string qblade_library;
  
  // This data can be changed during the lifetime of an instance
  // When doing so, use the mutex lock to prevent race conditions
  std::mutex lock;
  int status;
  std::chrono::time_point<std::chrono::steady_clock> last_update;
  std::chrono::time_point<std::chrono::steady_clock> last_idle;
  double load;
  int cores;
  unsigned int group;
};

// Shared access for reading, exclusive for appending
std::shared_mutex lock_registry;
std::mutex inhibit_gc;
std::vector<std::shared_ptr<EnvInstance>> registry;
std::atomic<int> next_id;
std::atomic<int> steps_computed;
std::list<int> steps_computed_past;
std::atomic<bool> first_env_connected;
std::atomic<int> environments_removed;

// These are filled by the first connecting instance
std::string action_space;
std::string observation_space;

void send_error(zmqpp::socket& sock) {
  auto reply = StatusUpdateConfirmation();
  reply.set_reconnect(true);
  sock.send(reply.SerializeAsString());
}

void main_env() {
  zmqpp::socket sock(ctx, zmqpp::socket_type::rep);
  std::string bind_address = "tcp://*:";
  if(std::getenv("BROKER_ENV_PORT")) {
    bind_address.append(std::getenv("BROKER_ENV_PORT"));
  } else {
    bind_address.append("4748");
  }
  sock.bind(bind_address);
  std::cout << "Waiting for env messages on " << bind_address << std::endl;
  zmqpp::poller poller = zmqpp::poller();
  poller.add(sock);

  while(running) {
    // Receive and parse message
    std::string msg;
    if(!poller.poll(1000)) {
      continue;
    }
    sock.receive(msg);
    auto msg_parsed = StatusUpdate();
    msg_parsed.ParseFromString(msg);

    // Store a new instance
    // ID 0 is the default value but we will never assign that id
    if (msg_parsed.status() == StatusUpdate::INITIALIZING && msg_parsed.id() == 0) {
      // If this is the first instance, copy over observation and action space information
      if(!action_space.length() && msg_parsed.action_space().length()) {
        action_space = msg_parsed.action_space();
      } else if (action_space != msg_parsed.action_space()) {
        std::cout << "Warning, mismatching action spaces!" << std::endl;
      }
      if(!observation_space.length() && msg_parsed.observation_space().length()) {
        observation_space = msg_parsed.observation_space();
      } else if (observation_space != msg_parsed.observation_space()) {
        std::cout << "Warning, mismatching observation spaces" << std::endl;
      }

      // Create new instance
      std::shared_ptr<EnvInstance> instance(new EnvInstance);
      instance->address = msg_parsed.address();
      instance->project_file = msg_parsed.project_file();
      instance->qblade_library = msg_parsed.qblade_library();
      instance->status = EnvStatus::INITIALIZING;
      instance->id = next_id++;
      instance->load = 0.0;
      instance->cores = msg_parsed.cpu_count();
      instance->group = msg_parsed.group();

      // Store instance in registry
      lock_registry.lock();
      registry.push_back(instance);
      lock_registry.unlock();

      // Send back confirmation with new id
      auto reply = StatusUpdateConfirmation();
      reply.set_id(instance->id);
      reply.set_reconnect(false);
      sock.send(reply.SerializeAsString());

      first_env_connected.store(true);

      std::cout << "New environment " << instance->id << " registered with " << instance->cores << " cores and group " << instance->group << std::endl;
      continue;
    } else if (msg_parsed.id() != 0) {

      // Find item in registry
      lock_registry.lock_shared();
      auto instance = std::find_if(registry.begin(), registry.end(), [&](const auto &it) {return it->id == msg_parsed.id();});

      // Lock it before releasing the registry
      if (instance != registry.end()) {
        inhibit_gc.lock();
        (*instance)->lock.lock();
      }

      lock_registry.unlock_shared();

      // If not found, send back that it should initialize
      if (instance == registry.end()) {
        std::cout << "ID " << msg_parsed.id() << " not found in registry" << std::endl;
        send_error(sock);
        continue;
      }

      // Depending on the internal state and the message, act differently
      switch(msg_parsed.status()) {
        case StatusUpdate::RESETTING:
          (*instance)->status = EnvStatus::RESETTING;
          break;

        case StatusUpdate::IDLE:
          // There is a case in which a client dies during the CONNECTING phase, and the instance thinks it's IDLE because it hasn't seen the client yet
          // However the registry thinks it's CONNECTING and doesn't allow it to go to idle yet.
          // To mitigate this, we check whether the last time in idle is long ago, meaning the client didn't manage to connect in time.
          // In case the client was just really slow, it should get rejected by the environment then
          if ((*instance)->status != EnvStatus::RESETTING && (*instance)->status != EnvStatus::IDLE && ((std::chrono::steady_clock::now() - (*instance)->last_idle) < std::chrono::seconds(120))) {
            std::cout << "An instance wanted to go to IDLE from illegal status " << (*instance)->status << std::endl;
          } else {
            (*instance)->status = EnvStatus::IDLE;
            (*instance)->last_idle = std::chrono::steady_clock::now(); 
          }
          break;
        case StatusUpdate::WORKING:
          if ((*instance)->status != EnvStatus::CONNECTING && (*instance)->status != EnvStatus::WORKING) {
            std::cout << "An instance wanted to go to WORKING from illegal status " << (*instance)->status << std::endl;
          } else {
            (*instance)->status = EnvStatus::WORKING;
          }
          break;
        case StatusUpdate::SHUTTING_DOWN:
          (*instance)->status = EnvStatus::SHUTDOWN;
      }

      (*instance)->last_update = std::chrono::steady_clock::now();
      if (msg_parsed.load()) {
        (*instance)->load = msg_parsed.load();
      }
      if (msg_parsed.address().length()) {
        (*instance)->address = msg_parsed.address();
      }

      if (msg_parsed.steps_computed()) {
        steps_computed.fetch_add(msg_parsed.steps_computed());
      }

      // Send confirmation
      auto reply = StatusUpdateConfirmation();
      reply.set_id((*instance)->id);
      reply.set_reconnect(false);

      (*instance)->lock.unlock();
      inhibit_gc.unlock();
      
      sock.send(reply.SerializeAsString());
      continue;
    } else {
      // No ID was passed though env is not in init state anymore
      // Tell env to reconnect to get a new id
      std::cout << "Received non-init message without id" << std::endl;
      send_error(sock);
      continue;
    }
  }
  sock.close();
}

std::shared_ptr<EnvInstance> tryAllocateInstance(unsigned int group, std::string hostname) {
  // Find an IDLE instance
  std::shared_ptr<EnvInstance> instance;

  lock_registry.lock_shared();
  // Loop through all instances and find one which is IDLE and has the hostname in its address
  // This way, instances on the same host are handed out with preference
  if(hostname.size()) {
    for(auto i : registry) {
      if(i->lock.try_lock()) {
        if(i->status == EnvStatus::IDLE && i->group == group && i->address.find(hostname) != std::string::npos) {
          i->status = EnvStatus::CONNECTING;
          instance = i;
          break;
        } else {
          i->lock.unlock();
        }
      }
    }
  }

  // In case that didn't work, loop through all instances and find one which is IDLE anywhere
  // If there are several, take the one with the lowest load
  if(!instance) {
    double lowest_found_load = 99999999.9;
    for(auto i : registry) {
      if(i->lock.try_lock()) {
        if(i->status == EnvStatus::IDLE && i->group == group && i->load < lowest_found_load) {
          // If we already had an instance, send it back to idle
          if(instance) {
            instance->status = EnvStatus::IDLE;
            instance->lock.unlock();
          }

          i->status = EnvStatus::CONNECTING;
          instance = i;
          lowest_found_load = i->load;
        } else {
          i->lock.unlock();
        }
      }
    }
  }

  if(instance) {
    instance->lock.unlock();
  }

  lock_registry.unlock_shared();

  return instance;
}

void main_agent() {
  zmqpp::socket sock(ctx, zmqpp::socket_type::rep);
  std::string bind_address = "tcp://*:";
  if(std::getenv("BROKER_AGENT_PORT")) {
    bind_address.append(std::getenv("BROKER_AGENT_PORT"));
  } else {
    bind_address.append("4749");
  }
  sock.bind(bind_address);

  zmqpp::poller poller = zmqpp::poller();
  poller.add(sock);

  // Wait for the first environment to connect before parsing agent requests
  while(!first_env_connected && running) {
    std::this_thread::sleep_for (std::chrono::milliseconds(50));
  }

  if (running)
    std::cout << "Agent thread starting on " << bind_address << std::endl;

  unsigned int allocation_attempts = 0;

  while(running) {
    // Receive and parse message
    std::string msg;
    if(!poller.poll(1000))
      continue;
    sock.receive(msg);
    auto msg_parsed = RequestEnv();
    msg_parsed.ParseFromString(msg);

    // Send the instance to the client
    auto reply = AssignEnv();
    if (msg_parsed.send_info()) {
      reply.set_action_space(action_space);
      reply.set_observation_space(observation_space);
      reply.set_env_count(registry.size());
    }
    if (msg_parsed.allocate_env()) {
      std::shared_ptr<EnvInstance> instance;
      instance = tryAllocateInstance(msg_parsed.group(), msg_parsed.hostname());
      if (instance) {
        reply.set_address(instance->address);
        allocation_attempts = 0;
      } else {
        allocation_attempts++;
        if (allocation_attempts % 10000 == 0) {
          std::cout << "Allocation attempts: " << allocation_attempts << std::endl;
        }
      }
    }

    sock.send(reply.SerializeAsString());
  }

  sock.close();
}

// This thread has the task of printing out stats regularly
void main_stats() {
  std::list<double> load_history;
  int checks_without_work = 0;
  if(std::getenv("BROKER_EXIT_ON_NO_WORK")) {
    std::cout << "Will shutdown after long period of no work" << std::endl;
  }

  std::this_thread::sleep_for (std::chrono::seconds(10));
  while(running) {
    int initializing = 0;
    int resetting = 0;
    int idle = 0; 
    int connecting = 0;
    int working = 0;
    int shutdown = 0;
    double load = 0.0;
    int cores = 0;

    lock_registry.lock_shared();

    for (auto i : registry) {
      // Don't lock - we might not get up to date data but for stat's it doesn't matter
      int status = i->status;
      switch(status) {
        case EnvStatus::INITIALIZING: initializing++; break;
        case EnvStatus::CONNECTING: connecting++; break;
        case EnvStatus::IDLE: idle++; break;
        case EnvStatus::RESETTING: resetting++; break;
        case EnvStatus::WORKING: working++; break;
        case EnvStatus::SHUTDOWN: shutdown++; break;
      }
      load += i->load;
      cores += i->cores;
    }
    if (registry.size())
      load /= registry.size();

    lock_registry.unlock_shared();

    load_history.push_back(load);
    while (load_history.size() > HISTORY_SIZE) {
      load_history.pop_front();
    }

    int steps = steps_computed.exchange(0);
    steps_computed_past.push_back(steps);
    while (steps_computed_past.size() > HISTORY_SIZE) {
      steps_computed_past.pop_front();
    }

    if(steps == 0) {
      checks_without_work++;
      if(std::getenv("BROKER_EXIT_ON_NO_WORK") && checks_without_work >= 60) {
        std::cout << "No work for " << checks_without_work*10 << " seconds, exiting!" << std::endl;
        running = false;
      }
    } else {
      checks_without_work = 0;
    }

    double avg_steps = std::accumulate(steps_computed_past.begin(), steps_computed_past.end(), 0) / (double)steps_computed_past.size();
    double avg_load = std::accumulate(load_history.begin(), load_history.end(), 0.0) / (double)load_history.size();

    std::cout 
      // << "init: " << initializing
      << "con: " << connecting + initializing + shutdown
      << " idl: " << idle
      << " rst: " << resetting
      << " wrk: " << working
      //<< " shut: " << shutdown
      << " gc: " << environments_removed.exchange(0)
      << " n: " << cores
      << " load: " << round(load*1000.0)/1000.0
      << "(" << round(avg_load*1000.0)/1000.0 << ")"
      << " steps: " << steps
      << "(" << avg_steps << ")"
      << std::endl;
    std::this_thread::sleep_for (std::chrono::seconds(10));
  }
}

void main_garbage_collect() {
  int timeout = 300;
  if(std::getenv("BROKER_ENV_TIMEOUT")) {
    timeout = std::stoi(std::getenv("BROKER_ENV_TIMEOUT"));
  }

  std::cout << "Starting env garbage collection with timeout " << timeout << std::endl;

  while(running) {
    // check if we should still be running
    if(time_limit > 0 && std::chrono::steady_clock::now() - startup_time > std::chrono::seconds(time_limit)) {
      std::cout << "Ending script as timeout of " << time_limit << " seconds was exceeded" << std::endl;
      running = false;
      break;
    }

    // Acquire a write lock
    // This should lock out all other instances from the registry
    // There is still a race condition between the agent main and this one on status, last_update and load
    // however this doesn't matter as even slightly out of date values should not break our code
    lock_registry.lock();
    inhibit_gc.lock();
    // Remove all environments that are not talking to us for more than 2 minutes
    // Also remove all environments which are shut down
    int l_prev = registry.size();

    registry.erase(std::remove_if(registry.begin(), registry.end(), [&timeout](const auto &i) {
      return i->status == EnvStatus::SHUTDOWN || ((std::chrono::steady_clock::now() - i->last_update) > std::chrono::seconds(timeout));
    }), registry.end());

    environments_removed += (l_prev - registry.size());

    // Order the rest by load to do some load-balancing
    // Note that through the race condition on load, the order could be garbled
    // This is not too bad though as it's only a loadbalancing heuristic anyways
    // std::sort(registry.begin(), registry.end(), [](const auto& a, const auto& b) {
    //   return a->load < b->load;
    // });

    inhibit_gc.unlock();
    lock_registry.unlock();
    std::this_thread::sleep_for (std::chrono::seconds(15));
  }
}

void exit_on_sigint(int s) {
  std::cout << "Received interrupt " << s << ", waiting for workers to stop" << std::endl;
  if(!running) {
    ctx.terminate();
    exit(1);
  }
  running = false;
}

int main(int argc, char *argv[]) {
  startup_time = std::chrono::steady_clock::now();
  time_limit = 0;
  if(std::getenv("BROKER_TIME_LIMIT"))
    time_limit = std::stoi(std::getenv("BROKER_TIME_LIMIT"));

  if(time_limit > 0)
    std::cout << "Starting broker with time limit " << time_limit << " seconds" << std::endl;
  else
    std::cout << "Starting broker without time limit" << std::endl;


  // Catch sigints
  struct sigaction sigIntHandler;
  sigIntHandler.sa_handler = exit_on_sigint;
  sigemptyset(&sigIntHandler.sa_mask);
  sigIntHandler.sa_flags = 0;
  sigaction(SIGINT, &sigIntHandler, NULL);

  // Start threads
  running.store(true);
  next_id.store(1);
  steps_computed.store(0);
  first_env_connected.store(false);
  environments_removed.store(0);

  std::thread env(main_env);
  std::thread agent(main_agent);
  std::thread stats(main_stats);
  std::thread gc(main_garbage_collect);

  gc.join();
  env.join();
  agent.join();
  stats.join();

  std::cout << "Ending broker operation normally" << std::endl;
  return 0;
}
