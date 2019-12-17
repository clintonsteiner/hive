from unittest import TestCase

from h3 import h3

from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.property_link import PropertyLink
from hive.util.helpers import H3Ops
from hive.util.units import unit


class TestH3Ops(TestCase):
    def test_point_along_link(self):
        # endpoints are about 1km apart
        start = h3.geo_to_h3(37, 122, 15)
        end = h3.geo_to_h3(37.008994, 122, 15)

        # create links with 1km speed
        kmph = (unit.kilometers/unit.hours)
        fwd_link = PropertyLink.build(Link("test", start, end), 1*kmph)
        bwd_link = PropertyLink.build(Link("test", end, start), 1*kmph)

        # test moving forward and backward, each by a half-unit of time
        fwd_result = H3Ops.point_along_link(fwd_link, 0.5*unit.hour)
        bwd_result = H3Ops.point_along_link(bwd_link, 0.5*unit.hour)

        # check that the point is half-way
        fwd_lat, fwd_lon = h3.h3_to_geo(fwd_result)
        self.assertAlmostEqual(fwd_lat, 37.004, places=2)
        self.assertAlmostEqual(fwd_lon, 122, places=2)

        bwd_lat, bwd_lon = h3.h3_to_geo(bwd_result)
        self.assertAlmostEqual(bwd_lat, 37.004, places=2)
        self.assertAlmostEqual(bwd_lon, 122, places=2)

    def test_nearest_entity_point_to_point(self):
        somewhere = h3.geo_to_h3(39.748971, -104.992323, 15)
        close_to_somewhere = h3.geo_to_h3(39.753600, -104.993369, 15)
        far_from_somewhere = h3.geo_to_h3(39.728882, -105.002792, 15)
        entities = {'1': 1, '2': 2, '3': 3, '4': 4}
        entity_locations = {close_to_somewhere: ('1', '2'), far_from_somewhere: ('3', '4')}

        nearest_entity = H3Ops.nearest_entity_point_to_point(somewhere, entities, entity_locations)

        self.assertEqual(nearest_entity, 1, "should have returned 1")