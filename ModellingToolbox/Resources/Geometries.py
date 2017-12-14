# -*- coding: UTF-8 -*-
"""
This module provides basic geometries (points and lines) for storing geological data in database.
"""

import sqlalchemy as sq
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import Session
from typing import List

from Resources.DBHandler import Base, AbstractDBObject
from Resources.GeoObject import AbstractGeoObject
from Resources.PropertyLogs import Property
from Resources.Stratigraphy import StratigraphicObject
from Resources.constants import float_precision


class GeoPoint(Base, AbstractGeoObject):
    """
    Class GeoPoint

    Represents a geological point feature, e.g. for storing line nodes or geological outcrops in a database.
    """
    # define db table name and columns
    __tablename__ = 'geopoints'

    id = sq.Column(sq.INTEGER, sq.Sequence('geopoints_id_seq'), primary_key=True)
    has_z = sq.Column(sq.BOOLEAN, default=False)
    horizon_id = sq.Column(sq.INTEGER, sq.ForeignKey('stratigraphy.id'), default=-1)

    # define relationship to stratigraphic table
    hor = relationship("StratigraphicObject")

    line_id = sq.Column(sq.INTEGER, sq.ForeignKey('lines.id'), default=-1)
    line_pos = sq.Column(sq.INTEGER, default=-1)

    # make the points unique -> coordinates + horizon + belongs to one line?
    sq.UniqueConstraint(AbstractGeoObject.east, AbstractGeoObject.north, AbstractGeoObject.alt, horizon_id, line_id,
                        line_pos, name='u_point_constraint')
    sq.Index('geopoint_coordinate_index', AbstractGeoObject.east, AbstractGeoObject.north)

    # add Property relation
    # order by property name
    properties = relationship("Property", order_by=Property.prop_name, backref="point",
                              primaryjoin='GeoPoint.id==Property.point_id', cascade="all, delete, delete-orphan")

    def __init__(self, horizon, has_z, *args, **kwargs):
        # type: (StratigraphicObject, bool, *object, **object) -> None
        """
        Creates a new GeoPoint

        :param horizon: stratigraphy of the point
        :type horizon: StratigraphicObject
        :param has_z: Is altitude stored as z value?
        :type has_z: bool
        :param args: parameters for AbstractGeoObject initialisation
        :type args: List()
        :param kwargs: parameters for AbstractGeoObject initialisation
        :type kwargs: Dict()
        :return: Nothing
        :raises ValueError: if has_z is not compatible to type bool
        """

        self.has_z = bool(has_z)
        self.horizon = horizon

        # call base class constructor
        AbstractGeoObject.__init__(self, *args, **kwargs)

    def __repr__(self):
        # type: () -> str
        """
        Returns a text-representation of the point

        :return: Returns a text-representation of the point
        :rtype: str
        """
        text = "<GeoPoint(id='{}', horizon='{}', line={}, line-position={})>\n".\
            format(self.id, str(self.horizon), self.line_id, self.line_pos)
        text += AbstractGeoObject.__repr__(self)
        return text

    def __str__(self):
        # type: () -> str
        """
        Returns a text-representation of the point

        :return: Returns a text-representation of the point
        :rtype: str
        """
        text = "[{}] {} - {} - {}\n".format(self.id, str(self.horizon), self.line_id, self.line_pos)
        text += AbstractGeoObject.__str__(self)
        return text

    @property
    def horizon(self):
        # type: () -> StratigraphicObject
        """
        The stratigraphy of the point object

        :type: StratigraphicObject or None
        :raises TypeError: if value is not of type Stratigraphy
        """
        return self.hor

    @horizon.setter
    def horizon(self, value):
        # type: (StratigraphicObject) -> None
        """
        see getter
        """
        if (value is not None) and (type(value) is not StratigraphicObject):
            raise TypeError('type of commited value ({}) is not StratigraphicObject!'.format(type(value)))

        if value is None:
            self.hor = None
            self.horizon_id = -1
        else:
            self.hor = value

    # delete z-dimension and information from point
    def del_z(self):
        # type: () -> None
        """
        removes the z-value from the point

        :return: Nothing
        """
        self.alt = 0
        self.has_z = False

    def use_z(self):
        # type: () -> None
        """
        uses the altitude value as z coordinate

        :return: Nothing
        """
        self.has_z = True

    # add and remove property information form point
    def add_property(self, prop):
        # type: (Property) -> None
        """
        Adds a new property to the point

        :param prop: new point property
        :type prop: Property
        :return: Nothing
        :raises TypeError: if log is not of type Property
        """
        if type(prop) is not Property:
            raise TypeError('property {} is not of type Property!'.format(str(prop)))

        self.properties.append(prop)

    def delete_property(self, prop):
        # type: (Property) -> None
        """
        Deletes a property from the point

        :param prop: property to delete
        :type prop: Property

        :return: Nothing
        :raises TypeError: if log is not of type Property
        :raises ValueError: if log is not part of self.properties
        """
        if type(prop) is not Property:
            raise TypeError('property {} is not of type Property!'.format(str(prop)))

        try:
            self.properties.remove(prop)
        except ValueError as e:
            raise ValueError(str(e) + '\nProperty with ID ' + str(prop.id) + ' not found in list!')

    # overwrite loading method
    @classmethod
    def load_all_without_lines_from_db(cls, session):
        # type: (Session) -> List[Line]
        """
        Returns all points in the database connected to the SQLAlchemy Session session, which are not part of a line.
        This function is similar the AbstractGeoObject.load_all_from_db(...) function.

        :param session: represents the database connection as SQLAlchemy Session
        :type session: Session
        :return: a list of points representing the result of the database query
        :rtype: List[GeoPoint]
        :raises TypeError: if session is not of type SQLAlchemy Session
        """
        if not isinstance(session, Session):
            raise TypeError("'session' is not of type SQLAlchemy Session!")

        result = session.query(GeoPoint). \
            filter(GeoPoint.line_id == -1). \
            order_by(cls.id).all()
        for point in result:
            point.session = session
        return result

    @classmethod
    def load_by_name_without_lines_from_db(cls, name, session):
        # type: (str, Session) -> List[GeoPoint]
        """
        Returns all GeoPoints with the given name in the database connected to the SQLAlchemy Session session, which
        don't belong to a line

        :param name: Only GeoPoints with this name will be returned
        :type name: str
        :param session: represents the database connection as SQLAlchemy Session
        :type session: Session
        :return: a list of GeoPoints representing the result of the database query
        :rtype: List[GeoPoints]
        :raises TypeError: if session is not of type SQLAlchemy Session
        """
        if not isinstance(session, Session):
            raise TypeError("'session' is not of type SQLAlchemy Session!")

        result = session.query(cls).filter(cls.line_id == -1).filter(cls.name_col == name).order_by(cls.id).all()
        for obj in result:
            obj.session = session
        return result

    @classmethod
    def load_in_extent_without_lines_from_db(cls, session, min_easting, max_easting, min_northing, max_northing):
        # type: (Session, float, float, float, float) -> List[Line]
        """
        Returns all points inside the given extent in the database connected to the SQLAlchemy Session session, which
        are not part of a line. This function is similar the AbstractGeoObject.load_in_extent_from_db(...) function.

        :param min_easting: minimal easting of extent
        :type min_easting: float
        :param max_easting: maximal easting of extent
        :type max_easting: float
        :param min_northing: minimal northing of extent
        :type min_northing: float
        :param max_northing: maximal northing of extent
        :type max_northing: float
        :param session: represents the database connection as SQLAlchemy Session
        :type session: Session
        :return: a list of points representing the result of the database query
        :rtype: List[GeoPoint]
        :raises ValueError: if one of the extension values is not compatible to type float
        :raises TypeError: if session is not of type SQLAlchemy Session
        """
        min_easting = float(min_easting)
        max_easting = float(max_easting)
        min_northing = float(min_northing)
        max_northing = float(max_northing)

        if not isinstance(session, Session):
            raise TypeError("'session' is not of type SQLAlchemy Session!")

        result = session.query(GeoPoint).filter(sq.between(GeoPoint.east, min_easting, max_easting)). \
            filter(sq.between(GeoPoint.north, min_northing, max_northing)). \
            filter(GeoPoint.line_id == -1). \
            order_by(cls.id).all()
        for point in result:
            point.session = session
        return result


