from unittest import TestCase

from tests.mock_lobster import *


class TestDispatcher(TestCase):
    def test_match_vehicle(self):
        dispatcher = BasicDispatcher(managers=(GreedyMatcher(low_soc_threshold=0.2),))

        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        near_to_somewhere = h3.geo_to_h3(39.754, -104.975, 15)
        far_from_somewhere = h3.geo_to_h3(39.755, -104.976, 15)

        req = mock_request_from_geoids(origin=somewhere)
        close_veh = mock_vehicle_from_geoid(vehicle_id='close_veh', geoid=near_to_somewhere)
        far_veh = mock_vehicle_from_geoid(vehicle_id='far_veh', geoid=far_from_somewhere)
        sim = mock_sim(
            h3_location_res=9,
            h3_search_res=9,
            vehicles=(close_veh, far_veh),
        )
        _, sim = simulation_state_ops.add_request(sim, req)

        dispatcher, instructions_map, _ = dispatcher.generate_instructions(sim)

        self.assertGreaterEqual(len(instructions_map), 1, "Should have generated at least one instruction")
        self.assertIsInstance(instructions_map[close_veh.id],
                              DispatchTripInstruction,
                              "Should have instructed vehicle to dispatch")
        self.assertEqual(instructions_map[close_veh.id].vehicle_id,
                         close_veh.id,
                         "Should have picked closest vehicle")

    def test_no_vehicles(self):
        dispatcher = BasicDispatcher(managers=(GreedyMatcher(low_soc_threshold=0.2),))

        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)

        req = mock_request_from_geoids(origin=somewhere)
        sim = mock_sim(h3_location_res=9, h3_search_res=9)
        _, sim = simulation_state_ops.add_request(sim, req)

        dispatcher, instructions_map, _ = dispatcher.generate_instructions(sim)

        self.assertEqual(len(instructions_map), 0, "There are no vehicles to make assignments to.")

    def test_charge_vehicle(self):
        # dispatcher = mock_dispatcher_with_mock_forecast()
        dispatcher = BasicDispatcher(managers=(BasicCharging(low_soc_threshold=0.2),))

        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.75, -104.976, 15)

        veh = mock_vehicle_from_geoid(geoid=somewhere)
        low_battery = mock_energy_source(soc=0.1)

        veh_low_battery = veh.modify_energy_source(low_battery)
        station = mock_station_from_geoid(geoid=somewhere_else)
        sim = mock_sim(h3_location_res=9, h3_search_res=9, vehicles=(veh_low_battery,), stations=(station,))

        dispatcher, instructions_map, _ = dispatcher.generate_instructions(sim)

        self.assertGreaterEqual(len(instructions_map), 1, "Should have generated at least one instruction")
        self.assertIsInstance(instructions_map[veh.id],
                              DispatchStationInstruction,
                              "Should have instructed vehicle to dispatch to station")

    def test_activate_vehicles(self):
        dispatcher = mock_dispatcher_with_mock_forecast(forecast=1)

        # manger will always predict we need 1 activate vehicle. So, we start with one inactive vehicle and see
        # if it is moved to active.

        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)

        veh = mock_vehicle_from_geoid(
            geoid=somewhere,
            vehicle_state=ReserveBase(
                DefaultIds.mock_vehicle_id(),
                DefaultIds.mock_base_id()
            )
        )
        base = mock_base_from_geoid(geoid=somewhere, stall_count=2)

        sim = mock_sim(vehicles=(veh,), bases=(base,))

        dispatcher, instructions_map, _ = dispatcher.generate_instructions(sim)

        self.assertGreaterEqual(len(instructions_map), 1, "Should have generated at least one instruction")
        self.assertIsInstance(instructions_map[veh.id],
                              RepositionInstruction,
                              "Should have instructed vehicle to reposition")

    def test_deactivate_vehicles(self):
        dispatcher = mock_dispatcher_with_mock_forecast(forecast=1)

        # manger will always predict we need 1 activate vehicle. So, we start with two active vehicle and see
        # if it is moved to base.

        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.75, -104.976, 15)

        veh1 = mock_vehicle_from_geoid(vehicle_id='v1', geoid=somewhere)
        veh2 = mock_vehicle_from_geoid(vehicle_id='v2', geoid=somewhere)
        base = mock_base_from_geoid(geoid=somewhere_else, stall_count=2)

        sim = mock_sim(
            h3_location_res=9,
            h3_search_res=9,
            vehicles=(veh1, veh2),
            bases=(base,)
        )

        dispatcher, instructions_map, _ = dispatcher.generate_instructions(sim)

        self.assertEqual(len(instructions_map), 1, "Should have generated only one instruction")
        self.assertIsInstance(list(instructions_map.values())[0],
                              DispatchBaseInstruction,
                              "Should have instructed vehicle to dispatch to base")

    def test_valuable_requests(self):
        dispatcher = BasicDispatcher(managers=(GreedyMatcher(low_soc_threshold=0.2),))

        # manger will always predict we need 1 activate vehicle. So, we start with two active vehicle and see
        # if it is moved to base.

        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.75, -104.976, 15)

        veh1 = mock_vehicle_from_geoid(vehicle_id='v1', geoid=somewhere)
        expensive_req = mock_request_from_geoids(request_id='expensive', origin=somewhere_else, value=100)
        cheap_req = mock_request_from_geoids(request_id='cheap', origin=somewhere_else, value=10)

        sim = mock_sim(
            h3_location_res=9,
            h3_search_res=9,
            vehicles=(veh1,)
        )
        _, sim = simulation_state_ops.add_request(sim, expensive_req)
        _, sim = simulation_state_ops.add_request(sim, cheap_req)

        dispatcher, instructions_map, _ = dispatcher.generate_instructions(sim)

        self.assertGreaterEqual(len(instructions_map), 1, "Should have generated at least one instruction")
        self.assertIsInstance(instructions_map[veh1.id],
                              DispatchTripInstruction,
                              "Should have instructed vehicle to dispatch")
        self.assertEqual(instructions_map[veh1.id].request_id, 'expensive', 'Should have picked expensive request')

    def test_limited_base_charging(self):
        """
        tests BaseManagement dispatch Manager can limit actively charging vehicles when saturated
        and that the lower soc vehicles are prioritized
        """
        dispatcher = BasicDispatcher(managers=(BaseManagement(base_vehicles_charging_limit=1),))

        station = mock_station_from_geoid(chargers=immutables.Map({Charger.LEVEL_2: 2}))
        base = mock_base_from_geoid(stall_count=2, station_id=station.id)

        vid_1 = 'lower_soc_vehicle'
        vid_2 = 'higher_soc_vehicle'

        # both vehicles eligible to charge at base
        close_veh = mock_vehicle_from_geoid(
            vehicle_id=vid_1,
            geoid=station.geoid,
            vehicle_state=ReserveBase(
                vehicle_id=vid_1,
                base_id=base.id
            ),
            soc=0.1
        )
        far_veh = mock_vehicle_from_geoid(
            vehicle_id=vid_2,
            geoid=station.geoid,
            vehicle_state=ReserveBase(
                vehicle_id=vid_2,
                base_id=base.id
            ),
            soc=0.2
        )
        sim = mock_sim(
            h3_location_res=9,
            h3_search_res=9,
            vehicles=(close_veh, far_veh),
            stations=(station,),
            bases=(base,)
        )

        dispatcher, instructions_map, _ = dispatcher.generate_instructions(sim)

        instruction = list(instructions_map.values())[0]

        self.assertGreaterEqual(len(instructions_map), 1, "Should have generated only one instruction")
        self.assertIsInstance(instruction, ChargeBaseInstruction, "Should have been instructed to charge at base")
        self.assertEquals(instruction.vehicle_id, vid_1, "should be charging the lower soc vehicle")
