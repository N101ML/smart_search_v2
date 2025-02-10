from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class CommentDB(Base):
  __tablename__ = 'comments'
  id = Column(Integer, primary_key=True, index=True)
  body = Column(String)
  replies = relationship("CommentDB", back_ref="parent", remote_side=[id])

  def __repr__(self):
    return f"<Comment(id={self.id}, body={self.body})>"