from unittest import TestCase, skip

from typing import Optional

from h3 import h3

from hive.model.energy.charger import Charger
from hive.model.energy.energysource import EnergySource
from hive.model.energy.powertrain import Powertrain
from hive.model.energy.powercurve import Powercurve
from hive.model.request import Request
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.vehicle import Vehicle
from hive.model.vehiclestate import VehicleState
from hive.model.roadnetwork.routetraversal import Route
from hive.model.roadnetwork.link import Link
from hive.util.typealiases import *
from hive.model.energy.energytype import EnergyType


class TestVehicle(TestCase):
    def test_has_passengers(self):
        self.assertEqual(TestVehicle.mock_vehicle().has_passengers(), False, "should have no passengers")
        updated_vehicle = TestVehicle.mock_vehicle().add_passengers(TestVehicle.mock_request().passengers)
        self.assertEqual(updated_vehicle.has_passengers(), True, "should have passengers")

    def test_has_route(self):
        self.assertEqual(TestVehicle.mock_vehicle().has_route(), False, "should have no route")
        updated_vehicle = TestVehicle.mock_vehicle()._replace(route=TestVehicle.mock_route())
        self.assertEqual(updated_vehicle.has_route(), True, "should have a route")

    def test_add_passengers(self):
        no_pass_veh = TestVehicle.mock_vehicle()
        mock_request = TestVehicle.mock_request()

        self.assertEqual(no_pass_veh.has_passengers(), False)
        with_pass_veh = no_pass_veh.add_passengers(mock_request.passengers)
        self.assertEqual(len(with_pass_veh.passengers), len(mock_request.passengers))

    @skip("test not yet implemented")
    def test_battery_swap(self):
        self.fail()

    def test_transition_idle(self):
        non_idling_vehicle = TestVehicle.mock_vehicle()._replace(route=TestVehicle.mock_route(),
                                                                 vehicle_state=VehicleState.REPOSITIONING)
        transitioned = non_idling_vehicle.transition(VehicleState.IDLE)
        self.assertEqual(transitioned.vehicle_state, VehicleState.IDLE, "should have transitioned into an idle state")

    def test_transition_repositioning(self):
        idle_vehicle = TestVehicle.mock_vehicle()
        self.assertNotEqual(idle_vehicle.vehicle_state, VehicleState.REPOSITIONING,
                            "test vehicle should not begin in repositioning state")

        transitioned = idle_vehicle.transition(VehicleState.REPOSITIONING)
        self.assertEqual(transitioned.geoid, idle_vehicle.geoid,
                         "vehicle position should not be changed")

    def test_transition_dispatch_trip(self):
        """
        given a Vehicle in an IDLE state,
        - assign it to a DISPATCH_TRIP state via Vehicle.transition_dispatch_trip
          - confirm the vehicle state is correctly updated
        """
        idle_vehicle = TestVehicle.mock_vehicle()

        # check on transition function result
        transitioned = idle_vehicle.transition(VehicleState.DISPATCH_TRIP)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.geoid, idle_vehicle.geoid,
                         "vehicle position should not be changed")

    def test_transition_servicing_trip(self):
        idle_vehicle = TestVehicle.mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.SERVICING_TRIP)

        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.geoid, idle_vehicle.geoid,
                         "vehicle position should not be changed")

    def test_transition_dispatch_station(self):
        idle_vehicle = TestVehicle.mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.DISPATCH_TRIP)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.geoid, idle_vehicle.geoid,
                         "vehicle position should not be changed")

    def test_transition_charging_station(self):
        idle_vehicle = TestVehicle.mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.CHARGING_STATION)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.geoid, idle_vehicle.geoid,
                         "vehicle position should not be changed")

    def test_transition_dispatch_base(self):
        idle_vehicle = TestVehicle.mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.DISPATCH_BASE)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.geoid, idle_vehicle.geoid,
                         "vehicle position should not be changed")

    def test_transition_charging_base(self):
        idle_vehicle = TestVehicle.mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.CHARGING_BASE)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.geoid, idle_vehicle.geoid,
                         "vehicle position should not be changed")

    def test_transition_reserve_base(self):
        idle_vehicle = TestVehicle.mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.RESERVE_BASE)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.geoid, idle_vehicle.geoid,
                         "vehicle position should not be changed")

    def test_can_transition_good(self):
        mock_request = TestVehicle.mock_request()
        idle_veh = TestVehicle.mock_vehicle()
        veh_serving_trip = idle_veh.transition(VehicleState.SERVICING_TRIP)
        veh_w_pass = veh_serving_trip.add_passengers(mock_request.passengers)

        veh_can_trans = veh_w_pass.can_transition(VehicleState.SERVICING_TRIP)

        self.assertEqual(veh_can_trans, True)

    def test_can_transition_bad(self):
        mock_request = TestVehicle.mock_request()
        idle_veh = TestVehicle.mock_vehicle()
        veh_serving_trip = idle_veh.transition(VehicleState.SERVICING_TRIP)
        veh_w_pass = veh_serving_trip.add_passengers(mock_request.passengers)

        veh_can_trans = veh_w_pass.can_transition(VehicleState.IDLE)

        self.assertEqual(veh_can_trans, False)

    def test_move(self):
        vehicle = TestVehicle.mock_vehicle().transition(VehicleState.REPOSITIONING)
        power_train = TestVehicle.mock_powertrain()
        road_network = TestVehicle.mock_network()
        start_geoid = vehicle.geoid

        vehicle_w_route = vehicle.assign_route(TestVehicle.mock_route())

        moved_vehicle = vehicle_w_route.move(road_network=road_network, power_train=power_train, time_step=10)
        m2 = moved_vehicle.move(road_network=road_network, power_train=power_train, time_step=10)
        m3 = m2.move(road_network=road_network, power_train=power_train, time_step=10)

        self.assertLess(moved_vehicle.energy_source.soc, 1)
        self.assertNotEqual(start_geoid, moved_vehicle.geoid)
        self.assertNotEqual(start_geoid, moved_vehicle.property_link.link.start)

        self.assertNotEqual(moved_vehicle.geoid, m2.geoid)
        self.assertNotEqual(m2.property_link.link.start, m3.property_link.link.start)

    def test_charge(self):
        vehicle = TestVehicle.mock_vehicle().transition(VehicleState.CHARGING_STATION)
        power_curve = TestVehicle.mock_powercurve()
        time_step_size_secs = 1.0

        result = vehicle.charge(power_curve, Charger.DCFC, time_step_size_secs)
        self.assertEqual(result.energy_source.load, vehicle.energy_source.load + 1, "should have charged 1 unit")

    def test_charge_when_full(self):
        vehicle = TestVehicle.mock_vehicle().transition(VehicleState.CHARGING_STATION)
        vehicle_full = vehicle.battery_swap(TestVehicle.mock_energysource(cap=100, max_charge=100, soc=1.0))  # full
        power_curve = TestVehicle.mock_powercurve()
        time_step_size_secs = 1.0

        result = vehicle_full.charge(power_curve, Charger.DCFC, time_step_size_secs)
        self.assertEqual(result.energy_source.load, vehicle_full.energy_source.load, "should have not charged")
        self.assertEqual(result.vehicle_state, VehicleState.IDLE, "should have been moved to an idle state")

    def test_from_string_good_row(self):
        """
        should take a row of data, ignoring spaces, and return a vehicle
        """
        #      id     ,lat,lon,powertrain,energycurve,energy_capacity,initial_soc
        row = "test_id,37 ,122,leaf      ,leaf       ,150            ,0.5"
        vehicle = Vehicle.from_string(row, self.mock_network())
        self.assertIsInstance(vehicle, Vehicle, "result of parse should be a vehicle")
        self.assertEquals(vehicle.id, "test_id")
        self.assertEquals(vehicle.geoid, h3.geo_to_h3(37, 122, self.mock_network().sim_h3_resolution))
        self.assertEquals(vehicle.energy_source.soc(), 0.5)
        self.assertEquals(vehicle.energy_source.capacity, 150)
        self.assertEquals(vehicle.powertrain_id, "leaf")

    def test_from_string_bad_id(self):
        """
        vehicle ids must be alphanumeric + underscore only
        """
        #      id     ,lat,lon,powertrain,energycurve,energy_capacity,initial_soc
        row = "bad-id$,37 ,122,leaf      ,leaf       ,150            ,0.5"
        result = Vehicle.from_string(row, self.mock_network())
        self.assertIsInstance(result, IOError, "the id should cause failure")

    def test_from_string_bad_lat(self):
        #      id     ,lat,lon,powertrain,energycurve,energy_capacity,initial_soc
        row = "test_id,a1 ,122,leaf      ,leaf       ,150            ,0.5"
        result = Vehicle.from_string(row, self.mock_network())
        self.assertIsInstance(result, IOError, "the lat should cause failure")

    def test_from_string_bad_lon(self):
        #      id     ,lat,lon,powertrain,energycurve,energy_capacity,initial_soc
        row = "test_id,37 ,1B$,leaf      ,leaf       ,150            ,0.5"
        result = Vehicle.from_string(row, self.mock_network())
        self.assertIsInstance(result, IOError, "the lon should cause failure")

    def test_from_string_bad_powertrain(self):
        #      id     ,lat,lon,powertrain,energycurve,energy_capacity,initial_soc
        row = "test_id,37 ,122,no-good   ,leaf       ,150            ,0.5"
        result = Vehicle.from_string(row, self.mock_network())
        self.assertIsInstance(result, IOError, "the powertrain should cause failure")

    @skip("vehicles don't have energycurves yet")
    def test_from_string_bad_energycurve(self):
        #      id     ,lat,lon,powertrain,energycurve,energy_capacity,initial_soc
        row = "test_id,37 ,122,leaf      ,beef       ,150            ,0.5"
        result = Vehicle.from_string(row, self.mock_network())
        self.assertIsInstance(result, IOError, "the energycurve should cause failure")

    def test_from_string_bad_initial_soc(self):
        #      id     ,lat,lon,powertrain,energycurve,energy_capacity,initial_soc
        row = "test_id,37 ,122,leaf      ,leaf       ,150            ,1.5"
        result = Vehicle.from_string(row, self.mock_network())
        self.assertIsInstance(result, IOError, "the initial_soc should cause failure")


    @classmethod
    def mock_powertrain(cls) -> Powertrain:
        return VehicleTestAssests.MockPowertrain()

    @classmethod
    def mock_powercurve(cls) -> Powercurve:
        return VehicleTestAssests.MockPowercurve()

    @classmethod
    def mock_network(cls) -> RoadNetwork:
        return VehicleTestAssests.MockRoadNetwork(VehicleTestAssests.property_links)

    @classmethod
    def mock_energysource(cls, cap=100, soc=0.25, max_charge=50.0) -> EnergySource:
        """
        invariant: test_charge depends on having some amount of battery to fill
        """
        return EnergySource.build(
            powercurve_id=TestVehicle.mock_powercurve().get_id(),
            energy_type=EnergyType.ELECTRIC,
            capacity=cap,
            max_charge_acceptance=max_charge,
            soc=soc)

    @classmethod
    def mock_vehicle(cls) -> Vehicle:
        mock_powertrain = TestVehicle.mock_powertrain()
        mock_powercurve = TestVehicle.mock_powercurve()
        mock_energy_source = TestVehicle.mock_energysource()
        mock_network = TestVehicle.mock_network()
        geoid = h3.geo_to_h3(0, 0, 11)
        mock_property_link = mock_network.property_link_from_geoid(geoid)
        mock_veh = Vehicle(id="v1",
                           powertrain_id=mock_powertrain.get_id(),
                           powercurve_id=mock_powercurve.get_id(),
                           energy_source=mock_energy_source,
                           geoid=geoid,
                           property_link=mock_property_link
                           )
        return mock_veh

    @classmethod
    def mock_request(cls) -> Request:
        return Request.build("test_request",
                             origin=h3.geo_to_h3(0, 0, 11),
                             destination=h3.geo_to_h3(10, 10, 11),
                             departure_time=0,
                             cancel_time=10,
                             passengers=2)

    @classmethod
    def mock_route(cls) -> Route:
        property_links = VehicleTestAssests.property_links

        return property_links["1"], property_links["2"], property_links["3"], property_links["4"]