class Line(Base, AbstractDBObject):
    """
    Class Line

    Represents a geological line feature, e.g. for storing faults or horizon surface expressions.
    """
    # define db table name and columns
    __tablename__ = 'lines'

    id = sq.Column(sq.INTEGER, sq.Sequence('line_id_seq'), primary_key=True)
    closed = sq.Column(sq.BOOLEAN)

    # set stratigraphy of the line
    horizon_id = sq.Column(sq.INTEGER, sq.ForeignKey('stratigraphy.id'))
    hor = relationship("StratigraphicObject")

    # add GeoPoint relation, important is the ordering by line_pos value
    # collection_class function automatically reorders this value in case of insertion or deletion of points
    points = relationship("GeoPoint", order_by=GeoPoint.line_pos, collection_class=ordering_list('line_pos'),
                          backref="line", primaryjoin='Line.id==GeoPoint.line_id',
                          cascade="all, delete, delete-orphan")

    def __init__(self, closed, horizon, points, *args, **kwargs):
        # type: (bool, StratigraphicObject, List[GeoPoint], *object, **object) -> None
        """
        Create a new line.

        :param closed: True if the line should be closed, else False
        :type closed: bool
        :param horizon: Stratigraphy to which the line belongs
        :type horizon: StratigraphicObject
        :param points: list of points which represents the lines nodes
        :type points: List[GeoPoint]
        :param args: parameters for AbstractDBObject initialisation
        :type args: List()
        :param kwargs: parameters for AbstractDBObject initialisation
        :type kwargs: Dict()
        :return: Nothing
        :raises ValueError: Raises ValueError if one of the types cannot be converted
        """
        for pnt in points:
            if type(pnt) is not GeoPoint:
                raise ValueError('At least on point in points is not of type GeoPoint!')

        self.is_closed = bool(closed)
        self.horizon = horizon
        self.points = points

        # check doubled values and stratigraphy in the line
        self.__remove_doubled_points()
        self.__check_line()

        # call base class constructor
        AbstractDBObject.__init__(self, *args, **kwargs)

    def __repr__(self):
        # type: () -> str
        """
        Returns a text-representation of the line

        :return: Returns a text-representation of the line
        :rtype: str
        """
        text = "<Line(id='{}', closed='{}', horizon='{}'\n)>".format(self.id, self.closed, str(self.horizon))
        text += AbstractDBObject.__repr__(self)
        text += "\npoints=\n" + str(self.points)
        return text

    def __str__(self):
        # type: () -> str
        """
        Returns a text-representation of the line

        :return: Returns a text-representation of the line
        :rtype: str
        """
        text = "[{}] {} - {}\n".format(self.id, "closed" if self.closed else "not closed", str(self.horizon))
        text += AbstractDBObject.__str__(self)
        text += "\npoints:\n"

        for point in self.points:
            text += "\n{}".format(str(point))

        return text

    @property
    def is_closed(self):
        # type: () -> bool
        """
        True if the line is closed else False

        :type: bool
        :raises ValueError: if value is not compatible to type bool
        """
        return self.closed

    @is_closed.setter
    def is_closed(self, value):
        # type: (bool) -> None
        """
        see getter
        """
        value = bool(value)
        self.closed = bool(value)

    @property
    def horizon(self):
        # type: () -> StratigraphicObject
        """
        The stratigraphy of the line object

        :type: StratigraphicObject
        :raises TypeError: Raises TypeError if value is not of type Stratigraphy
        """
        return self.hor

    @horizon.setter
    def horizon(self, value):
        # type: (StratigraphicObject) -> None
        """
        see getter
        """
        if (value is not None) and (type(value) is not StratigraphicObject):
            raise TypeError('type of committed value ({}) is not StratigraphicObject!'.format(type(value)))

        if value is None:
            self.hor = None
            self.horizon_id = -1
        else:
            self.hor = value

        # check stratigraphy
        self.__check_line()

    def insert_point(self, point, position):
        # type: (GeoPoint, int) -> None
        """
        Insert a point in the line at the committed index.

        :param point: point to be inserted in the line
        :type point: GeoPoint
        :param position: Index, where points should be inserted in the line
        :type position: int
        :return: Nothing
        :raises TypeError: Raises TypeError if point is not of type GeoPoint
        :raises ValueError: Raises ValueError if position is not of type int or cannot be converted to int
        """
        position = int(position)
        if type(point) is not GeoPoint:
            raise TypeError('point {} is not of type GeoPoint!'.format(str(point)))
        else:
            self.points.insert(position, point)

        # check doubled values and stratigraphy in the line
        self.__remove_doubled_points()
        self.__check_line()

    def insert_points(self, points, position):
        # type: (List[GeoPoint], int) -> None
        """
        Insert a points in the line at the committed index.

        :param points: List of points to be inserted in the line
        :type points: List[GeoPoint]
        :param position: Index, where points should be inserted in the line
        :type position: int
        :return: Nothing
        :raises TypeError: Raises TypeError if one of the points is not of type GeoPoint
        :raises ValueError: Raises ValueError if position is not of type int or cannot be converted to int
        """
        position = int(position)

        for pnt in points:
            if type(pnt) is not GeoPoint:
                raise TypeError('At least on point in points is not of type GeoPoint!')

        # use slicing for points insert
        if len(self.points) <= position:
            self.points[-1:-1] = points
        else:
            self.points[position:position] = points

        # check doubled values and stratigraphy in the line
        self.__remove_doubled_points()
        self.__check_line()

    def get_point_index(self, point):
        # type: (GeoPoint) -> int
        """
        Returns the index of the given point in the line

        :param point: point which has to be looked up
        :type point: GeoPoint
        :return: Index of the point in the line
        :rtype: int
        :raises ValueError: Raises ValueError if committed point is not part of the line
        """
        return self.points.index(point)

    def delete_point(self, point):
        # type: (GeoPoint) -> None
        """
        Deletes the point from the line

        :param point: GeoPoint object which should be deleted
        :type point: GeoPoint
        :return: Nothing
        :raises TypeError: Raises TypeError if point is not of type GeoPoint
        :raises ValueError: Raises ValueError the point is not part of the line
        """
        if type(point) is not GeoPoint:
            raise TypeError('point {} is not of type GeoPoint!'.format(str(point)))

        try:
            self.points.remove(point)
        except ValueError as e:
            raise ValueError(str(e) + '\nGeoPoint with ID ' + str(point.id) + ' not found in list!')

        # check doubled values and stratigraphy in the line
        self.__remove_doubled_points()
        self.__check_line()

    def delete_point_by_coordinates(self, easting, northing, altitude=0):
        # type: (float, float, float) -> None
        """
        Deletes a point with the given coordinates from the line

        :param easting: easting value of the point to be deleted
        :type easting: float
        :param northing: northing value of the point to be deleted
        :type northing: float
        :param altitude: altitude value of the point to be deleted (only necessary if point has z-values!)
        :type altitude: float
        :return: Nothing
        :raises ValueError: Raises ValueError if one parameter is not compatible to type float or no point can be found
        """
        try:
            easting = float(easting)
            northing = float(northing)
            altitude = float(altitude)
        except ValueError:
            raise ValueError('On of the input coordinates is not of type float!')

        # iterate over a copy of the list to avoid iteration issues caused by the deletion of values
        for pnt in self.points[:]:
            if (abs(float(pnt.easting) - easting) < float_precision) and (
                    abs(float(pnt.northing) - northing) < float_precision) and (
                    (abs(float(pnt.altitude) - altitude) < float_precision) or not pnt.has_z):
                self.points.remove(pnt)
                # check doubled values in a line
                self.__remove_doubled_points()
                self.__check_line()
                return

        raise ValueError('Point not found with coordinates {0}/{1}/{2}'.format(easting, northing, altitude))

    def __check_line(self):
        # type: () -> None
        """
        Checks the line for inconsistencies.
        Current checks:
        - stratigraphy check for all points

        :return: Nothing
        """
        for point in self.points:
            point.horizon = self.horizon

    def __remove_doubled_points(self):
        # type: () -> None
        """
        remove points with the same coordinates, if they follow up each other in the points list.

        :return: None
        """
        # create a full copy of the point-list
        tmp_pnts = self.points[:]
        for i in range(len(tmp_pnts) - 1):
            coord_1 = (tmp_pnts[i].easting, tmp_pnts[i].northing, tmp_pnts[i].altitude)
            coord_2 = (tmp_pnts[i + 1].easting, tmp_pnts[i + 1].northing, tmp_pnts[i + 1].altitude)

            # remove doubled points
            if coord_1 == coord_2:
                self.points.remove(tmp_pnts[i + 1])

        # test for first and last point
        # if identical, then remove last point and set closed to True
        coord_1 = (self.points[0].easting, self.points[0].northing, self.points[0].altitude)
        coord_2 = (self.points[-1].easting, self.points[-1].northing, self.points[-1].altitude)

        if coord_1 == coord_2:
            del self.points[-1]
            self.closed = True

        # reorder to ensure right position value without reloading from database
        self.points.reorder()

    @classmethod
    def load_in_extent_from_db(cls, session, min_easting, max_easting, min_northing, max_northing):
        # type: (Session, float, float, float, float) -> List[Line]
        """
        Returns all lines with at least on point inside the given extent in the database connected to the SQLAlchemy
        Session session. This function overloads the AbstractGeoObject.load_in_extent_from_db(...) function.

        :param min_easting: minimal easting of extent
        :type min_easting: float
        :param max_easting: maximal easting of extent
        :type max_easting: float
        :param min_northing: minimal northing of extent
        :type min_northing: float
        :param max_northing: maximal northing of extent
        :type max_northing: float
        :param session: represents the database connection as SQLAlchemy Session
        :type session: Session
        :return: a list of lines representing the result of the database query
        :rtype: List[Line]
        :raises ValueError: if one of the extension values is not compatible to type float
        :raises TypeError: if session is not of type SQLAlchemy Session
        """
        min_easting = float(min_easting)
        max_easting = float(max_easting)
        min_northing = float(min_northing)
        max_northing = float(max_northing)

        if not isinstance(session, Session):
            raise TypeError("'session' is not of type SQLAlchemy Session!")

        # select the points with a line_id that are located inside the extent
        # -> result will be a list of tuples with only a single line-id value
        # -> convert this list to a set in order to remove doubled values

        points = set(
            [x[0] for x in session.query(GeoPoint.line_id).
                filter(GeoPoint.line_id != -1).
                filter(sq.between(GeoPoint.east, min_easting, max_easting)).
                filter(sq.between(GeoPoint.north, min_northing, max_northing)).all()
             ])

        # return line with points in extend
        # to speed up the process, test if points (len > 0) exist in extent first
        if len(points) == 0:
            return []
        result = session.query(Line).filter(Line.id.in_(points)).order_by(cls.id).all()
        for line in result:
            line.session = session
        return result
