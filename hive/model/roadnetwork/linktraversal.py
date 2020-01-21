from typing import Optional, Union, NamedTuple

from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.util.helpers import H3Ops
from hive.util.units import Seconds


class LinkTraversal(NamedTuple):
    """
    represents the traversal of a link.

    :param traversed: represents any part of the link that was traversed.
    :type traversed: :py:obj:`Optional[PropertyLink]`
    :param remaining: represents any part of the link that remains to be traversed
    :type remaining: :py:obj:`Optional[PropertyLink]`
    :param remaining_time: represents any time the agent has left to traverse additional links
    :type remaining_time_seconds: :py:obj:`hours`
    """
    traversed: Optional[PropertyLink]
    remaining: Optional[PropertyLink]
    remaining_time_seconds: Seconds


def traverse_up_to(road_network: RoadNetwork,
                   property_link: PropertyLink,
                   available_time_seconds: Seconds) -> Union[Exception, LinkTraversal]:
    """
    using the ground truth road network, and some agent Link traversal, attempt to traverse
    the link, based on travel time calculations from the Link's PropertyLink attributes.

    :param road_network: the road network
    :param property_link: the plan the agent has to traverse a subset of a road network link
    :param available_time_seconds: the remaining time the agent has in this time step
    :return: the updated traversal, or, an exception.
             on update, if there is any remaining traversal, return an updated Link.
             if no traversal remains, return None.
             regardless, return the agent's remaining time after traversing
             if there was any error, return the exception instead.
    """
    property_link = road_network.get_current_property_link(property_link)
    if property_link is None:
        return AttributeError(f"attempting to traverse link {property_link.link_id} which does not exist")
    elif property_link.start == property_link.end:
        # already done!
        return LinkTraversal(
            traversed=None,
            remaining=None,
            remaining_time_seconds=available_time_seconds
        )
    else:
        # traverse up to available_time_hours across this link
        if property_link.travel_time_seconds <= available_time_seconds:
            # we can complete this link, so we return (remaining) Link = None
            return LinkTraversal(
                traversed=property_link,
                remaining=None,
                remaining_time_seconds=(available_time_seconds - property_link.travel_time_seconds)
            )
        else:
            # we do not have enough time to finish traversing this link, so, just traverse part of it,
            # leaving no remaining time.

            # find the point in this link to split into two sub-links
            mid_geoid = H3Ops.point_along_link(property_link, available_time_seconds)

            # create two sub-links, one for the part that was traversed, and one for the remaining part
            traversed = property_link.update_link(Link(property_link.link_id, property_link.start, mid_geoid))
            remaining = property_link.update_link(Link(property_link.link_id, mid_geoid, property_link.end))

            return LinkTraversal(
                traversed=traversed,
                remaining=remaining,
                remaining_time_seconds=0,
            )

