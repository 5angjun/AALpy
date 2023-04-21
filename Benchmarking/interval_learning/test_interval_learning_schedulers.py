import random
import sys

sys.path.append('../..')

from random import randint, choice

from Benchmarking.interval_learning.PrismInterface import PrismInterface
from aalpy.SULs import MdpSUL
from aalpy.automata import interval_smm_from_learning_data, interval_mdp_from_learning_data, IntervalSmm
from aalpy.learning_algs import run_stochastic_Lstar, run_Alergia
from aalpy.oracles import RandomWordEqOracle
from aalpy.utils import get_faulty_coffee_machine_MDP, get_small_gridworld, load_automaton_from_file, get_small_pomdp
from aalpy.utils import mdp_2_prism_format

import aalpy.paths

aalpy.paths.path_to_prism = '/mnt/c/Users/muskardine/Desktop/interval_prism/prism-imc2/prism/bin/prism'


# aalpy.paths.path_to_prism = "C:/Program Files/prism-4.7/bin/prism.bat"

def step_in_model(model, action, friendliness=0):
    assert friendliness in {-1, 0, 1}
    if action is None:
        return model.current_state.output

    probability_distributions = [i[1] for i in model.current_state.transitions[action]]
    states = [i[0] for i in model.current_state.transitions[action]]

    new_state = random.choices(states, probability_distributions, k=1)[0]

    if friendliness == 1 and random.random() > 0.5:
        new_state = states[probability_distributions.index(max(probability_distributions))]
    elif friendliness == -1 and random.random() > 0.5:
        new_state = states[probability_distributions.index(min(probability_distributions))]

    model.current_state = new_state
    return model.current_state.output


def evaluate_scheduler(scheduler, model, goal, num_steps, num_tests=26492, ):
    num_reached = 0
    for _ in range(num_tests):
        model.reset_to_initial()
        scheduler.reset()
        for _ in range(num_steps):
            action = scheduler.get_input()
            # print(action)
            if action is None:
                break
            output = step_in_model(model, action, friendliness=-1)
            # output = model.step(action)
            # print(output)
            reached_state = scheduler.step_to(action, output)
            if goal in output:
                num_reached += 1
                break
            if reached_state is None:  # in case of non-complete hypothesis
                break

    return round(num_reached / num_tests, 4)


experiment = 'first_grid'
confidence = 0.95

goal_states = {'first_grid': 'goal', 'second_grid': 'goal', 'tcp': 'crash', 'slot_machine': 'Pr2',
               'shared_coin': 'finished'}

steps_dict = {'first_grid': [8, 9, 10, 11, 12, 13],
              'second_grid': [11, 12, 13, 15, 17],
              'tcp': [5, 11, 17],
              'slot_machine': [4, 5, ],
              'shared_coin': [30, 40, 45]}

model_under_learning = load_automaton_from_file(f'../../DotModels/MDPs/{experiment}.dot', 'mdp')

# model_under_learning = get_faulty_coffee_machine_MDP()
# model_under_learning = get_small_pomdp()

sul = MdpSUL(model_under_learning)
alphabet = model_under_learning.get_input_alphabet()
eq_oracle = RandomWordEqOracle(alphabet, sul, num_walks=100)

learning_type = 'smm'
learned_model, data = run_stochastic_Lstar(alphabet, sul, eq_oracle, automaton_type=learning_type,
                                           target_unambiguity=0.8,
                                           min_rounds=5,
                                           max_rounds=100,
                                           return_data=True)

# learned_model = model_under_learning
# learned_interval_mdp = model_under_learning.to_interval_mdp_2()

if learning_type == 'mdp':
    learned_interval_mdp = learned_model.to_interval_mdp(data['observation_table'], confidence=confidence)
else:
    learned_interval_mdp = learned_model.to_interval_smm(data['observation_table'],
                                                         confidence=confidence).to_interval_mdp()
    learned_model = learned_model.to_mdp()

for step_nums in steps_dict[experiment]:
    #######################################

    goal_state = goal_states[experiment]
    num_steps = step_nums

    correct_property_val = PrismInterface(goal_state, model_under_learning, num_steps=num_steps, operation='Pmax',
                                          add_step_counter=True, stepping_bound=20).property_val

    prism_interface_mdp = PrismInterface(goal_state, learned_model, num_steps=num_steps, operation='Pmax',
                                         add_step_counter=True, stepping_bound=20)
    normal_scheduler = prism_interface_mdp.scheduler

    print('--------------------------------')
    print(f'Max step number to reach {goal_states[experiment]}: {step_nums}')
    print('Testing schedulers on 25000 episodes:')
    normal_scheduler_res = evaluate_scheduler(normal_scheduler, model_under_learning, goal_state, num_steps=num_steps)
    # print('Normal scheduler (Pmax) property        :', prism_interface_mdp.property_val)
    print('Ground truth (Pmax) property value      :', correct_property_val)
    print('Normal scheduler (Pmax) evaluation      :', normal_scheduler_res)

    #######################################

    prism_interface_mdp = PrismInterface(goal_state, learned_interval_mdp, num_steps=num_steps, operation='Pmaxmin',
                                         add_step_counter=True, stepping_bound=20)
    interval_scheduler = prism_interface_mdp.scheduler

    interval_scheduler_res = evaluate_scheduler(interval_scheduler, model_under_learning, goal_state,
                                                num_steps=num_steps)
    # print('Interval scheduler (Pmaxmin) property   :', prism_interface_mdp.property_val)
    print('Interval scheduler (Pmaxmin) evaluation :', interval_scheduler_res)

    #######################################

    prism_interface_mdp = PrismInterface(goal_state, learned_interval_mdp, num_steps=num_steps, operation='Pmaxmax',
                                         add_step_counter=True, stepping_bound=20)
    interval_scheduler = prism_interface_mdp.scheduler

    interval_scheduler_res = evaluate_scheduler(interval_scheduler, model_under_learning, goal_state,
                                                num_steps=num_steps)
    # print('Interval scheduler (Pmaxmax) property   :', prism_interface_mdp.property_val)
    print('Interval scheduler (Pmaxmax) evaluation :', interval_scheduler_res)
