import time

from aalpy.automata import Dfa, DfaState
from aalpy.base import Oracle, SUL
from aalpy.utils.HelperFunctions import print_learning_info
from .ClassificationTree import ClassificationTree
from .KV_helpers import prettify_hypothesis
from ...SULs import DfaSUL
from ...base.SUL import CacheSUL

counterexample_processing_strategy = [None, 'rs']
print_options = [0, 1, 2, 3]


def run_KV(alphabet: list, sul: SUL, eq_oracle: Oracle, automaton_type='dfa', cex_processing=None,
           max_learning_rounds=None, return_data=False, print_level=2, pretty_state_names=True, ):
    """
    Executes TTT algorithm.

    Args:

        alphabet: input alphabet

        sul: system under learning

        eq_oracle: equivalence oracle

        automaton_type: type of automaton to be learned. Currently only 'dfa' supported.

        cex_processing: None for no counterexample processing, or 'rs' for Rivest & Schapire counterexample processing

        max_learning_rounds: number of learning rounds after which learning will terminate (Default value = None)

        return_data: if True, a map containing all information(runtime/#queries/#steps) will be returned
            (Default value = False)

        print_level: 0 - None, 1 - just results, 2 - current round and hypothesis size, 3 - educational/debug
            (Default value = 2)

        pretty_state_names: if False, the resulting dfa's state names will be the ones generated during learning.
                            if True, generic 's0'-sX' state names will be used
            (Default value = True)

    Returns:

        automaton of type automaton_type (dict containing all information about learning if 'return_data' is True)

    """

    assert print_level in print_options
    assert cex_processing in counterexample_processing_strategy
    assert automaton_type == 'dfa'
    assert isinstance(sul, DfaSUL)

    start_time = time.time()
    eq_query_time = 0
    learning_rounds = 0

    sul = CacheSUL(sul)

    # Do a membership query on the empty string to determine whether
    # the start state of the SUL is accepting or rejecting
    empty_string_mq = sul.query(tuple())[-1]

    # Construct a hypothesis automaton that consists simply of this
    # single (accepting or rejecting) state with self-loops for
    # all transitions.
    initial_state = DfaState(state_id=(),
                             is_accepting=empty_string_mq)

    for a in alphabet:
        initial_state.transitions[a] = initial_state

    hypothesis = Dfa(initial_state=initial_state,
                     states=[initial_state])

    # Perform an equivalence query on this automaton
    eq_query_start = time.time()
    cex = eq_oracle.find_cex(hypothesis)
    eq_query_time += time.time() - eq_query_start
    if cex is None:
        return hypothesis

    # initialise the classification tree to have a root
    # labeled with the empty word as the distinguishing string
    # and two leaves labeled with access strings cex and empty word
    classification_tree = ClassificationTree(alphabet=alphabet,
                                             sul=sul,
                                             cex=cex,
                                             empty_is_true=empty_string_mq)

    while True:
        learning_rounds += 1
        if max_learning_rounds and learning_rounds - 1 == max_learning_rounds:
            break

        hypothesis = classification_tree.gen_hypothesis()

        if print_level > 1:
            print(f'Hypothesis {learning_rounds}: {len(hypothesis.states)} states.')

        if print_level == 3:
            # TODO: print classification tree
            pass

        if counterexample_successfully_processed(sul, cex, hypothesis):
            # Perform an equivalence query on this automaton
            eq_query_start = time.time()
            cex = eq_oracle.find_cex(hypothesis)
            eq_query_time += time.time() - eq_query_start

            if cex is None:
                break

            if print_level == 3:
                print('Counterexample', cex)

        if cex_processing == 'rs':
            classification_tree.update_rs(cex, hypothesis)
        else:
            classification_tree.update(cex, hypothesis)

    total_time = round(time.time() - start_time, 2)
    eq_query_time = round(eq_query_time, 2)
    learning_time = round(total_time - eq_query_time, 2)

    info = {
        'learning_rounds': learning_rounds,
        'automaton_size': len(hypothesis.states),
        'queries_learning': sul.num_queries,
        'steps_learning': sul.num_steps,
        'queries_eq_oracle': eq_oracle.num_queries,
        'steps_eq_oracle': eq_oracle.num_steps,
        'learning_time': learning_time,
        'eq_oracle_time': eq_query_time,
        'total_time': total_time,
        'classification_tree': classification_tree
    }

    prettify_hypothesis(hypothesis, alphabet, keep_access_strings=not pretty_state_names)

    if print_level > 0:
        print_learning_info(info)

    if return_data:
        return hypothesis, info

    return hypothesis


def counterexample_successfully_processed(sul, cex, hypothesis):
    cex_outputs = sul.query(cex)
    hyp_outputs = hypothesis.execute_sequence(hypothesis.initial_state, cex)
    return cex_outputs[-1] == hyp_outputs[-1]
