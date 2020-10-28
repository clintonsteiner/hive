from __future__ import annotations

import functools as ft
import logging
import immutables
from typing import Tuple, Optional, TYPE_CHECKING, Callable, NamedTuple

from hive.dispatcher.instruction.instruction import Instruction
from hive.dispatcher.instruction.instruction_result import InstructionResult
from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.model.vehicle.vehicle import Vehicle, VehicleId
from hive.state.entity_state import entity_state_ops
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.vehicle_state.charge_queueing import ChargeQueueing
from hive.util import TupleOps
from hive.reporting.reporter import Report
from hive.reporting.report_type import ReportType

if TYPE_CHECKING:
    from hive.runner.environment import Environment
    from hive.util.typealiases import SimTime

log = logging.getLogger(__name__)


def _instruction_to_report(i: Instruction, sim_time: SimTime) -> Report:
    i_dict = i._asdict()
    i_dict['sim_time'] = sim_time
    i_dict['instruction_type'] = i.__class__.__name__

    return Report(ReportType.INSTRUCTION, i_dict)


def log_instructions(instructions: Tuple[Instruction], env: Environment, sim_time: SimTime):
    for i in instructions:
        env.reporter.file_report(_instruction_to_report(i, sim_time))


def perform_driver_state_updates(simulation_state: SimulationState, env: Environment) -> SimulationState:
    """
    helper function for StepSimulation which runs the update function for all driver states

    :param simulation_state: the simulation state to update
    :param env: the simulation environment
    :return: the sim after all vehicle update functions have been called
    """

    def _step_drivers(s: SimulationState, vehicle: Vehicle) -> SimulationState:
        driver_state = vehicle.driver_state
        error, updated_sim = driver_state.update(s, env)
        if error:
            log.error(error)
            return simulation_state
        elif not updated_sim:
            return simulation_state
        else:
            return updated_sim

    next_state = ft.reduce(_step_drivers, simulation_state.get_vehicles(), simulation_state)
    return next_state


def perform_vehicle_state_updates(simulation_state: SimulationState, env: Environment) -> SimulationState:
    """
    helper function for StepSimulation which applies a vehicle state update to each vehicle

    :param simulation_state: the simulation state to update
    :param env: the simulation environment
    :return: the sim after all vehicle update functions have been called
    """

    def _step_vehicle(s: SimulationState, vehicle: Vehicle) -> SimulationState:
        error, updated_sim = vehicle.vehicle_state.update(s, env)
        if error:
            log.error(error)
            return simulation_state
        elif not updated_sim:
            return simulation_state
        else:
            return updated_sim

    def _sort_by_vehicle_state(vs: Tuple[Vehicle, ...]) -> Tuple[Vehicle, ...]:
        """
        a one-pass partitioning to place ChargeQueueing agents after their non-ChargeQueueing friends
        and to sort the charge queueing agents by their enqueue_time

        if we need additional sort criteria for future VehicleStates we may need to
        instead call sim.get_vehicles with a sort_key function in place of this shortcut


        :param vs: the vehicles
        :return: the vehicles with all ChargeQueueing vehicles at the tail
        """
        charge_queueing_vehicles, other_vehicles = TupleOps.partition(
            lambda v: isinstance(v.vehicle_state, ChargeQueueing),
            vs
        )

        sorted_charge_queueing_vehicles = tuple(sorted(charge_queueing_vehicles, key=lambda v: v.vehicle_state.enqueue_time))

        return other_vehicles + sorted_charge_queueing_vehicles

    # why sort here? see _sort_by_vehicle_state for an explanation
    vehicles = _sort_by_vehicle_state(simulation_state.get_vehicles())
    next_state = ft.reduce(_step_vehicle, vehicles, simulation_state)

    return next_state


def apply_instructions(sim: SimulationState,
                       env: Environment,
                       instructions: Tuple[Instruction]) -> SimulationState:
    """
    this helper function takes a map with one instruction per agent at most, and attempts to apply each
    instruction to the simulation, managing the instruction's externalities, and managing failure.

    :param sim: the current simulation state
    :param env: the sim environment
    :param instructions: all instructions to add at this time step
    :return: the simulation state modified by all successful Instructions
    """
    # construct the vehicle state transitions
    run_in_parallel = False  # env.config.system.local_parallelism > 1

    if run_in_parallel:
        # run in parallel
        # todo: inject some means for parallel execution of the apply instruction operation
        #   requires shared memory access to SimulationState and Environment,
        #   and a serialization codec to ship Instructions and Instruction.apply_instruction remotely
        result = ((NotImplementedError, None),)
    else:
        # run in a synchronous loop
        result = ft.reduce(lambda acc, i: acc + (i.apply_instruction(sim, env),), instructions, ())

    has_errors, no_errors = TupleOps.partition(lambda t: t[0] is not None, result)
    valid_instruction_results = map(lambda t: t[1], no_errors)
    # report any errors from applying instructions
    if len(has_errors) > 0:
        # at least one failed
        for err, _ in has_errors:
            log.error(err)

    # update the simulation with each vehicle state transition in sequence
    def _add_instruction(
            s: SimulationState,
            i: InstructionResult,
    ) -> SimulationState:
        update_error, updated_sim = entity_state_ops.transition_previous_to_next(s, env, i.prev_state, i.next_state)
        if update_error:
            log.error(update_error)
            return s
        elif updated_sim is None:
            return s
        else:
            return updated_sim

    return ft.reduce(
        _add_instruction,
        valid_instruction_results,
        sim
    )


class UserProvidedUpdateAccumulator(NamedTuple):
    updated_fns: Tuple[InstructionGenerator, ...] = ()

    def apply_updated_instruction_generator(self, i: InstructionGenerator):
        return self._replace(updated_fns=self.updated_fns + (i,))


def instruction_generator_update_fn(
        fn: Callable[[InstructionGenerator, SimulationState], Optional[InstructionGenerator]],
        sim: SimulationState
) -> Callable[[UserProvidedUpdateAccumulator, InstructionGenerator], UserProvidedUpdateAccumulator]:
    """
    applies a user-provided function designed to inject an external update to InstructionGenerators

    :param fn: the function which applies an update or returns None for no update
    :param sim: the simulation state, which will not be modified but available to the update function
    :return: the updated list of InstructionGenerators
    """

    def _inner(acc: UserProvidedUpdateAccumulator,
               i: InstructionGenerator
               ) -> UserProvidedUpdateAccumulator:
        try:
            result = fn(i, sim)
            if not result:
                return acc.apply_updated_instruction_generator(i)
            else:
                return acc.apply_updated_instruction_generator(result)
        except Exception as e:
            raise e

    return _inner
