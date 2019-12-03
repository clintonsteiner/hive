from typing import Tuple, Optional
from unittest import TestCase

from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.routetraversal import traverse
from hive.model.roadnetwork.linktraversal import traverse_up_to
from hive.util.helpers import H3Ops
from hive.util.typealiases import LinkId, GeoId

from h3 import h3


class TestRouteTraversal(TestCase):
    def test_traverse_with_enough_time(self):
        """
        the mock problem is tuned to complete the route with a time step of just beyond 3 time units
        """
        network = TestRouteTraversalAssets.mock_network()
        links = TestRouteTraversalAssets.mock_links()
        result = traverse(
            route_estimate=links,
            road_network=network,
            time_step=4
        )
        self.assertGreater(result.remaining_time, 0, "should have more time left")
        self.assertEqual(len(result.remaining_route), 0, "should have no more route")
        self.assertEqual(len(result.experienced_route), 3, "should have hit all 3 links")

    def test_traverse_without_enough_time(self):
        """
        the mock problem needs more than 1.5 time to complete the route. should end
        up somewhere in the middle
        """
        network = TestRouteTraversalAssets.mock_network()
        links = TestRouteTraversalAssets.mock_links()
        result = traverse(
            route_estimate=links,
            road_network=network,
            time_step=1.5
        )
        self.assertEqual(result.remaining_time, 0, "should have no more time left")
        self.assertEqual(len(result.remaining_route), 2, "should have 2 links remaining")
        self.assertEqual(len(result.experienced_route), 2, "should have traversed 2 links")

    def test_traverse_up_to_split(self):
        network = TestRouteTraversalAssets.mock_network()
        links = TestRouteTraversalAssets.mock_links()
        test_link = links[0]

        result = traverse_up_to(
            road_network=network,
            property_link=test_link,
            available_time=0.5,
        )

        traversed = result.traversed
        remaining = result.remaining

        self.assertEqual(test_link.start, traversed.start, "Original link and traversed link should share start")
        self.assertEqual(test_link.end, remaining.end, "Original link and remaining link should share end")
        self.assertEqual(traversed.end, remaining.start, "Traversed end should match remaining start")

    def test_traverse_up_to_no_split(self):
        network = TestRouteTraversalAssets.mock_network()
        links = TestRouteTraversalAssets.mock_links()
        test_link = links[0]

        result = traverse_up_to(
            road_network=network,
            property_link=test_link,
            available_time=4,
        )

        traversed = result.traversed
        remaining = result.remaining

        self.assertEqual(test_link.start, traversed.start, "Original link and traversed link should share start")
        self.assertEqual(test_link.end, traversed.end, "Original link and traversed link should share end")
        self.assertIsNone(remaining, "There should be no remaining route")


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
        pass

    def geoid_within_geofence(self, geoid: GeoId) -> bool:
        pass

    def link_id_within_geofence(self, link_id: LinkId) -> bool:
        pass

    def geoid_within_simulation(self, geoid: GeoId) -> bool:
        pass

    def link_id_within_simulation(self, link_id: LinkId) -> bool:
        pass


class TestRouteTraversalAssets:
    """
    a mock scenario with 3 road network links. their travel time each is in
    generic units.
    """

    sim_h3_resolution = 15

    links = {
        "1": Link("1",
                  h3.geo_to_h3(37, 122, sim_h3_resolution),
                  h3.geo_to_h3(37.008994, 122, sim_h3_resolution)),
        "2": Link("2",
                  h3.geo_to_h3(37.008994, 122, sim_h3_resolution),
                  h3.geo_to_h3(37.017998, 122, sim_h3_resolution)),
        "3": Link("3",
                  h3.geo_to_h3(37.017998, 122, sim_h3_resolution),
                  h3.geo_to_h3(37.026992, 122, sim_h3_resolution)),
    }

    property_links = {
        # distance of 1.0 KM, speed of 1 KM/time unit
        "1": PropertyLink.build(links["1"], 1),
        "2": PropertyLink.build(links["2"], 1),
        "3": PropertyLink.build(links["3"], 1)
    }

    @classmethod
    def mock_network(cls) -> RoadNetwork:
        return MockRoadNetwork(cls.property_links)

    @classmethod
    def mock_links(cls) -> Tuple[PropertyLink, ...]:
        return cls.property_links["1"], cls.property_links["2"], cls.property_links["3"]
