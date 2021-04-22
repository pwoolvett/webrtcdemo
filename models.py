#!/usr/bin/env python
import sqlalchemy

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String

from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def create_database(engine):
    Base.metadata.create_all(engine)

def get_engine(connection_string:str):
    return sqlalchemy.create_engine(connection_string)

def get_session(connection_string:str):
    engine = get_engine(connection_string)
    session_class = sqlalchemy.orm.sessionmaker(bind=engine)
    return session_class
    

class Detection(Base):
    __tablename__ = 'detections'
    id = Column(Integer, primary_key=True)
    frame_id = Column(Integer, ForeignKey('frames.id'), nullable=False)
    label = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    x_min = Column(Float, nullable=False)
    x_max = Column(Float, nullable=False)
    y_min = Column(Float, nullable=False)
    y_max = Column(Float, nullable=False)

    objects = relationship("Object", backref="detections", lazy=True)

    def __repr__(self):
        return f"<<{self.label}({(100*self.confidence):.1f}%)@[({self.x_min:.1f},{self.y_min:.1f}),({self.x_max:.1f}\n, {self.y_max:.1f})>>"


class Frame(Base):
    __tablename__ = 'frames'
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=True)
    object_count = Column(Integer, nullable=False)
    camera_id = Column(Integer, nullable=False)
    frame_number = Column(Integer, nullable=False)
    
    detections = relationship("Detection", backref="frames", lazy=True)
    
    def __repr__(self):
        return f"<<Frame {self.frame_number}@CAM_{self.camera_id}. Objects:{self.object_count:02d}Event ID:{self.event_id}"


class Object(Base):
    __tablename__ = 'objects'
    id = Column(Integer, primary_key=True)
    detection_id = Column(Integer, ForeignKey('detections.id'), nullable=False)
    rois = Column(String, nullable=True)

    def __repr__(self):
        return f"<<Object number {self.id}_D{self.detection_id}.ROIs:{self.rois}>>"


class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    event_type = Column(String, nullable=False)
    evidence_video_path = Column(String, unique=True, nullable=False)

    frames = relationship("Frame", backref="events", lazy=True, uselist=False)

    def __repr__(self):
        return f"Event {self.event_type}@{self.timestamp}"


if __name__=='__main__':
    db_location = "/db/test.db"
    db_connection_string = f"{db_location}"
    db = get_session(db_connection_string)
    db.create_all()