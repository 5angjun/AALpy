import time

from aalpy.automata import Sevpa, SevpaState
from aalpy.base import Oracle, SUL
from aalpy.utils.HelperFunctions import print_learning_info, visualize_classification_tree
from .VpdaClassificationTree import VpdaClassificationTree
from aalpy.learning_algs.vpda.VpdaCounterExampleProcessing import counterexample_successfully_processed
from ...base.SUL import CacheSUL

print_options = [0, 1, 2, 3]
counterexample_processing_strategy = [None, 'rs']


def run_KV_vpda(alphabet: list, sul: SUL, eq_oracle: Oracle, cex_processing='rs',
                max_learning_rounds=None, cache_and_non_det_check=True, return_data=False, print_level=2):
    """
    Executes the KV algorithm.

    Args:

        alphabet: input alphabet

        sul: system under learning

        eq_oracle: equivalence oracle

        cex_processing: None for no counterexample processing, or 'rs' for Rivest & Schapire counterexample processing

        max_learning_rounds: number of learning rounds after which learning will terminate (Default value = None)

        cache_and_non_det_check: Use caching and non-determinism checks (Default value = True)

        return_data: if True, a map containing all information(runtime/#queries/#steps) will be returned
            (Default value = False)

        print_level: 0 - None, 1 - just results, 2 - current round and hypothesis size, 3 - educational/debug
            (Default value = 2)


    Returns:

        automaton of type automaton_type (dict containing all information about learning if 'return_data' is True)

    """

    assert print_level in print_options
    assert cex_processing in counterexample_processing_strategy

    start_time = time.time()
    eq_query_time = 0
    learning_rounds = 0

    if cache_and_non_det_check:
        # Wrap the sul in the CacheSUL, so that all steps/queries are cached
        sul = CacheSUL(sul)
        eq_oracle.sul = sul

    empty_string_mq = sul.query(tuple())[-1]

    initial_state = SevpaState(state_id='s0', is_accepting=empty_string_mq)

    initial_state.prefix = tuple()

    # TODO Create 1-SEVPA class
    # When creating a hypothesis, infer call transition destinations based on (loc, call) pairs

    # TODO Create initial hypothesis
    # Maybe move initialization of classification tree here
    # Add a new method to it called generate_initial_hypothesis()
    # Either -> one state and then procedure is same like in default KV (add cex later)
    # Discover a new state

    hypothesis = Sevpa(initial_state=initial_state, states=[], input_alphabet=alphabet)
    # Perform an equivalence query on this automaton
    eq_query_start = time.time()
    cex = eq_oracle.find_cex(hypothesis)

    print(f'Counterexample: {cex}')

    eq_query_time += time.time() - eq_query_start
    if cex is not None:
        cex = tuple(cex)

        # initialise the classification tree to have a root
        # labeled with the empty word as the distinguishing string
        # and two leaves labeled with access strings cex and empty word
        classification_tree = VpdaClassificationTree(alphabet=alphabet, sul=sul, cex=cex)
        visualize_classification_tree(classification_tree.root)

        while True:
            learning_rounds += 1
            if max_learning_rounds and learning_rounds - 1 == max_learning_rounds:
                break

            hypothesis = classification_tree.gen_hypothesis()
            hypothesis.reset_to_initial()

            if print_level == 2:
                print(f'\rHypothesis {learning_rounds}: {hypothesis.size} states.', end="")

            if print_level == 3:
                # would be nice to have an option to print classification tree
                print(f'Hypothesis {learning_rounds}: {hypothesis.size} states.')

            if counterexample_successfully_processed(sul, cex, hypothesis):
                # Perform an equivalence query on this automaton
                eq_query_start = time.time()
                cex = eq_oracle.find_cex(hypothesis)
                eq_query_time += time.time() - eq_query_start

                if cex is None:
                    if print_level == 3:
                        visualize_classification_tree(classification_tree.root)
                    break
                else:
                    cex = tuple(cex)

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
        'automaton_size': hypothesis.size,
        'queries_learning': sul.num_queries,
        'steps_learning': sul.num_steps,
        'queries_eq_oracle': eq_oracle.num_queries,
        'steps_eq_oracle': eq_oracle.num_steps,
        'learning_time': learning_time,
        'eq_oracle_time': eq_query_time,
        'total_time': total_time,
        'cache_saved': sul.num_cached_queries,
    }

    if print_level > 0:
        if print_level == 2:
            print("")
        print_learning_info(info)

    if return_data:
        return hypothesis, info

    return hypothesis
