import unittest

from nrel.hive.config.network import Network
from nrel.hive.initialization.load import load_simulation
from nrel.hive.initialization.initialize_simulation import (
    initialize,
    default_init_functions,
    osm_init_function,
)
from nrel.hive.initialization.initialize_simulation_with_sampling import (
    initialize_simulation_with_sampling,
)
from nrel.hive.resources.mock_lobster import *

import nrel.hive.state.simulation_state.simulation_state_ops as sso


class TestInitializeSimulation(unittest.TestCase):
    def test_initialize_simulation(self):
        conf = mock_config().suppress_logging()

        sim, env = initialize(conf)
        self.assertEqual(len(sim.vehicles), 20, "should have loaded 20 vehicles")
        self.assertEqual(len(sim.stations), 4, "should have loaded 4 stations")
        self.assertEqual(len(sim.bases), 2, "should have loaded 1 base")

    def test_initialize_simulation_with_filtering(self):
        conf = mock_config().suppress_logging()

        def filter_veh(
            conf: HiveConfig, sim: SimulationState, env: Environment
        ) -> Tuple[SimulationState, Environment]:
            sim_or_error = sso.remove_vehicle_safe(sim, "v1")
            return sim_or_error.unwrap(), env

        def filter_base(
            conf: HiveConfig, sim: SimulationState, env: Environment
        ) -> Tuple[SimulationState, Environment]:
            sim_or_error = sso.remove_base_safe(sim, "b1")
            return sim_or_error.unwrap(), env

        def filter_station(
            conf: HiveConfig, sim: SimulationState, env: Environment
        ) -> Tuple[SimulationState, Environment]:
            sim_or_error = sso.remove_station_safe(sim, "s1")
            return sim_or_error.unwrap(), env

        init_funtions = default_init_functions()
        init_funtions.extend([filter_veh, filter_base, filter_station])

        sim, env = initialize(conf, init_functions=init_funtions)

        self.assertIsNone(sim.vehicles.get("v1"), "should not have loaded vehicle v1")
        self.assertIsNone(sim.bases.get("b1"), "should not have loaded base b1")
        self.assertIsNone(sim.stations.get("s1"), "should not have loaded station s1")

    def test_initialize_simulation_with_sampling(self):
        conf = (
            mock_config()
            ._replace(
                network=Network(
                    network_type="osm_network",
                    default_speed_kmph=40,
                )
            )
            .suppress_logging()
        )

        new_input = conf.input_config._replace(
            road_network_file=Path(
                resource_filename(
                    "nrel.hive.resources.scenarios.denver_downtown.road_network",
                    "downtown_denver_network.json",
                )
            )
        )

        conf = conf._replace(input_config=new_input)

        sim, env = initialize_simulation_with_sampling(
            config=conf,
            vehicle_count=20,
        )
        self.assertEqual(len(sim.vehicles), 20, "should have loaded 20 vehicles")
        self.assertEqual(len(sim.stations), 4, "should have loaded 4 stations")
        self.assertEqual(len(sim.bases), 2, "should have loaded 2 bases")

    @unittest.skip("makes API call to OpenStreetMaps via osmnx")
    def test_initialize_simulation_load_from_geofence_file(self):
        """Move this to long running if it gets to be out of hand"""
        conf = (
            mock_config()
            ._replace(
                network=Network(
                    network_type="osm_network",
                    default_speed_kmph=40,
                )
            )
            .suppress_logging()
        )

        new_input = conf.input_config._replace(
            geofence_file=Path(
                resource_filename(
                    "nrel.hive.resources.scenarios.denver_downtown.geofence",
                    "downtown_denver.geojson",
                )
            ),
            road_network_file=None,
        )

        conf = conf._replace(input_config=new_input)

        runnerPayload = load_simulation(
            config=conf,
        )
        self.assertIsNotNone(runnerPayload.s.road_network)