class VehicleTestAssests:
    class MockRoadNetwork(RoadNetwork):
        """
        a road network that only implements "get_link"
        """

        def __init__(self, property_links):
            self.sim_h3_resolution = 15

            self.property_links = property_links

        def route(self, origin: GeoId, destination: GeoId) -> Tuple[Link, ...]:
            pass

        def update(self, sim_time: int) -> RoadNetwork:
            pass

        def get_link(self, link_id: LinkId) -> Optional[PropertyLink]:
            if link_id in self.property_links:
                return self.property_links[link_id]
            else:
                return None

        def get_current_property_link(self, property_link: PropertyLink) -> Optional[PropertyLink]:
            link_id = property_link.link.link_id
            if link_id in self.property_links:
                current_property_link = self.property_links[link_id]
                updated_property_link = property_link.update_speed(current_property_link.speed)
                return updated_property_link
            else:
                return None

        def property_link_from_geoid(self, geoid: GeoId) -> Optional[PropertyLink]:
            return PropertyLink("mpl", Link("ml", geoid, geoid), 1, 1, 1)

        def geoid_within_geofence(self, geoid: GeoId) -> bool:
            pass

        def link_id_within_geofence(self, link_id: LinkId) -> bool:
            pass

        def geoid_within_simulation(self, geoid: GeoId) -> bool:
            pass

        def link_id_within_simulation(self, link_id: LinkId) -> bool:
            pass

    class MockPowertrain(Powertrain):
        def get_id(self) -> PowertrainId:
            return "mock_powertrain"

        def get_energy_type(self) -> EnergyType:
            return EnergyType.ELECTRIC

        def energy_cost(self, route: Route) -> Kw:
            return len(route)

    class MockPowercurve(Powercurve):
        """
        just adds 1 when charging
        """

        def get_id(self) -> PowercurveId:
            return "mock_powercurve"

        def get_energy_type(self) -> EnergyType:
            return EnergyType.ELECTRIC

        def refuel(self, energy_source: 'EnergySource', charger: 'Charger', duration_seconds: Time = 1,
                   step_size_seconds: Time = 1) -> 'EnergySource':
            return energy_source.load_energy(1.0)

    sim_h3_resolution = 15

    links = {
        "1": Link("1",
                  h3.geo_to_h3(0, 0, sim_h3_resolution),
                  h3.geo_to_h3(0, 5, sim_h3_resolution)),
        "2": Link("2",
                  h3.geo_to_h3(0, 5, sim_h3_resolution),
                  h3.geo_to_h3(5, 5, sim_h3_resolution)),
        "3": Link("3",
                  h3.geo_to_h3(5, 5, sim_h3_resolution),
                  h3.geo_to_h3(5, 10, sim_h3_resolution)),
        "4": Link("4",
                  h3.geo_to_h3(5, 10, sim_h3_resolution),
                  h3.geo_to_h3(10, 10, sim_h3_resolution)),
    }

    property_links = {
        "1": PropertyLink.build(links["1"], 10),
        "2": PropertyLink.build(links["2"], 10),
        "3": PropertyLink.build(links["3"], 10),
        "4": PropertyLink.build(links["4"], 10)
    }
