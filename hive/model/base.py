from __future__ import annotations

from typing import Optional, NamedTuple, Dict

from h3 import h3

from hive.util.exception import SimulationStateError
from hive.util.typealiases import *


class Base(NamedTuple):
    """
    Represents a base within the simulation.

    :param id: unique base id.
    :type id: str
    :param geoid: location of base.
    :type geoid: GeoId
    :param total_stalls: total number of parking stalls.
    :type total_stalls: int
    :param available_stalls: number of available parking stalls.
    :type available_stalls: int
    :param station_id: Optional station that is located at the base.
    :type station_id: Optional[StationId]
    """
    id: BaseId
    geoid: GeoId
    total_stalls: int
    available_stalls: int
    station_id: Optional[StationId]

    @classmethod
    def build(cls,
              id: BaseId,
              geoid: GeoId,
              station_id: Optional[StationId],
              stall_count: int
              ):
        return Base(id, geoid, stall_count, stall_count, station_id)

    @classmethod
    def from_row(cls, row: Dict[str, str],
                 sim_h3_resolution: int) -> Base:
        """
        takes a csv row and turns it into a Base

        :param row: a row as interpreted by csv.DictReader
        :param sim_h3_resolution: the h3 resolution that events are experienced at
        :return: a Base, or an error
        """
        if 'base_id' not in row:
            raise IOError("cannot load a base without a 'base_id'")
        elif 'lat' not in row:
            raise IOError("cannot load a base without an 'lat' value")
        elif 'lon' not in row:
            raise IOError("cannot load a base without an 'lon' value")
        elif 'stall_count' not in row:
            raise IOError("cannot load a base without a 'stall_count' value")
        base_id = row['base_id']
        try:
            lat, lon = float(row['lat']), float(row['lon'])
            geoid = h3.geo_to_h3(lat, lon, sim_h3_resolution)
            stall_count = int(row['stall_count'])

            # allow user to leave station_id blank or use the word "none" to signify no station at base
            station_id_name = row['station_id'] if len(row['station_id']) > 0 else "none"
            station_id = None if station_id_name.lower() == "none" else station_id_name

            return Base.build(
                id=base_id,
                geoid=geoid,
                station_id=station_id,
                stall_count=stall_count
            )

        except ValueError:
            raise IOError(f"unable to parse request {base_id} from row due to invalid value(s): {row}")

    def has_available_stall(self) -> bool:
        """
        Does base have a stall or not.

        :return: Boolean
        """
        return bool(self.available_stalls > 0)

    def checkout_stall(self) -> Optional[Base]:
        """
        Checks out a stall and returns the updated base if there are enough stalls.

        :return: Updated Base or None
        """
        stalls = self.available_stalls
        if stalls < 1:
            return None
        return self._replace(available_stalls=stalls - 1)

    def return_stall(self) -> Base:
        """
        Checks out a stall and returns the updated base.

        :return: Updated Base
        """
        stalls = self.available_stalls
        if (stalls + 1) > self.total_stalls:
            raise SimulationStateError('Base already has maximum sta')
        return self._replace(available_stalls=stalls + 1)
